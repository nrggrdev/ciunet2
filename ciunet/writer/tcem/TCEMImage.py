import numpy
import warnings
import logging
import datetime

from ctypes import sizeof
from PyQt5 import QtCore

from .headers import T_CIUIMAGE
from daq_net.daq import Temperature


class TCEMImage(object):
    def __init__(self, composed_image, tcem_manager, config):
        super().__init__()
        self.logger = logging.getLogger("TCEMImage")
        self.header = self.create_header(tcem_manager, config)
        self.header.pixels_per_line = composed_image.width
        self.header.no_image_lines = composed_image.height
        self.kelvin_profiles = None
        self.composed_image = composed_image
        temperature_resolution = (self.header.tscale_tup - self.header.tscale_tlow) / (2 ** self.header.bits_per_pixel - 1)
        self.logger.info("TCEM Image temperature resolution: {}°C".format(temperature_resolution))
        self.data_ok=False

    def update_data(self, transform_temperatures):
        """Update data from composed image"""

        self.composed_image_data = self.composed_image.image  # get max over scanner dimension
        self.tcem_image_data = self.adjust_data(self.composed_image_data, transform_temperatures)
        self.kelvin_profiles = self.build_profiles()
        self.tcem_profiles = self.adjust_data(self.kelvin_profiles, transform_temperatures)
        if not transform_temperatures:
            self.data_ok=True
        else:

            x= Temperature.kelvinToCelsius(self.composed_image_data)
            self.data_ok=True
#            self.data_ok = numpy.min(x) > self.composed_image.image_reset_value


    def build_profiles(self):
        """Build TCEM profile data"""
        profile_types = {0: numpy.nanmin, 1: numpy.nanmax, 2: numpy.nanmean}
        nProfiles = self.header.no_profile_lines
        profiles = []
        data = self.composed_image_data
        for i in range(nProfiles):
            with warnings.catch_warnings():
                # Suppress warnings about all-NAN slices
                warnings.simplefilter("ignore", category=RuntimeWarning)
                x = numpy.array(profile_types[i](data, axis=0))
                # if i==0:
                #     self.data_ok=numpy.average(x)>270
                #     print(numpy.average(x))
                #     print('data_ok'*80)
                #     print(self.data_ok)
                profiles.append(x)
        return profiles

    def adjust_data(self, data, transform_temperatures):
        """Adjust composed image data to tcem specific format"""
        # TCEM internal temperature data is always in Celsius
        # 1D-DAQ composed image is in Kelvin
        if not transform_temperatures:
            # Digital values are mapped directly, no transformation applied
            return data

        data = Temperature.kelvinToCelsius(data)

        tlow = self.header.tscale_tlow
        tup = self.header.tscale_tup
        dtemp = tup - tlow
        v_min = 0
        v_max = (2 ** self.header.bits_per_pixel - 1)
        transformed = (data - tlow) * (v_max - v_min) / dtemp
        cut_off = numpy.clip(transformed, v_min, v_max)  # safety check
        return cut_off

    def create_header(self, tcem_manager, config):
        """Initialize TCEM image header"""
        imgheader = T_CIUIMAGE()
        imgheader.identifier = b"CIUIMAGE"
        imgheader.company = b"GESOTEC"
        assert(sizeof(imgheader) == 1536)
        imgheader.header_length = sizeof(imgheader)
        imgheader.version = 5000
        imgheader.serial_number = b"0"
        imgheader.description = b"CIU-NETx %s image. %s" % (QtCore.QCoreApplication.applicationVersion().
                                                            encode("ascii"),
                                                            tcem_manager.kiln.description)
        imgheader.index = tcem_manager.ciu_index
        imgheader.recorded_timestamp = 0
        imgheader.recorded_datetime = "{:%d.%m.%Y %H:%M:%S}".format(datetime.datetime.now()).encode()
        imgheader.record_interval = -1
        imgheader.no_profile_lines = 3
        imgheader.pixels_per_line = 0
        imgheader.no_image_lines = 0
        imgheader.no_raw_image_lines = 0
        imgheader.imaging_formula = 0
        imgheader.bytes_per_pixel = 2
        imgheader.bits_per_pixel = int(config.get("bits_per_pixel", 16))
        imgheader.tscale_tlow = float(config.get("tscale_tlow", Temperature.celsiusNP))
        imgheader.tscale_tup = float(config.get("tscale_tup", 2048))
        imgheader.hscale_low = tcem_manager.kiln.kiln_start
        imgheader.hscale_high = tcem_manager.kiln.kiln_end
        imgheader.vscale_low = config["vscale_low"]
        imgheader.vscale_high = config["vscale_high"]
        imgheader.vscale_length = 0
        imgheader.obj_distance = 0
        imgheader.hscale_linearised = 1
        # D = degree,
        imgheader.fov_unit = tcem_manager.horizontal_unit
        
        vertical_length_unit = config["vertical_length_unit"]
        imgheader.length_unit = vertical_length_unit.encode("ascii")  # d is interpreted as degree by TCEM
        imgheader.temp_unit = b"C"  # C,F,K
        imgheader.auto_start_level = 0.0
        imgheader.auto_start_slope = 0
        imgheader.auto_start_enable = 0
        imgheader.auto_end_level = 0.0
        imgheader.auto_end_slope = 0
        imgheader.auto_end_enable = 0
        imgheader.auto_window_low = 0
        imgheader.auto_window_high = 0
        imgheader.edge_level = 0.0
        imgheader.edge_enable = 0
        imgheader.tamb = 0.0
        imgheader.tatm = 0.0
        imgheader.eps_obj = 0.0
        imgheader.tau_atm = 0.0
        imgheader.t_mode = 0
        imgheader.ciu_version = tcem_manager.ciuVersion.encode()
        imgheader.fixed_aspect = 0
        imgheader.pixelaspect_ytox = 0.0
        imgheader.spectral_channel = 0
        imgheader.m_segmentNumber = 0
        imgheader.filler = b""
        # self.ciuStartIndex=80
        # self.serialfile     =   os.path.join(self.serialPath,'serial%i.CIU'%self.ciuStartIndex)

        return imgheader
