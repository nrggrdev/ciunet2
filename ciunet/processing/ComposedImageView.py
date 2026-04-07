import warnings
import logging

from Qt import QtCore
import numpy


class ComposedImageViewer(QtCore.QObject):
    """Thermal image consisting of one SingleImage per sensor"""

    def __init__(self, config, image, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.composed_image = image
        self.valid = False
        self.data = None
        self.__defaultMergeFunc = numpy.nanmax

        self.width_reduction_factor = int(config["width_reduction"])
        if self.width_reduction_factor <= 0:
            raise ValueError("Width image reduction factor must be positive.")
        self.height_reduction_factor = int(config["height_reduction"])
        if self.height_reduction_factor <= 0:
            raise ValueError("Height image reduction factor must be positive.")
        self.image_reset_value = float(config.get("image_reset_value", -1))
        if self.image_reset_value < 0:
            self.image_reset_value = numpy.nan

        self.width = self.composed_image.width // self.width_reduction_factor
        self.height = self.composed_image.height // self.height_reduction_factor

        image.signal_image_updates.connect(self.update, QtCore.Qt.DirectConnection)

    @property
    def rawlines(self):
        return self.composed_image.get_num_rawlines()

    @property
    def image(self):
        try:
            if self.composed_image.image_empty():
                return self.get_empty()
            return self.get_reduced_image()
        except Exception:
            self.logger.warning("image error", exc_info=True)
            return self.get_empty()

    def update(self):
        self.valid = False

    def get_empty(self):
        r = numpy.empty((self.height, self.width))
        r[:] = self.image_reset_value
        return r

    def get_reduced_image(self):
        if not self.valid:
            self.data = self.reduce()

            self.valid = True
        return self.data

    def reduce(self):
        source_data = self.composed_image.get_full_data()
        """Block-reduce internal image by width/heigh factor"""
        reduced_data = []
        with warnings.catch_warnings():
            # Suppress warnings about all-NAN slices
            warnings.simplefilter("ignore", category=RuntimeWarning)
            for d in source_data:
                # block-reduce image, using func=nanmax
                try:
                    d=numpy.nan_to_num(d,self.image_reset_value)
                    r = numpy.nanmax(d.reshape((d.shape[0], -1, self.width_reduction_factor)), axis=2)
                    r = numpy.nanmax(r.reshape((-1, self.height_reduction_factor, r.shape[1],)), axis=1)
                    reduced_data.append(r)
                except Exception as e:
                    print('__>')
                    print(e)
            data = self.__defaultMergeFunc(reduced_data, axis=0)
        return data
