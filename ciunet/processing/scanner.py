import logging
import influxpy
import datetime
import sys
import traceback
import time
from pymodbus.client import ModbusTcpClient
#from pymodbus.client.sync import ModbusTcpClient
from PyQt5 import QtCore
import numpy
import pprint

from python_util import util as util
from daq_net.daq.receiver import DaLiReceiver
from .temperatures.TemperatureConverter import TemperatureConverter
from daq_net.daq import Temperature
from .InternalTemperature import InternalTemperature
from .multiplexedValues import MultiplexedValuesManager
from .Pyrometer import Pyrometer
from .ConvertedLine import ConvertedLine
from .temperaturesManager import TemperaturesManager
from ciunet.processing.transform.geometrical_transformation import GeoTransformator
from . import Sensor


class Scanner(Sensor.Sensor):
    """
    Manager representing a IR-Scanner.
    - set up the daq-receiver
    - handle all line-based data processing/transformation
    - emit processed scanner lines and other data for further image composition
    """
    signal_got_internal_trigger = QtCore.pyqtSignal(object)
    signalTimeout = QtCore.pyqtSignal(object)
    signalTimeout2 = QtCore.pyqtSignal(object)

    def __init__(self, config, scanner_index, sensor_index, config_path, kiln):
        Sensor.Sensor.__init__(self, config, sensor_index, kiln=kiln, parent=kiln)
        self.data_ok=False
        self.restarting=False
        self.analogValues = [0, 0, 0, 0, 0, 0]
        self.kiln = kiln
        self.config_path = config_path
        self.displayIndex = scanner_index
        self.model = config.get("model", "")
        self.type='scanner'
        self.serial = config.get("serial", "")
        try:
            self.type = config.get("type", "scanner")
            if self.type!="scanner": self.hasLinedata=False

        except Exception as e:
            print(e)

        self.logger = logging.getLogger(str(self))
        self.time_channels={}

        if "time_measurement" in config:
            try:
                time_measurement_config=config["time_measurement"]
                used_channels=time_measurement_config["used_channels"]
                channel_offset=int(time_measurement_config["channel_offset"])
                for ch in used_channels:
                    self.time_channels[int(ch)]=int(ch)+channel_offset
            except Exception as e:
                print(e)
                self.logger.warning("could not add time measurement channels")
            self.logger.info(f"time_measurement_channels: {self.time_channels}")
#            sys.exit(0)



        self.max_FOV_value=int(config.get('max_FOV_V',99999))
        self.min_FOV_value=int(config.get('min_FOV_V',0))
        self.pyrometers = []
#        print(config_path)
#        print(config)
        self.modbusAktiv=config['dali_control'].as_bool('aktiv')
        if self.modbusAktiv:
            self.modbusNormalOpen = config['dali_control'].as_bool('normalOpen')

            self.modbusIp=config['dali_control']['ip']
            self.modbusCoil=int(config['dali_control']['coil'])
            self.modbusDelay=float(config['dali_control']['delay'])
        self.__lastTimeReceivedLine = None
        self.geometrical_mode = "default"
        self.__timedOut = False
        self.timeoutInterval = float(config.get("timeout", 30.0))
        self.__scannerTimeOutTimer = QtCore.QTimer(self)
        self.__scannerTimeOutTimer.setInterval(1000)

        self.logger.debug("Creating Scanner object. config:\n{}".format(pprint.pformat(config)))
        self.trigger = False
        self.reverse_horizontal = util.str2bool(config["reverse_h"])
        self.fov_angle = float(config["fov_angle"]) % 360.0
        self.fov_offset = float(config["fov_offset"])
        self.multiplexedValuesManager = MultiplexedValuesManager(self, config)
        self.__parsePyrometers(config, sensor_index)
        self.receiver = DaLiReceiver(parent=self, grabber_parent=None, config=config["receiver"], scanner=self,timechannels=self.time_channels)
        self.temperatureManager = TemperaturesManager(self, config)
        self.geologe = GeoTransformator(kiln=kiln,
                                        target_pixel=self.target_pixel,
                                        fov_angle=self.fov_angle,
                                        geometry_config=config["geometry"],
                                        mask=self.mask,
                                        interpolation_mode=kiln.composed_image.horizontal_interpolation_mode)
        self.internalTemperature = InternalTemperature(self, config["internal_temperature"])
        self.temperature_transformer = TemperatureConverter(config=config["temperature"],
                                                            scanner=self,
                                                            parent=self)

