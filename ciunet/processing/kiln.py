import logging
import datetime
import os
import traceback
from PyQt5 import QtCore
#import configobj
from python_util.util import configobj
ConfigObj = configobj.myConfigObj
from python_util import util as util
from .scanner import Scanner
from .TireSlipTrigger import TireSlipTrigger
from .ComposedImage import ComposedImage
from ciunet.writer.image import ImageWriter
from ciunet.writer.text import TextWriter
#python311
#from ciunet.writer.nowiny.nowiny_xml import NowinyXMLWriter
from ciunet.writer.tcem.TCEMManager import TCEMManager
from .networkTrigger import udpTrigger, adamTrigger

class ReceiverThread(util.WorkerThread):
    pass


class TCEMThread(util.WorkerThread):
    pass

class InfluxMThread(util.WorkerThread):
    pass

class Kiln(QtCore.QObject):
    signalGotTrigger = QtCore.pyqtSignal(object,bool)
    signalTimeout = QtCore.pyqtSignal(object)
    signalGotStatusData = QtCore.pyqtSignal(object, object)

    def setTireslipCalc(self,calcer):
        self.tireslip_calculator=calcer
        self.tireslip_calculator.moveToThread(self.tireslip_receiver_thread)
        self.tireslip_receiver_thread.start()
        self.signalGotTrigger.connect(self.tireslip_calculator.receiver)


    def setTireslipReceiver(self, receiver):
        self.tireslip_receiver=receiver
        self.tireslip_receiver.moveToThread(self.tireslip_receiver_thread)

        for s in self.scanners:
            s.receiver.signalNewTimeData.connect(self.tireslip_receiver.writeRawValue)
            print (s,self.tireslip_receiver)
            print('/'*80)
    def all_scanner_ok(self):
        ok=False
        for s in self.scanners:
            ok=ok|s.data_ok
        return ok


    def __init__(self, config):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Creating kiln object")
        self.rpm = 0.0
        self.trigger_state = False
        self._transform_temperatures = True
        self._fov_mode = False
        self.__softwareTimeoutTicker = None
        self.__allScannersTimedOut = False
        self.tireslip_receiver_thread = InfluxMThread()
        self._global_sensorIndex = [0]  # counter to give unique index to scanners/pyrometers. stored in a MUTABLE list
        self.sensors = {}

        self.parse_config(config)

        self.__scannerTimeOutTimer = QtCore.QTimer(self)
        self.__initComposer(config["image"])
        self.__initScanners(config["scanners"])
        self.composed_image.init_sensors(self)
        self.__initTCEMWriter(config["tcem"])
        self.__init_image_writer(config["image_writer"])
        self.__init_text_writer(config["text_writer"])
        self.__init_nowiny_writer(config["nowiny_writer"])
        self.__initTrigger(config["trigger"])
    def parse_config(self, config):
        self.description = config.get("description", "Gesotec - Kiln#1").encode()
        try:
            self.length_unit = str(config["length_unit"])
        except Exception as e:
            raise Exception("Could not parse config option '{}'.".format(e)) from e
        if self.length_unit not in ("m", "f"):
            raise ValueError("Invalid kiln length unit.")
        self.kiln_start = float(config["kiln_start"])
        self.kiln_end = float(config["kiln_end"])
        if self.length == 0.0:
            raise ValueError("Kiln length must be greater than 0.")

    @property
    def transform_temperatures(self):
        """Get status of temperature transformation"""
        return self._transform_temperatures

    @transform_temperatures.setter
    def transform_temperatures(self, value):
        """Enable/Disable temperature transformation"""
        self._transform_temperatures = bool(value)
        self.composed_image.clear()
        self.tcem.tic()
        self.logger.info("Temperature Transformation set to: {}".
                         format("Enabled" if self.transform_temperatures else "Disabled"))

    @property
    def fov_mode(self):
        return self._fov_mode

    @fov_mode.setter
    def fov_mode(self, value):
        """Enable/Disable fov mode"""
        self._fov_mode = bool(value)
        self.composed_image.clear()
        self.tcem.tic()
        self.logger.info("FoV mode set to: {}".format("Enabled" if self.fov_mode else "Disabled"))

    @property
    def raw_image_width(self):
        return self.target_pixel * self.image_reduction_factor

    def connect_signals(self):
        self.__scannerTimeOutTimer.timeout.connect(self.__checkScannerTimeouts)
