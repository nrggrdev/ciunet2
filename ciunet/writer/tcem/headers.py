from ctypes import *
import time


cMaxRawChannels = 3
RAW_HEADER_VERSION = 103
MAXSEG = 31
# from ciuvideoDoc.h


class T_SCANNER_CALIB(Structure):
    _pack_ = 2
    _fields_ = [("digref1", c_int16), \
				("digref2", c_int16), \
				("tempref1", c_float), \
				("tempref2", c_float), \
				("factorref1", c_float), \
				("factorref2", c_float), \
				("tempextref", c_float), \
				("digextref", c_int16), \
				("a", c_float), \
				("b", c_float), \
				("c", c_float), \
				("u0", c_float), \
				("model", c_char * 20), \
				("serialno", c_char * 20), \
				("description", c_char * 100), \
				("a_mode", c_int16), \
				("windowtemp", c_float), \
				("windowtransm", c_float), \
				("ae", c_float), \
				("ee", c_int16)]


class T_CHANNEL_INFO(Structure):
    _pack_ = 2
    _fields_ = [("nSizeX", c_int16), \
				("nSizeY", c_int16), \
				("nFileOffset", c_int), \
				("nBrightness", c_int16), \
				("nContrast", c_int16), \
				("nBands", c_int16), \
				("szVideoNorm", c_char * 8), \
				("nDignMux", c_int16), \
				("filler", c_char * 4)]
# #        def __init_(self,size):
# #                self.nSizeX=size[0]
# #		self.nSizeY=size[1]
# #		self.nFileOffset=nFileOffset
# #		self.nBrightness=nBrightness
# #		self.nContrast=nContrast
# #		self.nBands=nBands
# #		self.szVideoNorm=szVideoNorm
# #		self.nDignMux=nDignMux


class T_RAWIMAGE(Structure):
    _pack_ = 2
    _fields_ = [("identifier", c_char * 10), \
				("company", c_char * 10), \
				("header_length", c_int16), \
				("header_version", c_int16), \
				("recorded_timestamp", c_long), \
				("recorded_datetime", c_char * 22), \
				("nChannels", c_int16), \
				("info", T_CHANNEL_INFO * cMaxRawChannels), \
				("nBytesPerPixel", c_int16), \
				("nBits", c_int16), \
				("ciu_version", c_char * 10), \
				("bFieldMode", c_int16), \
				("filler", c_char * 100), \
				("serialno", c_long)]

    def getOffset(self, channel):
        offset = 256
        if channel > 0:return self.getOffset(channel - 1) + self.info[channel - 1].nSizeX * self.info[channel - 1].nSizeY * self.info[channel - 1].nBands
        else: return offset
        """    
    def __init__(self,nChannels=1,info=[T_CHANNEL_INFO(),T_CHANNEL_INFO(),T_CHANNEL_INFO()],nBytesPerPixel=3,nBits=0,serialno=0):
            self.identifier='RAWIMAGE'
            self.company='GESOTEC'
            self.header_length=512
            self.header_version=RAW_HEADER_VERSION
            self.recorded_timestamp=int(time.time())
            self.recorded_datetime= time.strftime('%d.%m.%Y %H:%M:%S',time.localtime(self.recorded_timestamp))
            self.nChannels=nChannels
            self.info=info
            self.nBytesPerPixel=nBytesPerPixel
            self.nBits=nBits
            self.ciu_version='new0.1'
            self.bFieldMode=-1
            self.serialno=serialno
"""        

class ScannerSegment(Structure):
    _pack_ = 2
    _fields_ = [("scannerNumber", c_int8), \
				("left", c_float), \
				("right", c_float)]


class T_SCANDATA(Structure):
    _pack_ = 2
    _fields_ = [("first_pixel", c_int16), \
				("last_pixel", c_int16), \
				("calib", T_SCANNER_CALIB)]


class T_CIUIMAGE(Structure):
    _pack_ = 2
    _fields_ = [("identifier", c_char * 10), \
				("company", c_char * 10), \
				("header_length", c_int16), \
				("header_version", c_int16), \
				("serial_number", c_char * 12), \
				("description", c_char * 120), \
				("index", c_int16), \
				("recorded_timestamp", c_int32), \
				("recorded_datetime", c_char * 22), \
				("record_interval", c_int32), \
				("no_profile_lines", c_int16), \
				("pixels_per_line", c_int16), \
				("no_image_lines", c_int16), \
				("no_raw_image_lines", c_int16), \
				("imaging_formula", c_int16), \
				("bytes_per_pixel", c_int16), \
				("bits_per_pixel", c_int16), \
				("tscale_tlow", c_double), \
				("tscale_tup", c_double), \
				("hscale_low", c_double), \
				("hscale_high", c_double), \
				("vscale_low;", c_double), \
				("vscale_high", c_double), \
				("vscale_length", c_double), \
				("obj_distance", c_double), \
				("hscale_linearised", c_int16), \
				("fov_unit", c_char * 2), \
				("length_unit", c_char * 2), \
				("temp_unit", c_char * 2), \
				("auto_start_level", c_double), \
				("auto_start_slope", c_int16), \
				("auto_start_enable", c_int16), \
				("auto_end_level", c_double), \
				("auto_end_slope", c_int16), \
				("auto_end_enable", c_int16), \
				("auto_window_low", c_int16), \
				("auto_window_high", c_int16), \
				("edge_level", c_double), \
				("edge_enable", c_int16), \
				("tamb", c_double), \
				("tatm", c_double), \
				("eps_obj", c_double), \
				("tau_atm", c_double), \
				("t_mode", c_int16), \
				("nscanners", c_int16), \
				("scan_data", T_SCANDATA * 4), \
				("ciu_version", c_char * 10), \
				("fixed_aspect", c_int16), \
				("pixelaspect_ytox", c_float), \
				("spectral_channel", c_int16), \
				("m_segmentNumber", c_int16), \
				("segments", ScannerSegment * MAXSEG), \
				("filler", c_char * 49)
                ]