#        self.fov_angle=359
        self.last_trigger = None
        self.next_to_last_trigger = None
        self.next_to_next_last_trigger = None
        self.last_line = None
        self.signalTimeout2.connect(self.restartDali)

    @property
    def name(self):
        return f"{self.type}"#_{self.displayIndex}"

    @QtCore.pyqtSlot()
    @util.noexcept
    def start(self):
        self.logger.debug("Starting scanner")
        self.receiver.signalGotLine.connect(self.receiveLine, QtCore.Qt.QueuedConnection)
        self.receiver.signalNewAnalogData.connect(self.receiveAnalogvalues, QtCore.Qt.QueuedConnection)
        self.receiver.signalGotTrigger.connect(self.intTrigger, QtCore.Qt.QueuedConnection)
        self.__scannerTimeOutTimer.timeout.connect(self.__checkTimeout)
        self.__scannerTimeOutTimer.start()
        QtCore.QMetaObject.invokeMethod(self.receiver, "start")
    def receiveAnalogvalues(self,values):
        self.analogValues=values
    def restartDali(self):
        self.restarting=True
        if not self.modbusAktiv:
            return
        ip=self.modbusIp
        coil=self.modbusCoil
        delay=self.modbusDelay
        self.logger.info(f'restart Dalineta with Modbus IP: {ip} Coil:{coil}')
        try:
            client = ModbusTcpClient(ip)
        except Exception as e:
            self.logger.error('modbus connection failed')
            return
        try:
            r = client.write_coil(coil, self.modbusNormalOpen)
            self.logger.info(r)
            if delay>0:
                self.logger.info(f'wait {delay}s')
                time.sleep(delay)
            r = client.write_coil(coil, not self.modbusNormalOpen)
            self.logger.info(r)
        except Exception as e:
            self.logger.error('modbus write coil failed')
        time.sleep(delay)
        self.restarting=False
    @QtCore.pyqtSlot()
    @util.noexcept
    def stop(self):
        self.logger.debug("Stopping scanner")
        QtCore.QMetaObject.invokeMethod(self.receiver, "stop")

    @QtCore.pyqtSlot(object)
    @util.noexcept
    def externTrigger(self, data):
        # if self.last_line is None:
        #     self.logger.debug("Scanner does not yet have any last lines, ignoring trigger.")
        #     return
        print ("extern trigger")
        try:
            trigger_time = self.last_line.time_usec
        except:
            import time
            print ("trigger time")
            trigger_time=int(time.time()*1000000000)
            trigger_time=int(time.time()*1000000)

        if self.next_to_last_trigger:
            self.next_to_next_last_trigger = self.next_to_last_trigger
        if self.last_trigger:
            self.next_to_last_trigger = self.last_trigger
        self.last_trigger = trigger_time
        if self.last_trigger and self.next_to_last_trigger:
            diff = self.last_trigger - self.next_to_last_trigger
        else:
            diff = None
        self.logger.info("Scanner received extern trigger. lt={}, t={}, diff={}".format(self.next_to_last_trigger,
                                                                                        self.last_trigger,
                                                                                        diff))
        if self.last_line is None:

            self.logger.debug("Scanner does not yet have any last lines, ignoring trigger.")
            print ('no lines')
#            return
        self.signal_got_trigger.emit(self)
        for pyrometer in self.pyrometers:
            pyrometer.signal_got_trigger.emit(pyrometer)

    def intTrigger(self, segment):
        print ("intern trigger", self.trigger,segment,segment.last_trigger_usec)
        try:
            if not self.trigger:
                return
            self.logger.debug("Scanner received internal trigger.")
#             if self.next_to_last_trigger:
#                 self.next_to_next_last_trigger = self.next_to_last_trigger
#             if self.last_trigger:
#                 self.next_to_last_trigger = self.last_trigger
#             else:
#                 self.next_to_last_trigger = segment.next_to_last_kiln_trigger_time_usec
#             self.last_trigger = segment.last_kiln_trigger_time_usec
            self.signal_got_internal_trigger.emit(None)
#             self.signal_got_trigger.emit(self)
            for pyrometer in self.pyrometers:
                pyrometer.signal_got_trigger.emit(pyrometer)
        except Exception as e:
            self.logger.warning("scanner exception when re-emitting trigger signal: {}".format(e))
            pass

    @property
    def status(self):
        s = {}
        s["receiver"] = self.receiver.status
        return s

    @property
    def timeOutStatus(self):
        return self.__timedOut

    def isTimedOut(self, timeoutInterval):
        try:
            #return (datetime.datetime.now() - self.__lastTimeReceivedLine).total_seconds() > timeoutInterval
            return (datetime.datetime.now(datetime.timezone.utc) - self.__lastTimeReceivedLine).total_seconds() > timeoutInterval
        except Exception as _e:
            self.logger.debug("Could not check timeout", exc_info=True)
            self.logger.debug("Timeout: lastreceived={} now={}".
                              format(self.__lastTimeReceivedLine, datetime.datetime.now()))
            return False

    def checkTimedOut(self, timeoutInterval):
        r = self.isTimedOut(timeoutInterval)
        self.__timedOut = r
        return r

    def moving_average(self, a, n=3):
        ret = numpy.cumsum(a, dtype=float)
        ret[n:] = ret[n:] - ret[:-n]
        ret = numpy.roll(ret, int(n / 2))
        return ret[n - 1:] / n

    def filter_line(self, data):
        return self.moving_average(data, 1)

    @QtCore.pyqtSlot(object)