#        self.scanners.

    @QtCore.pyqtSlot()
    @util.noexcept
    def start(self):
        self.logger.debug("Starting Kiln. Thread={}".format(QtCore.QThread.currentThread()))
        self.connect_signals()
        for scanner in self.scanners:
            scanner.start()
        self.__scannerTimeOutTimer.start()
        if self.__softwareTimeoutTicker is not None:
            self.__softwareTimeoutTicker.start()
            self.logger.info("Starting software trigger")
        self.tcem_thread.start(QtCore.QThread.LowPriority)
        QtCore.QMetaObject.invokeMethod(self.tcem, "start")

    @util.noexcept
    def quit(self):
        self.logger.debug("Quitting kiln")
        self.stop()
        self.tcem_thread.quit()
        self.tcem_thread.wait()
        if self.tireslip_receiver_thread:
            self.tireslip_receiver_thread.quit()
            self.tireslip_receiver_thread.wait()
        self.logger.debug("Quitted kiln")

    @QtCore.pyqtSlot()
    @util.noexcept
    def stop(self):
        self.logger.debug("Stopping kiln")
        QtCore.QMetaObject.invokeMethod(self.__scannerTimeOutTimer, "stop")
        QtCore.QMetaObject.invokeMethod(self.__softwareTimeoutTicker, "stop")
        self.tcem.stop()
        for scanner in self.scanners:
            scanner.stop()
        self.logger.debug("Kiln stopped")

    @QtCore.pyqtSlot()
    def toggle_temperature_transformation(self):
        self.transform_temperatures = not self.transform_temperatures

    @QtCore.pyqtSlot()
    def toggle_fov_mode(self):
        self.fov_mode = not self.fov_mode

    @QtCore.pyqtSlot(object)
    @util.noexcept
    def __scannerTimedOut(self, scanner):
        self.composed_image.blackout(scanner)
        for pyrometer in scanner.pyrometers:
            self.composed_image.blackout(pyrometer)
        self.signalTimeout.emit("Scanner {} timed out".format(scanner.displayIndex))

    @QtCore.pyqtSlot()
    @util.noexcept
    def __checkScannerTimeouts(self):
        allTimedOut = True
        for scanner in self.scanners:
            if not scanner.timeOutStatus:
                allTimedOut = False

        if allTimedOut:
            if not self.__allScannersTimedOut:
                self.logger.warning("All Scanners timed out!")
                self.signalTimeout.emit("All Scanners timed out!")
            self.__allScannersTimedOut = True

    def __initScanners(self, scanners_config):
        self.__scannerTimeOutTimer.setInterval(1000)
        try:
            self.scanners = []
            if isinstance(scanners_config, str):
                # Configparser automatically creates a string if only one scanner is given,
                # or a list of strings if a comma-separated list is given. So
                # make sure we always have a list to iteratre over.
                scanners_config = [scanners_config]
            for scanner_config in scanners_config:
                    config_file = os.path.join("config", scanner_config)
                    c = configobj.ConfigObj(config_file, encoding="utf-8")
                    s = Scanner(config=c,
                                scanner_index=len(self.scanners) + 1,
                                sensor_index=self._global_sensorIndex,
                                config_path=config_file,
                                kiln=self)
                    s.signalTimeout.connect(self.__scannerTimedOut)
