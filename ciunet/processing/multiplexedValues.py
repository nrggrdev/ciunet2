import logging
import re

import numpy
from python_util.util.MovingValue import MovingValue
from python_util import util


class MultiplexedValue(object):
    def __init__(self, name, startPos, endPos, size, composer, analog_reference_point):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = name
        self.startPos = startPos
        self.endPos = endPos
        self.composer = composer
        self.analog_reference_point = analog_reference_point
        self.lines = MovingValue(size)
        self.valid = False

    @property
    def value(self):
        if not self.valid:
            self.__value = self._calculate_value()
        return self.__value

    def parseLine(self, video_data):
        try:
            self.valid = False
            value = self._calculate_value_of_line(video_data)
            self.lines.add(value)
        except Exception as e:
            self.logger.info("Could not parse line: {}".format(e))

    def _calculate_value(self):
        return self.lines.mean

    def _calculate_value_of_line(self, video_data):
        dataLen = len(video_data)
        start_angle = self.startPos + self.analog_reference_point
        start_angle = start_angle % 360.0
        start_pos = int((start_angle / 360.0) * dataLen)
        end_angle = self.endPos + self.analog_reference_point
        end_angle = end_angle % 360.0
        end_pos = int((end_angle / 360.0) * dataLen)
        if start_pos >= 0 and start_pos <= end_pos:
            multiplex_data = video_data[start_pos:end_pos]
        else:
            # In this case we have to compose data from [start_pos:] and [:end_pos]
            multiplex_data = numpy.concatenate((video_data[start_pos:], video_data[:end_pos]))
        return self.composer(multiplex_data)

    def __str__(self):
        return "[MultiPlexedValue {}/{}: sP={}, eP={}]".format(self.name, self.startPos, self.endPos)


class MultiplexedValuesManager:
    def __init__(self, scanner, config):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.multiplexedValues = []
        self.parseConfig(scanner, config)

    def parseConfig(self, scanner, config):
        valid_analog_reference_point = {"video_sync": 0,
                                        "fov_middle": scanner.fov_angle / 2.0,
                                        "t0": scanner.fov_angle / 2.0 + 180.0,
                                        }
        analog_reference_point = config["analog_reference_point"]
        if analog_reference_point in valid_analog_reference_point.keys():
            self.logger.debug("Analog reference point chosen: {}".format(analog_reference_point))
            self.analog_reference_point = valid_analog_reference_point[analog_reference_point]
        else:
            raise ValueError("Invalid analog reference point {} not valid ({}).".
                             format(analog_reference_point, valid_analog_reference_point.keys()))
        
        analog_reference_offset = float(config["analog_reference_offset"])
        analog_reference_offset = analog_reference_offset % 360.0
        self.analog_reference_point += analog_reference_offset
        self.analog_reference_point = self.analog_reference_point % 360.0
        self.logger.info("Analog reference point relative to video sync: {}".format(self.analog_reference_point))

        sections = [s for s in config.sections if re.search("analog", s, re.IGNORECASE)]
        logging.debug("MultiplexedValues sections: {}".format(sections))
        for section in sections:
            try:
                c = config[section]
                name = str(c["name"])
                startPos = float(c["startPos"]) % 360.0
                endPos = float(c["endPos"]) % 360.0
                composer = getattr(numpy, c["composer"])
                size = int(c.get("size", 20))
                mV = MultiplexedValue(name, startPos, endPos, size, composer, self.analog_reference_point)
                self.multiplexedValues.append(mV)
            except Exception as e:
                raise Exception("Could not config MultiplexedValue.") from e

    def parseLine(self, video_data):
        """
        :type rawLine: RawLine
        """
        for v in self.multiplexedValues:
            v.parseLine(video_data)

    def getValue(self, index):
        return self.multiplexedValues[index].value

#     def getValueByName(self, name):
#         for mv in self.multiplexedValues:
#             if name == mv.name:
#                 return mv.value
#         raise RuntimeError("Could not find MultiplexedValue with name={}".format(name))

    def hasValueByName(self, name):
        for mv in self.multiplexedValues:
            if name == mv.name:
                return True
        return False

    def find(self, name):
        for i, mv in enumerate(self.multiplexedValues):
            if name == mv.name:
                return i
        return -1
