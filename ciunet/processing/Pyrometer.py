import logging

from Qt import QtCore
import numpy

from python_util import util as util
from daq_net.daq import Temperature
from . import Sensor
from . import ConvertedLine

from collections import namedtuple

PyrometerLine = namedtuple('PyrometerLine', ['data', 'last_angle', 'angle'])

class Pyrometer(Sensor.Sensor):
    def __init__(self, scanner, name, config, sensor_index):
        super().__init__(config, sensor_index, scanner.kiln, parent=scanner)
        self.pyrometerType='classic' # 'dali'
        try:
            if config['type']=='classic':        self.pyrometerType='classic' # 'Dali'
            elif config['type']=='dali':        self.pyrometerType='dali' # 'Dali'
        except Exception as e:
            print(e)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.name = name
        self.scanner = scanner
        self.logger.debug("index={}".format(self.index))
        self.logger.debug("config: {}".format(config))
        self.source = str(config["source"])
        if self.pyrometerType=='classic':
            if not self.scanner.multiplexedValuesManager.hasValueByName(self.source):
                raise Exception("Could not find pyrometer input '{}'".format(self.source))
            self.analog_index = self.scanner.multiplexedValuesManager.find(self.source)
        if self.pyrometerType=='dali':
            self.analog_index=int(self.source)
        self.reverse_vertical = util.str2bool(config["reverse_v"])
        self.__t_mode = Temperature.unit[config["temp_unit"]]
        P1_dig = float(config["P1_dig"])
        P1_factor = float(config["P1_factor"])
        P1_offset = float(config["P1_offset"])
        P1_dig += P1_offset
        P1_dig *= P1_factor
        P1_temp = Temperature.temperatureToKelvin(self.__t_mode, float(config["P1_temp"]))
        P2_dig = float(config["P2_dig"])
        P2_factor = float(config["P2_factor"])
        P2_offset = float(config["P2_offset"])
        P2_dig += P2_offset
        P2_dig *= P2_factor
        P2_temp = Temperature.temperatureToKelvin(self.__t_mode, float(config["P2_temp"]))
        self.__factor = (P2_temp - P1_temp) / (P2_dig - P1_dig)
        self.__x1 = P1_dig
        self.__y1 = P1_temp

        self.logger.debug("Created pyrometer with config={}".format(config))

    @QtCore.Slot()
    @util.noexcept
    def receiveLine(self):
        def generate_data(target_pixel, value):
            data = numpy.empty(target_pixel)
            data[:] = numpy.nan
            data[self.mask] = value
            yield data
        if self.pyrometerType=='classic':
            value = self.scanner.multiplexedValuesManager.getValue(self.analog_index)
        elif self.pyrometerType=='dali':
            value = self.scanner.analogValues[self.analog_index]
        else:
            return
        transformed_value = self.__transform(value)
        c = ConvertedLine.ConvertedLineWithGenerator(self.scanner.last_line.time_usec)
        c.generator = generate_data(target_pixel=self.scanner.target_pixel, value=transformed_value)
        self.sigConvertedLine.emit(c, self)

    def __transform(self, value):
        if self.scanner.kiln.transform_temperatures:
            # Kelvin
            value = self.__factor * (value - self.__x1) + self.__y1
        return value

    @property
    def last_trigger(self):
        return self.scanner.last_trigger

    @property
    def next_to_last_trigger(self):
        return self.scanner.next_to_last_trigger

    @property
    def next_to_next_last_trigger(self):
        return self.scanner.next_to_next_last_trigger