#                    s.receiver.signalNewAnalogData
                    self.scanners.append(s)

        except Exception as e:
            print(traceback.format_exc())
            raise Exception("Could not Initialize Scanners:\n{}".format(e)) from e

    def __initComposer(self, image_config):
        try:
            self.composed_image = ComposedImage(config=image_config, parent=self)
            self.signalGotTrigger.connect(self.trigger_composer, QtCore.Qt.QueuedConnection)
        except Exception as e:
            raise Exception("Could not Initialize Composer.") from e

    def __initTCEMWriter(self, tcem_config):
        try:
            self.tcem_thread = TCEMThread()
            self.tcem = TCEMManager(config=tcem_config,
                                    length_unit=self.length_unit,
                                    kiln=self,
                                    composed_image=self.composed_image)
            self.tcem.moveToThread(self.tcem_thread)
            self.tcem.connect_signals()
            self.composed_image.signal_image_updates.connect(self.tcem.registerTrigger, QtCore.Qt.QueuedConnection)
        except Exception as e:
            print (e)

            raise Exception("Could not Initialize TCEM Writer.") from e

    def __init_image_writer(self, image_config):
        try:
            self.image_writer = ImageWriter(
                                    composed_image=self.composed_image,
                                    config=image_config,
                                    kiln=self,
                                    parent=None)
            self.image_writer.moveToThread(self.tcem_thread)
            self.composed_image.signal_image_updates.connect(self.image_writer.registerTrigger,
                                                             QtCore.Qt.QueuedConnection)
        except Exception as e:
            raise Exception("Could not Initialize new Image Writer.") from e

    def __init_text_writer(self, image_config):
        try:
            self.text_writer = TextWriter(
                                    composed_image=self.composed_image,
                                    config=image_config,
                                    kiln=self,
                                    parent=None)
            self.text_writer.moveToThread(self.tcem_thread)
            self.composed_image.signal_image_updates.connect(self.text_writer.registerTrigger,
                                                             QtCore.Qt.QueuedConnection)
        except Exception as e:
            raise Exception("Could not Initialize new Text Writer.") from e

    def __init_nowiny_writer(self, image_config):
        pass
        #python311
        return
        try:
            self.nowiny_writer = NowinyXMLWriter(
                                    composed_image=self.composed_image,
                                    config=image_config,
                                    kiln=self,
                                    parent=None)
            self.nowiny_writer.moveToThread(self.tcem_thread)
            self.composed_image.signal_image_updates.connect(self.nowiny_writer.registerTrigger,
                                                             QtCore.Qt.QueuedConnection)
        except Exception as e:
            raise Exception("Could not Initialize Nowiny Writer.") from e

    @QtCore.pyqtSlot(object)
    @util.noexcept
    def trigger_composer(self, _interval,sw_timeout=True):
        # Inform tcem about a trigger slightly later, to avoid any interpolation problems
        QtCore.QTimer.singleShot(100, self.composed_image.update_image)

    def __initTrigger(self, trigger_config):
        try:
            parsedSoftwareTimeout = float(trigger_config["softwareTimeout"])
            if parsedSoftwareTimeout <= 0.0:
                raise ValueError("Trigger software timeout must be positive.")

            parsedType = str(trigger_config["type"])
            parsed_minimum_trigger_interval = float(trigger_config.get("minimum_trigger_interval", 0.0))
            if parsed_minimum_trigger_interval < 0.0:
                raise ValueError("Minimum trigger interval must not be negative.")
            self.minimum_trigger_interval = datetime.timedelta(seconds=parsed_minimum_trigger_interval)

            if parsedType == "scanner":
                parsedScannerID = int(trigger_config["scannerID"])
                scannerid = parsedScannerID - 1
                try:
                    scanner = self.scanners[scannerid]
                    scanner.trigger = True
