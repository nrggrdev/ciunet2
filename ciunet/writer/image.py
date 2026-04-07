import os

from Qt import QtCore
import numpy
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from python_util import util as util


class ImageWriter(QtCore.QObject):
    def __init__(self, composed_image, config, kiln, parent):
        super().__init__(parent)
        self.kiln = kiln
        self.composed_image = composed_image
        self.active = config.get("active", False)
        self.png_filename = str(config["dest"])
        self.png_filename = os.path.abspath(self.png_filename)

    def save_png(self):
        if not self.active:
            return
        data = numpy.nan_to_num(self.composed_image.image)
        data *= 10  # Convert to Dezi-Kelvin, to fill 16bit space between 0K and 6553.6K
#             print(numpy.mean(data), numpy.min(data), numpy.max(data), data.dtype)
        data = data.astype(numpy.uint32)
        img = Image.fromarray(data, mode="I")

        idx = "ggr:"
        info = PngInfo()
        now = util.datetime_helper.current_local_time()
        info.add_text(idx + "time", str(now.timestamp()))
        info.add_text(idx + "time_fmt", str(now))
        info.add_text(idx + "raw_lines", str(self.composed_image.rawlines))
        info.add_text(idx + "width_unit", str(self.kiln.length_unit))
        info.add_text(idx + "height_unit", "degrees")
        info.add_text(idx + "left_pos", str(self.kiln.kiln_start))
        info.add_text(idx + "right_pos", str(self.kiln.kiln_end))

        dir_path = os.path.dirname(self.png_filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with util.save_file.open_savefile(self.png_filename, 'wb') as imageFile:
            img.save(imageFile, format="png", pnginfo=info)

    @QtCore.Slot()
    @util.noexcept
    def registerTrigger(self):
        self.save_png()
