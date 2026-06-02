import logging
import os
import configparser
import threading

import numpy
from PyQt5 import QtCore

from daq_net.daq import Temperature
from python_util import util as util


class Window:
    DEFAULT_VALUE = 1  # Do not set to 0, so users can set 0 as lower limit in TCEM

    def __init__(self):
        self.tmin = Window.DEFAULT_VALUE
        self.tmax = Window.DEFAULT_VALUE
        self.tavg = Window.DEFAULT_VALUE
        self.code = 0


class WindowAlarmChecker(QtCore.QObject):
    def __init__(self, config, kiln_start, kiln_end, parent, t_unit, h_unit):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("WinAlarm")
        self.__outputFile = str(config["outFile"])
        self.__outputFile2 = str(config["outFile"])+".2opc"
        self.__outputFileINI = str(config["outFileINI"])
        self.__configFile = str(config["configFile"])
        self.__configParseInterval = int(config["configParseInterval"])
        self.__configINI_interval = int(config["outFileINI_interval"])
        self.kiln_start = kiln_start
        self.kiln_end = kiln_end
        self.__windows = []
        self.__windowsLock = threading.Lock()
        self.__periodicConfigParser = QtCore.QTimer(self)
        self.__periodicConfigParser.setInterval(1000 * self.__configParseInterval)
        self._t_unit = t_unit
        self._h_unit = h_unit
        self.__ini_writer_timer = QtCore.QTimer(self)
        self.__ini_writer_timer.setInterval(1000 * self.__configINI_interval)

    @QtCore.pyqtSlot()
    @util.noexcept
    def start(self):
        self.logger.debug("Starting Window Alarm checker.")
        self.__periodicConfigParser.timeout.connect(self.__parseConfig, QtCore.Qt.QueuedConnection)
        self.__periodicConfigParser.start()
        self.__ini_writer_timer.timeout.connect(self.__buildINIOutputFile)
        self.__ini_writer_timer.start()

    @QtCore.pyqtSlot()
    @util.noexcept
    def stop(self):
        self.__periodicConfigParser.stop()
        self.__ini_writer_timer.stop()

    @QtCore.pyqtSlot(object)
    @util.noexcept
    def receiveData(self, tcem_image):
        self.logger.debug("Window alarm received data. #Windows={}".format(len(self.__windows)))
        with self.__windowsLock:
            for window in self.__windows:
                kilnLen = self.kiln_end - self.kiln_start

                imgData = tcem_image.composed_image_data  # in Kelvin
                imgLen = imgData.shape[1]

                pos_left = int((window.left - self.kiln_start) / kilnLen * imgLen)
                pos_right = int((window.right - self.kiln_start) / kilnLen * imgLen)

                if pos_left > pos_right:
                    pos_left, pos_right = pos_right, pos_left

                pos_left = max(0, pos_left)
                pos_right = max(0, pos_right)

                pos_left = min(imgLen, pos_left)
                pos_right = min(imgLen, pos_right)

                # Do nothing for empty windows
                if pos_left == pos_right:
                    continue

                data = imgData[:, pos_left:pos_right:]
                if len(data):
                    data = numpy.nan_to_num(data)
                    convertedData = Temperature.convert(Temperature.Kelvin, self._t_unit, data)
                    vMin = numpy.nanmin(convertedData)
                    vMax = numpy.nanmax(convertedData)
                    vAvg = numpy.nanmean(convertedData)
                    window.tmin = vMin
                    window.tmax = vMax
                    window.tavg = vAvg
                    window.code = 0x0
                    if vMin < window.tlow:
                        window.code |= 0x2
                    if vMax > window.tup:
                        window.code |= 0x1
            self.__buildTcemOutputFile()

    def __checkWindows(self, data):
        pass

    @QtCore.pyqtSlot()
    @util.noexcept
    def __parseConfig(self):
        try:
            self.logger.debug("Parsing Window Config file '{}'.".format(self.__configFile))
            if not os.path.exists(self.__configFile):
                raise FileNotFoundError("File {} does not exist".format(self.__configFile))
            settings = configparser.ConfigParser()
            settings.read(self.__configFile)
            windows = []
            for section in settings.sections():
                # Set default values to 1 so TCEM clients can set lower limit to 0 (cannot be negative),
                # and still not get a low-temp alarm
                window = Window()
                left = float(settings[section]["Left"])
                right = float(settings[section]["Right"])
                if left < right:
                    window.left = left
                    window.right = right
                else:
                    window.left = right
                    window.right = left

                window.tlow = float(settings[section]["Tlow"])
                window.tup = float(settings[section]["Tup"])

                windows.append(window)
            with self.__windowsLock:
                self.__windows = windows
        except FileNotFoundError as e:
            self.logger.error("Could not parse window ini file: {}".format(e))
        except Exception as e:
            raise Exception("Could not parse Window config file.") from e

    def __buildTcemOutputFile(self):
        try:
            baseDir = os.path.dirname(self.__outputFile)
            if not os.path.exists(baseDir):
                self.logger.info("Creating window dir: {}".format(baseDir))
                os.makedirs(baseDir)
            with util.save_file.open_savefile(self.__outputFile, "w") as f:
                f.write(self.__buildTcemOutputString())
            with util.save_file.open_savefile(self.__outputFile2, "w") as f:
                f.write(self.__buildTcemOutputString())
        except Exception as e:
            raise Exception("Could not write Window Alarm Output File.") from e
    def getWindowData(self):

        return os.path.join('window',os.path.basename(self.__outputFile)),self.__buildTcemOutputString()

    def __buildTcemOutputString(self):
        combinedAlarm = 0
        for window in self.__windows:
            combinedAlarm |= window.code
        data = {"combinedAlarm": combinedAlarm,
                "numWindows": len(self.__windows),
                "tempUnit": Temperature.text[self._t_unit],
                "filler": "00", }
        out = "{combinedAlarm:d}\n{numWindows:<2d} {tempUnit:2s} {filler:2s}".format(**data)
        out += "\n{:>1s} {:>6s} {:>6s} {:>6s} {:>6s} {:>6s} {:>6s} {:>6s} ".format("#C", "Tmin", "Tmax", "Tavg",
                                                                                   "Left", "Right", "Tlow", "Tup")
        for window in self.__windows:
            data = {"code": window.code,
                    "tmin": window.tmin,
                    "tmax": window.tmax,
                    "tavg": window.tavg,
                    "left": window.left,
                    "right": window.right,
                    "tlow": window.tlow,
                    "tup": window.tup, }
            out += "\n{code:>1d} {tmin:>6.1f} {tmax:>6.1f} {tavg:>6.1f} {left:>6.1f} {right:>6.1f} {tlow:>6.1f} {tup:>6.1f}".\
                format(**data)
        # Add windows
        return out

    @QtCore.pyqtSlot()
    def __buildINIOutputFile(self):
        try:
            windows = self.__windows

            # Checkout base dir
            baseDir = os.path.dirname(self.__outputFileINI)
            if not os.path.exists(baseDir):
                self.logger.info("Creating window INI dir: {}".format(baseDir))
                os.makedirs(baseDir)

            s = configparser.RawConfigParser()
            entries = {"code": "code",
                       "temp_min": "tmin",
                       "temp_max": "tmax",
                       "temp_avg": "tavg",
                       "pos_left": "left",
                       "pos_right": "right",
                       "limit_low": "tlow",
                       "limit_high": "tup",
                       }
            for i, window in enumerate(windows):
                section = "Window_{}".format(i)
                s.add_section(section)
                for key, value in entries.items():
                    s.set(section, key, getattr(window, value))

            with open(self.__outputFileINI, "w") as f:
                s.write(f)
        except Exception as e:
            self.logger.error("Could not write Window Alarm INI Output File: {}".format(e), exc_info=True)