#                    scanner.signal_got_internal_trigger.connect(self._receive_hardware_trigger,
#                                                                QtCore.Qt.QueuedConnection)
                    scanner.signal_got_internal_trigger.connect(self._receive_hardware_trigger,)
                except IndexError as e:
                    raise Exception("Trigger scanner id '{}' out of range!".format(parsedScannerID)) from e
            if parsedType == "tireslip":
                self.tireslip_trigger = TireSlipTrigger(trigger_config, parent=self)
                self.tireslip_trigger.signal_trigger.connect(self._receive_hardware_trigger)
                self.tireslip_trigger.start()

            if parsedType == "udpmessage":
                self.udp_trigger = udpTrigger(trigger_config, parent=self)
                self.udp_trigger.signal_trigger.connect(self._receive_hardware_trigger)
                self.udp_trigger.start()
            if parsedType == "virtualadam":
                self.adam_trigger = adamTrigger(trigger_config, parent=self)
                self.adam_trigger.signal_trigger.connect(self._receive_hardware_trigger)
                self.adam_trigger.start()

            self.udp_trigger = udpTrigger(trigger_config, parent=self,local=True)
            self.udp_trigger.signal_trigger.connect(self._receive_hardware_trigger)
            self.udp_trigger.start()



            self.__softwareTimeoutTicker = QtCore.QTimer(self)
            self.last_trigger_time = None
            self.softwareTimeout = datetime.timedelta(seconds=parsedSoftwareTimeout)
            if self.softwareTimeout.total_seconds() > 0.0:
                timeout = int(self.softwareTimeout.total_seconds() * 1000.0)
                self.__softwareTimeoutTicker.setInterval(timeout)
                self.logger.info("Configured Software Timeout with interval={}ms".format(timeout))
                self.__softwareTimeoutTicker.timeout.connect(self.__receiveSoftwareTimeout, QtCore.Qt.QueuedConnection)

        except Exception as e:
            raise Exception("Could not Initialize Trigger.") from e

    @QtCore.pyqtSlot()
    @util.noexcept
    def __receiveSoftwareTimeout(self):
        self.logger.info("Received Software Timeout")
        self.__receiveTrigger(self.softwareTimeout, softwareTimeout=True)

    @QtCore.pyqtSlot(object)
    @util.noexcept
    def _receive_hardware_trigger(self, interval):
        if (interval is not None) and interval > self.softwareTimeout:
            self.logger.warning("Received hardware trigger interval ({}) is larger "
                                "than configured software timeout ({}).".
                                format(interval, self.softwareTimeout))
        self.__receiveTrigger(interval=interval,
                              softwareTimeout=False)

    def __receiveTrigger(self, interval, softwareTimeout):
        try:
            self.logger.info("Kiln received trigger. sw-timeout={}".format(softwareTimeout))
            merged_interval = interval
            if interval is not None:
                rpm = 60.0/interval.total_seconds() if interval is not None else None
                self.logger.info("Kiln trigger interval={} (rpm={}) sw-timeout={}".
                                 format(interval, rpm, softwareTimeout))
            else:
                if self.last_trigger_time is not None:
                    now = datetime.datetime.now()
                    merged_interval = now - self.last_trigger_time
                    rpm = 60.0/interval.total_seconds() if interval is not None else 0
                    self.logger.info("Adjusted trigger interval={} (rpm={})".
                                     format(interval, rpm))
            if merged_interval is not None and merged_interval < self.minimum_trigger_interval:
                self.logger.warning("Rejected trigger with interval={}, because it was shorter "
                                    "than minimum_trigger_interval={}".
                                    format(interval, self.minimum_trigger_interval))
                return

            QtCore.QMetaObject.invokeMethod(self.__softwareTimeoutTicker, "start")
            for scanner in self.scanners:
                scanner.externTrigger(merged_interval)
#                 if softwareTimeout:
#                     scanner.externTrigger(interval)
#                 else:
#                     if not scanner.trigger:
#                         scanner.externTrigger(interval)
            if merged_interval is not None:
                self.rpm = 60.0 / merged_interval.total_seconds()
            self.trigger_state = not softwareTimeout
            self.signalGotTrigger.emit(merged_interval,softwareTimeout)
            self.last_trigger_time = datetime.datetime.now()
        except Exception as e:
            self.logger.error("Error when receiving trigger: {}".format(e))

    @property
    def length(self):
        """kiln length. Can be positive or negative"""
        return self.kiln_end - self.kiln_start

    @property
    def status(self):
        desc = "ggr-daq kiln"
        dat = {desc: {"type": "kiln", "value": {}}}
        dats = dat[desc]["value"]
        for i, s in enumerate(self.scanners):
            try:
                dats["scanner %i" % i] = {"type": "scanner", "value": s.status}
            except Exception as e:
                self.logger.debug("Could not add scanner status: {}".format(e))
        return dat

    def export_thermal_image(self):
        self.logger.info("Exporting thermal image")
        now = util.current_local_time()
        filename = os.path.abspath("./thermal_image_{}.IMG".format(now))
        self.tcem.write_mage_to_file(filename)
        return filename
