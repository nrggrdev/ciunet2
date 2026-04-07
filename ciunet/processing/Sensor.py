import logging

import numpy
from Qt import QtCore

from python_util import util as util


def _createMask(kiln, maskfile, targetpixel):
    """ Creates a mask for image composer in image-coordinates
        from a list of user-given mask segments in kiln-coordinates"""
    # Create a empty mask, all entries set to 0
    mask = numpy.zeros(targetpixel, dtype=bool)
    try:

        user_masks = numpy.loadtxt(maskfile, delimiter=",")
        # Reshape the input so we always get a array with 2 columns, N rows
        user_masks = numpy.reshape(user_masks, (-1, 2))
        logging.debug("User input masks: {}".format(user_masks))

        def to_pixel(kiln_pos):
            """Transform kiln-coordinate to image coordinate"""
            return int((kiln_pos - kiln.kiln_start) * targetpixel / (kiln.kiln_end - kiln.kiln_start))

        for left, right in user_masks:
            left_pixel_pos, right_pixel_pos = to_pixel(left), to_pixel(right)

            # We need to ensure left index is smaller for numpy indexing to work.
            if left_pixel_pos > right_pixel_pos:
                left_pixel_pos, right_pixel_pos = right_pixel_pos, left_pixel_pos

            # Cap range between image borders
            left_pixel_pos = max(0, left_pixel_pos)
            right_pixel_pos = min(targetpixel, right_pixel_pos)

            mask[left_pixel_pos:right_pixel_pos] = 1

        logging.debug("Created mask: {}".format(mask))
        return mask
    except UserWarning as e:
        # Assume we have a empty file.
        mask[:] = 1
        return mask
    except Exception as e:
        raise Exception("Could not create Scanner Mask: {}".format(e)) from e


class Sensor(QtCore.QObject):
    """base class for scanner and pyrometer"""
    signal_got_trigger = QtCore.Signal(object)
    sigConvertedLine = QtCore.Signal(object, object)

    def __init__(self, config, sensor_index, kiln, parent):
        super().__init__(parent=parent)
        self.index = sensor_index[0]
        sensor_index[0] += 1
        kiln.sensors[self.index] = self
        self.reverse_vertical = util.str2bool(config["reverse_v"])
        self.vertical_offset = float(config["vertical_offset"])
        if "linedata" in config:
            self.hasLinedata=util.str2bool(config["linedata"])
        else:
            self.hasLinedata=True

        if self.vertical_offset < 0.0:
            raise ValueError("Vertical offset must be positive.")
        if self.vertical_offset > 360.0:
            # Current implementation of vertical line position calculation does
            # not allow for a larget offset, because we do not keep old lines
            # long enough with the current system. 2016-09-15
            raise ValueError("Vertical offset must be less than 360.0.")

        self.target_pixel = kiln.composed_image.width
        self.mask = _createMask(kiln, config["mask"], self.target_pixel)