#    @util.noexcept
    def receiveLine(self, rawline):
        """
        :type rawline: RawLine
        """
        if not self.type=='scanner':
            return
        try:
            if self.trigger and self.last_trigger is None:
                self.last_trigger = rawline.last_segment.last_trigger_usec
            start_fov = int(self.fov_offset * len(rawline.data) / 360.0)

            end_fov = int((self.fov_offset + self.fov_angle) * len(rawline.data) / 360.0)
            # video_data = self.filter_line(rawline.video_data)
            video_data = rawline.video_data
            if start_fov >= 0:
                fov_video_data = video_data[start_fov:end_fov]
            else:
                # In this case we have to compose FoV data from [start_fov:] and [:end_fov]
                fov_video_data = numpy.concatenate((video_data[start_fov:], video_data[:end_fov]))
            if self.reverse_horizontal:
                fov_video_data = numpy.flipud(fov_video_data)
            if numpy.max(fov_video_data)>self.max_FOV_value:
                self.logger.warning('wrong data line(value over range), possible trigger missed')
                self.logger.warning(len(rawline.video_data))
                return
            if numpy.average(fov_video_data)<self.min_FOV_value:
                self.logger.warning('wrong data line(value under range), possible trigger missed')
                self.logger.warning(len(rawline.video_data))
                return

            self.__lastTimeReceivedLine = datetime.datetime.now()
            self.multiplexedValuesManager.parseLine(video_data)
            self.temperature_transformer.update_references()
            self.internalTemperature.invalidate()

            if len(fov_video_data)>1000:
                cline = self.__convertLine(rawline, fov_video_data)
            else:
                cline = self.__convertLine(rawline, video_data)

            self.last_line = cline
            for pyrometer in self.pyrometers:
                pyrometer.receiveLine()
            self.sigConvertedLine.emit(cline, self)
        except Exception as e:
            self.logger.info("Scanner receiveLine unhandled Exception: {}".format(e))
            self.logger.debug(traceback.format_exc())

    @property
    def internal_temperature(self):
        return self.internalTemperature.get_value()

    @QtCore.pyqtSlot()
    @util.noexcept
    def __checkTimeout(self):
        scannerStatusBefore = self.timeOutStatus
        timedOut = self.checkTimedOut(self.timeoutInterval)
        if timedOut and not scannerStatusBefore:
            self.logger.warning("scanner timed out!")
            self.logger.info("Timeout: lastreceived={} now={}".
                             format(self.__lastTimeReceivedLine, datetime.datetime.now()))
            self.signalTimeout.emit(self)
        if not self.restarting and timedOut:
            self.signalTimeout2.emit(self)
        if not timedOut and scannerStatusBefore:
            self.logger.info("Scanner is back online!")

    def __transformTemperatures(self, data):
        try:
            if self.type!='scanner':
                self.data_ok=True
                return
        except Exception as e:
            self.logger.warning('scanner type unknown')

        try:
            if self.kiln.transform_temperatures:
                self.data_ok=data.min()
                self.data_ok=True

                data = self.temperature_transformer.convert(self.fov_angle, data)
            else:
                self.data_ok=True
            if not self.data_ok:
                self.logger.warning('scandata not valid!!!!! Error 375')

            return data
        except Exception as e:
            raise Exception("Could not transform temperature.") from e

    def __transformGeometry(self, data):
        try:
            return self.geologe.convert(data, self.kiln.fov_mode, self.fov_angle)
        except Exception as e:
            raise Exception("Could not transform geometry.") from e

    def __convertLine(self, rawline, data):
        try:
            data = self.__transformTemperatures(data)
            data = self.__transformGeometry(data)
            c = ConvertedLine(rawline.time_usec)
            c.data = data
            return c
        except Exception as e:
            raise Exception("Line Data conversion failed: {}".format(e)) from e

    def getTemperatureType(self):
        return Temperature.Kelvin if self.kiln.isTemperatureTransformationEnabled() else Temperature.RAW

    def __parsePyrometers(self, config, sensor_index):
        self.logger.debug("parsing Pyrometers")
        if "pyrometers" in config:
            npyrometers = int(config["pyrometers"]["npyrometers"])
            for i in range(npyrometers):
                try:
                    p = Pyrometer(self,
                                  name="Pyrometer{}(Scanner{})".format(i + 1, self.displayIndex),
                                  config=config["pyrometers"]["pyrometer_%i" % (i + 1)],
                                  sensor_index=sensor_index)
                    self.pyrometers.append(p)
                except Exception as e:
                    raise Exception("Could not add pyrometer") from e

    def __str__(self):
        sn = " ({})".format(self.serial) if len(self.serial) else ""
        return "{}{}".format(self.name, sn)
