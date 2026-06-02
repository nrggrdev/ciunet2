import time
import logging
import os
import datetime

from PyQt5 import QtCore
import numpy

from .TCEMImage import TCEMImage
from .WindowAlarmChecker import WindowAlarmChecker
from ciunet.processing.ComposedImageView import ComposedImageViewer
from daq_net.daq import Temperature
from python_util import util as util
from ciunet.net import server
import asyncio
class TCEMManager(QtCore.QObject):
    signalSavingImage = QtCore.pyqtSignal(object)

    def __init__(self, kiln, config, length_unit, composed_image):
        try:
            super().__init__(parent=None)

            self.logger = logging.getLogger("TCEMManager")
            self.logger.debug("Creating imageWriter: {}".format(config))
            self.kiln = kiln

#            print ('create loop')
            self.webserverAktiv=False
            self.tcemserverAktiv=False
            self.config=config
            if 'webserver' in config['server']:
                l=asyncio.get_event_loop()
                self.websocket=server.webThread(l)
                self.websocket.start()
                self.webserverAktiv=True


            if 'tcemserver' in config['server']:
                try:
                    self.tcemserver=server.tcemServer(config["server"])
                    self.tcemserver.start()
                    self.tcemserverAktiv=True
                except Exception as e:
                    print (e)
                    self.logger.warning("could not start tcem-server")
            self.parsed_temperature_unit = config["temp_unit"]
            self.__parseUseLocale = config["use_locale"]
            self.__locale = (QtCore.QLocale("de") if self.__parseUseLocale else QtCore.QLocale("C"))
            try:
                self.temperature_unit = Temperature.unit[self.parsed_temperature_unit]
            except KeyError as e:
                raise ValueError("Could not parse temperature unit.") from e

            if "separate_image_limits" in config:
                self.separate_image_limits = util.str2bool(config["separate_image_limits"])
            else:
                self.separate_image_limits = False

            self.horizontal_unit = length_unit.encode("ASCII")
            self.ciuVersion = QtCore.QCoreApplication.applicationVersion()
            self.__hasImage = False

            self.__base_path = os.path.abspath(str(config["tcempath"]))
            self.ciu_index = int(config["ciu_index"])
            self.__historyBasePath = os.path.abspath(str(config["historyBasePath"]))
            self.__serialfileName = os.path.join(self.__base_path, "ciu{:d}/serial{:d}.ciu".
                                                 format(self.ciu_index, self.ciu_index))
            self.__tirecreepfileName = os.path.join(self.__base_path, "ciu{:d}/Tire/Tirecr.{:d}".
                                                    format(self.ciu_index, self.ciu_index))

            self.logger.debug("serial file: {}".format(self.__serialfileName))
            self.composed_image = composed_image
            self.image_viewer = ComposedImageViewer(config.get("image", {}), composed_image, self)
            self.tcem_image = TCEMImage(self.image_viewer, self, config.get("image", {}))
            self.__imageTimer = QtCore.QTimer(self)
            self.__imageRefreshInterval = float(config["refreshInterval"])
            self.__triggerRefresh = self.__imageRefreshInterval <= 0
            self.__lastImageID = None
            self.serial = 0
            self.__windowChecker = WindowAlarmChecker(config=config["windows"],
                                                      kiln_start=kiln.kiln_start,
                                                      kiln_end=kiln.kiln_end,
                                                      parent=self,
                                                      t_unit=self.temperature_unit,
                                                      h_unit=self.horizontal_unit)

            self.history_image_sync_interval = int(config["history_image_sync_interval"])
            self.history_image_sync_counter = 0
            history_image_interval = int(config["history_image_interval"])
            self.history_image_timer = QtCore.QTimer(self)
            self.history_image_timer.setInterval(int(history_image_interval * 1000))
            self.history_image_timer.timeout.connect(self.saveImageHistory)

            self.history_profile_sync_interval = int(config["history_profile_sync_interval"])
            self.history_profile_sync_counter = 0
            history_profile_interval = float(config["history_profile_interval"])
            self.history_profile_timer = QtCore.QTimer(self)
            self.history_profile_timer.setInterval(int(history_profile_interval * 1000))
            self.history_profile_timer.timeout.connect(self.saveProfileHistory)
        except Exception as e:
            import sys
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
    def connect_signals(self):
        if not self.__triggerRefresh:
            self.__imageTimer.setInterval(1000 * self.__imageRefreshInterval)
            self.__imageTimer.timeout.connect(self.tic)
        self.signalSavingImage.connect(self.__windowChecker.receiveData)

    @QtCore.pyqtSlot()
    @util.noexcept
    def stop(self):
        QtCore.QMetaObject.invokeMethod(self.__imageTimer, "stop")
        QtCore.QMetaObject.invokeMethod(self.__windowChecker, "stop")

    @QtCore.pyqtSlot()
    @util.noexcept
    def start(self):
        self.logger.debug("Starting TCEM manager. Thread={}".format(QtCore.QThread.currentThread()))
        if not self.__triggerRefresh:
            self.__imageTimer.start()
        self.__windowChecker.start()
        self.history_image_timer.start()
        self.history_profile_timer.start()
        self.tic()

    @QtCore.pyqtSlot()
    @util.noexcept
    def registerTrigger(self):
        self.logger.debug("registerTrigger")
        if self.__triggerRefresh:
            self.tic()
        if self.history_image_sync_interval > 0:
            self.history_image_sync_counter += 1
            if self.history_image_sync_counter >= self.history_image_sync_interval:
                self.saveImageHistory()
        if self.history_profile_sync_interval > 0:
            self.history_profile_sync_counter += 1
            if self.history_profile_sync_counter >= self.history_profile_sync_interval:

                self.saveProfileHistory()



    @QtCore.pyqtSlot()
    def tic(self):
        try:
            self.logger.debug("tic")
            if not self.kiln.all_scanner_ok():
                self.logger.warning('scandata not valid!!!!! Error 375')
                return
            self.tcem_image.update_data(self.kiln.transform_temperatures)
            self.updateHeader()
            if self.tcem_image.composed_image.rawlines==0:
                return
            if not self.tcem_image.data_ok:
                self.logger.info("invalid image.", exc_info=True)
                return
            self.serial += 1

            self.save()
            if self.tcemserverAktiv:
                self.send()
        except Exception:
            self.logger.error("Could not update TCEM image.", exc_info=True)

    def send(self):
        '''send data via server'''
        self.logger.debug('transmit Files to Clients...')
        try:
            serialdata=self.buildSerialFile()
            serialname=(os.path.basename(self.__serialfileName))
            imagename=(self.imageFilename)
            imagedata=self.getImagedata()
            try:
                windowfilename, windowdata = self.__windowChecker.getWindowData()
                self.tcemserver.broadCastData(windowdata, windowfilename)
            except:
                pass
            try:
                liningName='lining1.ini'
                lp = os.path.join(self.__base_path, f"ciu{self.ciu_index}",liningName)

                with open(lp,'r')as f:
                    data=f.read()
                self.tcemserver.broadCastData(data, liningName)
            except Exception as e:
                print(e)
                pass
            try:
