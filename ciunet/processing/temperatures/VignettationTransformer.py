import numpy
import logging

from scipy import interpolate


class VignettationTransformer:
    def __init__(self, filename):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.table = numpy.loadtxt(filename, skiprows=1, delimiter=",")
        self.__validateTable()
        self.x = self.table[:, 0]
        self.y = self.table[:, 1]
        self.logger.debug("x={}".format(self.x))
        self.logger.debug("y={}".format(self.y))
        logging.debug("Imported Transmission Transformation file: {} / shape: {}".format(self.table, self.table.shape))
        self.f = interpolate.interp1d(self.x, self.y, kind="cubic", bounds_error=False, fill_value="extrapolate")
        self.cached_vignetting_matrix = {}

    def get_vignetting_matrix(self, fov_angle, data_length):
        if data_length in self.cached_vignetting_matrix:
            return self.cached_vignetting_matrix[data_length]

        data_angles = numpy.linspace(0.0, fov_angle, data_length)
        vignetting_matrix = self.f(data_angles)
        self.cached_vignetting_matrix[data_length] = vignetting_matrix
        return vignetting_matrix

    def convert(self, fov_angle, data):
        vignetting_matrix = self.get_vignetting_matrix(fov_angle, len(data))
        return vignetting_matrix

    def __validateTable(self):
        if len(self.table.shape) != 2:
            raise UserWarning("Transmission Transformation Error: Invalid csv table shape: {}".format(self.table.shape))
