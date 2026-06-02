import logging

from PyQt5 import QtCore
import numpy

from python_util import util as util
from daq_net.daq import Temperature


class LinearTemperature(QtCore.QObject):
    def __init__(self, scanner, config, name):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = name
        self.multiplexedValuesManager = scanner.multiplexedValuesManager
        self.source_type = str(config.get("source_type", "scanner"))  # analog or mbed device status
        self.__source = str(config["source"])  # Index of analog_# value used for internal temperature
        self.temp_unit = Temperature.unit[config["temp_unit"]]
        P1_dig = float(config["P1_dig"])
        P1_factor = float(config["P1_factor"])
        P1_offset = float(config["P1_offset"])
        P1_dig += P1_offset
        P1_dig *= P1_factor
        P1_temp = Temperature.temperatureToKelvin(self.temp_unit, float(config["P1_temp"]))
        P2_dig = float(config["P2_dig"])
        P2_factor = float(config["P2_factor"])
        P2_offset = float(config["P2_offset"])
        P2_dig += P2_offset
        P2_dig *= P2_factor
        P2_temp = Temperature.temperatureToKelvin(self.temp_unit, float(config["P2_temp"]))
        self.__factor = (P2_temp - P1_temp) / (P2_dig - P1_dig)
        self.__x1 = P1_dig
        self.__y1 = P1_temp
        self.logger.debug("{}: P1_dig={}, P1_temp={}K, P2_dig={}, P2_temp={}K".format(name, P1_dig, P1_temp, P2_dig, P2_temp))
        self.logger.debug("{}: factor={}, x1={}, y1={}K".format(name, self.__factor, self.__x1, self.__y1))
        self.validate_source(scanner)
        self.logger.debug("Successfully configured LinearTemperature with name={}".format(self.name))

    def validate_source(self, scanner):
        if self.source_type == "scanner":
            index = self.multiplexedValuesManager.find(self.__source)
            if index < 0:
                raise Exception("Invalid temperature source '{}'".format(self.__source))
            self.get_source = lambda: self.multiplexedValuesManager.getValue(index)
        elif self.source_type == "dali":
            self.host = scanner.receiver.ip.toString()
            self.cached_value = numpy.nan
            scanner.kiln.signalGotStatusData.connect(self.getStatusData)
            self.get_source = lambda: self.cached_value
        else:
            raise RuntimeError("Invalid source type: {}".format(self.source_type))

    @QtCore.pyqtSlot(object, object)
    @util.noexcept
    def getStatusData(self, data, host):
        if self.host != host:
            return
        try:
            if self.__source not in data["analog_ins"]:
                raise RuntimeError("Source {} not available.".format(self.__source))
            self.cached_value = data["analog_ins"][self.__source]["value"]
        except Exception as e:
            self.logger.info("Could not calc intern. temperature: {}".format(e))

    def get_temperature(self):
        """
        in Kelvin
        """
        try:
            raw = self.get_source()
            value = self.__factor * (raw - self.__x1) + self.__y1
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("{}: raw={} v={} deg Celsius".format(self.name, raw, Temperature.kelvinToCelsius(value)))
        except Exception as e:
            self.logger.debug("Could not get Internal Temp: {}".format(e))
            value = -1
        return value