#                tireslipConfig = self.config['tireslip']
                tireslipConfig = "Tirecr.1"
                #tireFilename = os.path.join('Tire',tireslipConfig["filename"])
                tireFilename = os.path.join('Tire',"Tirecr.1")
                lp = os.path.join(self.__base_path, f"ciu{self.ciu_index}",tireFilename)

                with open(lp,'r')as f:
                    data=f.read()
                self.tcemserver.broadCastData(data, tireFilename)
            except Exception as e:
                print(e)
                pass

            self.tcemserver.broadCastData(imagedata,imagename)
            self.tcemserver.broadCastData(serialdata,serialname)
            self.logger.info('Transmission to Client complete')


        except Exception as e:
            print(e)
            self.logger.warning('Transmission to Client failed')
#            return
#            raise
#        print ('send')

        if not self.webserverAktiv:
            return
        d=numpy.array(self.tcem_image.tcem_image_data, dtype=numpy.uint16)#.transpose()
        #d=numpy.array(self.tcem_image_data.tcem_image_data, dtype=numpy.uint16)#.transpose()
        toggle = self.serial % 2
        if toggle==0:
            dx = numpy.linspace(numpy.linspace(0,100,2000),numpy.linspace(100,255,2000),500)
        else:
            dx = numpy.linspace(numpy.linspace(255,100,2000),numpy.linspace(100,0,2000),500)

#        d=d[::,::3]

        #d=d-d&(1<<12)
