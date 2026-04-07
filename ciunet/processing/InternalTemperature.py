import logging


from daq_net.daq import Temperature


class InternalTemperature(object):
    def __init__(self, scanner, config):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__source = str(config["source"])  # Name of analog_# value used for internal temperature
        self.temp_unit = Temperature.unit[config["temp_unit"]]
        self.__lowerLimit = Temperature.temperatureToKelvin(self.temp_unit, float(config["lowerLimit"]))
        self.__upperLimit = Temperature.temperatureToKelvin(self.temp_unit, float(config["upperLimit"]))
        self.validate_source(scanner)
        self.valid = False

    def validate_source(self, scanner):
        if not scanner.temperatureManager.hasValueByName(self.__source):
            raise Exception("Invalid internal temperature source '{}'".format(self.__source))
        index = scanner.temperatureManager.find(self.__source)
        self.get_source = lambda: scanner.temperatureManager.getValue(index)

    def getErrorCode(self, temp):
        errorCode = 0x0
        if temp < 0:
            errorCode |= 0x4
        if temp < self.__lowerLimit:
            errorCode |= 0x2
        if temp > self.__upperLimit:
            errorCode |= 0x1
        return errorCode

    def getErrorText(self, temp):
        errorCode = self.getErrorCode(temp)
        text = ""
        if errorCode == 0x0:
            return "OK"
        if errorCode & 0x2:
            text += "LOW"
        if errorCode & 0x1:
            text += "HIGH"
        if errorCode & 0x4:
            text += "NA"
        return text

    def calculate(self):
        """Calculate internal temperature in Kelvin"""
        try:
            value = self.get_source()
            # self.logger.debug("Internal Temp: v={:.2f} deg Celsius".format(Temperature.kelvinToCelsius(value)))
        except Exception as e:
            self.logger.debug("Could not get Internal Temp: {}".format(e))
            value = 0
        return value

    def invalidate(self):
        """Invalidates the cached temperature value"""
        self.valid = False

    def get_value(self):
        """Get internal temperature on-demand, with caching"""
        if not self.valid:
            self.__value = self.calculate()
        return self.__value
