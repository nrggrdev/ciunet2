import logging
import re

from .temperatures.LinearTemperature import LinearTemperature


class TemperaturesManager(object):
    def __init__(self, scanner, config):
        object.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.temperatures = []
        self.parseConfig(scanner, config)

    def parseConfig(self, scanner, config):
        sections = [s for s in config if re.search("^temperature_", s, re.IGNORECASE)]
        self.logger.debug("Temperatures sections: {}".format(sections))
        for section in sections:
            try:
                c = config[section]
                mV = LinearTemperature(scanner, c, section)
                self.temperatures.append(mV)
            except Exception as e:
                self.logger.error("Could not config TemperaturesValue: {}".format(e), exc_info=True)

    def getValueByName(self, name):
        for mv in self.temperatures:
            if name == mv.name:
                return mv.get_temperature()
        raise RuntimeError("Could not find Temperature with name={}".format(name))

    def getValue(self, index):
        return self.temperatures[index].get_temperature()

    def hasValueByName(self, name):
        for mv in self.temperatures:
            if name == mv.name:
                return True
        return False

    def find(self, name):
        for i, mv in enumerate(self.temperatures):
            if name == mv.name:
                return i
        return -1