#        d2=((d-numpy.min(d))/numpy.max(d))*255
        #d2=d2.astype(dtype=numpy.uint8)
        d2=d.astype(dtype=numpy.uint16)
        #w=1200
        #h=400
        #d2 = numpy.random.randint(256, size=(w, h), dtype=numpy.uint8)
        h,w=d2.shape
        try:
            for y in range(h):
                vy=int(y/10)%2
                for x in range(w):
                    vx = int(x / 10) % 2

                    d[y,x]=100+vy*20#+vx*20
        except Exception as e:
            print(e)
        w,h=d2.shape
        w1=w>>8
        h1=h>>8
        w2=w%256
        h2=h%256
        #s=numpy.array((w1,w2,h1,h2), dtype=numpy.uint8)
        s=numpy.array((w1,w2,h1,h2), dtype=numpy.uint16)
        self.websocket.setData(s.tobytes()+d2.tobytes())
        print ('send done ')


    def updateHeader(self):
        header = self.tcem_image.header
        self.logger.debug("Updating Header.")
        header.serial_number = str(self.serial).encode()
        now = datetime.datetime.now()
        header.pixels_per_line = self.tcem_image.composed_image.width
        if self.kiln.fov_mode:
            header.fov_unit = b"d"
            # Fixed 120deg FoV
            header.hscale_low = 0
            header.hscale_high = 120
        else:
            header.fov_unit = self.horizontal_unit
            header.hscale_low = self.kiln.kiln_start
            header.hscale_high = self.kiln.kiln_end
        header.recorded_timestamp = int(time.mktime(now.timetuple()))
        header.recorded_datetime = "{:%d.%m.%Y %H:%M:%S}".format(now).encode()
        if self.kiln.transform_temperatures:
            header.temp_unit = bytes(self.parsed_temperature_unit, encoding="ASCII")
        else:
            header.temp_unit = b"D"
        header.nscanners = len(self.kiln.scanners)
        header.no_raw_image_lines = self.tcem_image.composed_image.rawlines
        header.record_interval = 0
        for i, scanner in enumerate(self.kiln.scanners):
            t = scanner.temperature_transformer
            header.scan_data[i].first_pixel = -1
            header.scan_data[i].last_pixel = -1
            header.scan_data[i].calib.digref1 = 0
            header.scan_data[i].calib.digref2 = 0
            header.scan_data[i].calib.tempref1 = 0.0
            header.scan_data[i].calib.tempref2 = 0.0
            header.scan_data[i].calib.factorref1 = 0.0
            header.scan_data[i].calib.factorref2 = 0.0
            header.scan_data[i].calib.tempextref = 0.0
            header.scan_data[i].calib.digextref = 0
            header.scan_data[i].calib.a = float(t.A)
            header.scan_data[i].calib.b = float(t.B)
            header.scan_data[i].calib.c = float(t.C)
            header.scan_data[i].calib.u0 = float(t.u0)
            header.scan_data[i].calib.model = scanner.model.encode("ascii")
            header.scan_data[i].calib.serialno = scanner.serial.encode("ascii")
            header.scan_data[i].calib.description = b""
            header.scan_data[i].calib.a_mode = 0
            header.scan_data[i].calib.windowtemp = 0.0
            header.scan_data[i].calib.windowtransm = 0.0
            header.scan_data[i].calib.ae = 0.0
            header.scan_data[i].calib.ee = 0

    def save(self):
        try:
            self.logger.debug("Saving")
            if self.tcem_image.header.no_raw_image_lines == 0:
                self.logger.info("Not saving tcem image because there are 0 raw lines.")
                return
            self.writeImage()
            self.writeSerial()
            self.signalSavingImage.emit(self.tcem_image)
        except Exception as e:
            raise Exception("Could not save TCMNET Image.") from e

    def getImagedata(self):
        data=bytes(self.tcem_image.header)
        profiles = numpy.array(self.tcem_image.tcem_profiles)
        profiles = numpy.nan_to_num(profiles)
        profiles = profiles.astype(numpy.uint16)
        for profile in profiles:
            data+=numpy.array(numpy.nan_to_num(profile)).tobytes()
        data+= numpy.array(self.tcem_image.tcem_image_data, dtype=numpy.uint16).tobytes()
        return data

    def write_mage_to_file(self, filename):
        with util.save_file.open_savefile(filename, 'wb') as imageFile:
            imageFile.write(self.tcem_image.header)
            profiles = numpy.array(self.tcem_image.tcem_profiles)
            profiles = numpy.nan_to_num(profiles)
            profiles = profiles.astype(numpy.uint16)
            for profile in profiles:
                numpy.array(numpy.nan_to_num(profile)).tofile(imageFile)
            data = numpy.array(self.tcem_image.tcem_image_data, dtype=numpy.uint16)
            data.tofile(imageFile)
        self.logger.info("Wrote TCEM Image (serial={}) to: {}".format(self.serial, filename))

    def writeImage(self):
        toggle = self.serial % 2
        imageFileName = os.path.join(self.__base_path,
                                     "ciu{:d}".format(self.ciu_index),
                                     "IMAGE{:d}.{:d}".format(self.ciu_index, toggle))
        self.imageFilename="IMAGE{:d}.{:d}".format(self.ciu_index, toggle)
        self.write_mage_to_file(imageFileName)

    @QtCore.pyqtSlot()
    @util.noexcept
    def saveImageHistory(self):
        try:
            if self.tcem_image.kelvin_profiles is None:
                self.logger.warning("Can not yet save image history because there is no data available.")
                return
            self.history_image_sync_counter = 0
            now = datetime.datetime.now()
            extension = "IMAGE/{:Y%Y/M%m/D%d/H%HM%M%S.IMG}".format(now)
            history_file = os.path.join(self.__historyBasePath, extension)
            directory = os.path.dirname(history_file)
            if not os.path.exists(directory):
                self.logger.info("Creating History Subdir: {}".format(directory))
                os.makedirs(directory)
            self.logger.debug("History Image File: {}".format(history_file))
            self.write_mage_to_file(history_file)
            self.logger.info("Saved history image.")
        except Exception as e:
            self.logger.error("Could not save Image History: {}".format(e), exc_info=True)

    @QtCore.pyqtSlot()
    @util.noexcept
    def saveProfileHistory(self):
        try:
            if self.tcem_image.kelvin_profiles is None:
                self.logger.warning("Can not yet save profile history because there is no data available.")
                return
            self.history_profile_sync_counter = 0
            profile = self.buildAsciiProfile()
            if profile is None:
                return
            if not self.tcem_image.data_ok:
                return
            now = datetime.datetime.now()
            extension = "PROFILE/{:Y%Y/M%m/D%d/H%HM%M%S.txt}".format(now)
            history_file = os.path.join(self.__historyBasePath, extension)
            directory = os.path.dirname(history_file)
            if not os.path.exists(directory):
                self.logger.info("Creating History Subdir: {}".format(directory))
                os.makedirs(directory)
            self.logger.debug("History Profile File: {}".format(history_file))
            with open(history_file, "w") as f:
                f.write(profile)
            self.logger.info("Saved history profile.")
        except Exception as e:
            self.logger.error("Could not save Profile History: {}".format(e), exc_info=True)

    def saveHistory(self):
        if not self.__tcemImg.isValid:
            self.logger.debug("No valid Image to save for history")
            return
        if not self.tcem_image.data_ok:
            return

        self.saveImageHistory()
        self.saveProfileHistory()

    def writeSerial(self):
        serialFileData = self.buildSerialFile()
        self.seriaFileData=serialFileData
        with util.save_file.open_savefile(self.__serialfileName, "w") as fserial:
            fserial.write(serialFileData)
        self.logger.debug("Wrote serial file with serial_number={}".format(self.serial))

    def buildAsciiProfile(self):
        rawProfiles = self.tcem_image.kelvin_profiles
        if len(rawProfiles) != 3:
            return None
        convertedProfiles = Temperature.convert(Temperature.Kelvin, self.temperature_unit, rawProfiles)

        # Header Data
        now = datetime.datetime.now()
        num_elements_per_profile = convertedProfiles[0].shape[0]
        formatted_time = "{:%Y/%m/%d %H:%M:%S}".format(now)

        header_data = [("formatted_time", formatted_time),
                       ("c_time", int(time.mktime(now.timetuple()))),
                       ("num_header_lines", 2),
                       ("num_profile_sets", 3),
                       ("num_profile_in_each_set", 1),
                       ("num_elements_per_profile", num_elements_per_profile),
                       ("integration_type", 0),  # 0=snapshot 1= accumulated over interval
                       ("interval_in_hours", 0),
                       ("horizontal object start", self.kiln.kiln_start),
                       ("horizontal object end", self.kiln.kiln_end),
                       ("horizontal object unit", self.horizontal_unit.decode("UTF-8")),
                       ("temperature unit", self.parsed_temperature_unit),
                       ]

        # Build File
        out = ""
        for data in header_data:
            out += "{};".format(data[1])
        out += "\n{description}".format(description="description")
        out += "\n{};{};{}".format(0, 1, 2)  # min / max / avg
        out += "\n{};{};{}".format(0, 0, 0)  # vertical coordinates ?

        # Add Data
        for i in range(num_elements_per_profile):
            out += "\n{min:.1f};{max:.1f};{avg:.1f}".format(min=convertedProfiles[0][i],
                                                            max=convertedProfiles[1][i],
                                                            avg=convertedProfiles[2][i])
        return out

    def writeTirecreepfile(self, _path=""):
        ds = {"I": 0,
              "pos": 0,
              "intvl": 1,
              "rpm": self.kiln.rpm,
              "st": self.kiln.trigger_state,
              "result1": 1,
              "result2": 2.1,
              "code": 0, }

        data = """1 1 in Slip Clearance
#ID Position Seconds  rpm     St Slip     Clearance EC
{I:2} {pos: >8.2f} {intvl: >8.2f} {rpm: >8.3f} {st: >1d} {result1: >8.3f} {result2: >8.3f} {code: >1d}
""".format(**ds)

        if not os.path.exists(self.__tirecreepfileName):
            self.logger.warning("tire creep missed")
            try:
                self.logger.info("building tire creep path")
                os.makedirs(os.path.dirname(self.__tirecreepfileName))
            except OSError:
                self.logger.warning("tire creep path create failed")

        try:
            with util.save_file.open_savefile(self.__tirecreepfileName, "w") as fserial:
                fserial.write(data)
        except Exception as _e:
            self.logger.warning("Could not write tire creep file.")

    def buildSerialFile(self):
        # self.logger.debug( "Building Serial File" )
        # typedef enum {TEMP_DIGITAL, TEMP_DEGREES, TEMP_ISOTHERM} // TODO
        l=len(self.kiln.scanners)
        for i, s in enumerate(self.kiln.scanners):
            if s.type!='scanner':
                l-=1

        serial_file_data = {"serial_number": self.serial,
                            "c_time": self.tcem_image.header.recorded_timestamp,
                            "formatted_time": time.strftime('%d.%m.%Y %H:%M:%S',
                                                            time.localtime(self.tcem_image.header.recorded_timestamp)),
                            "ciu_version": self.ciuVersion,
                            "rpm": self.__locale.toString(self.kiln.rpm, format="f", precision=3),
                            "kiln_trigger_state": not self.kiln.trigger_state,
                            "num_scanners": l,
                            "horizontal_state": 20,
                            "temp_mode": 1, }
        serial_file = """{serial_number:<10d}{c_time:<10d} #{formatted_time:<20s}{ciu_version:s}
{rpm:5s} {kiln_trigger_state:d}
{num_scanners:2d} {horizontal_state:3x} {temp_mode:d}""".format(**serial_file_data)

        for i, s in enumerate(self.kiln.scanners):
            if s.type!='scanner':
                continue
            internalTempKelvin = s.internal_temperature
            convertedInternalTemp = Temperature.kelvinToTemperature(self.temperature_unit, internalTempKelvin)
            statusCode = 0x0
            statusText = "OK"
            if s.internalTemperature.getErrorCode(internalTempKelvin) != 0x0:
                statusCode |= 0x200
                statusText = "BodyTemp_" + s.internalTemperature.getErrorText(internalTempKelvin)
            scanner_data = {"status_code": statusCode,
                            "scanner_num": (i + 1),
                            "status_text": statusText,
                            "space": "",
                            "internal_temp": convertedInternalTemp,
                            "t_unit": self.parsed_temperature_unit}
            scanner_data["error_text"] = "Rcv {scanner_num:d}: {status_text:s}".format(**scanner_data)
            serial_file += "\n{status_code:03X}  #{error_text:<40s} {internal_temp:6.1f} deg{t_unit:1s}".\
                format(**scanner_data)
        return serial_file
