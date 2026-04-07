import datetime

import numpy

from .headers import base as base_header
from .headers import extended as extended_header
from . import math_32bit


MAX_WORDS = 2000


class RawSegment(object):
    def __init__(self, data,triggerchannel,lastmbedTime=0,starttime=0,offset=0,lasttime=0,overflows=0):
        super().__init__()
#        print(lastmbedTime)
        self.analogValues=[0,0,0,0,0,0]
        self.overflows=0
        self.time_offset=offset#-starttime
        self.__triggerchannel=triggerchannel

        self.__extract_data(data,lastmbedTime,starttime,offset,lasttime=lasttime,overflows=overflows)

    @property
    def block_time(self):
        return self.block_time_usec / 1e6

    def all_channel_times(self):
        data=[]
        data2={}

        if not self.extended_header_id>6003:
            return {'rising':[],'falling':[]}
        data.append((self.channel_time_rising_0_0,self.channel_time_rising_0_1,self.channel_time_rising_0_2,self.channel_time_rising_0_3,self.channel_time_rising_0_4))
        data.append((self.channel_time_rising_1_0, self.channel_time_rising_1_1, self.channel_time_rising_1_2,
                    self.channel_time_rising_1_3, self.channel_time_rising_1_4))
        data.append((self.channel_time_rising_2_0, self.channel_time_rising_2_1, self.channel_time_rising_2_2,
                    self.channel_time_rising_2_3, self.channel_time_rising_2_4))
        data.append((self.channel_time_rising_3_0, self.channel_time_rising_3_1, self.channel_time_rising_3_2,
                    self.channel_time_rising_3_3, self.channel_time_rising_3_4))
        data.append((self.channel_time_rising_4_0, self.channel_time_rising_4_1, self.channel_time_rising_4_2,
                    self.channel_time_rising_4_3, self.channel_time_rising_4_4))
        data.append((self.channel_time_rising_5_0, self.channel_time_rising_5_1, self.channel_time_rising_5_2,
                    self.channel_time_rising_5_3, self.channel_time_rising_5_4))
        data.append((self.channel_time_rising_6_0, self.channel_time_rising_6_1, self.channel_time_rising_6_2,
                    self.channel_time_rising_6_3, self.channel_time_rising_6_4))
        data.append((self.channel_time_rising_7_0, self.channel_time_rising_7_1, self.channel_time_rising_7_2,
                    self.channel_time_rising_7_3, self.channel_time_rising_7_4))
        data2['rising']=data

        data=[]
        data.append((self.channel_time_falling_0_0, self.channel_time_falling_0_1, self.channel_time_falling_0_2,
                    self.channel_time_falling_0_3, self.channel_time_falling_0_4))
        data.append((self.channel_time_falling_1_0, self.channel_time_falling_1_1, self.channel_time_falling_1_2,
                    self.channel_time_falling_1_3, self.channel_time_falling_1_4))
        data.append((self.channel_time_falling_2_0, self.channel_time_falling_2_1, self.channel_time_falling_2_2,
                    self.channel_time_falling_2_3, self.channel_time_falling_2_4))
        data.append((self.channel_time_falling_3_0, self.channel_time_falling_3_1, self.channel_time_falling_3_2,
                    self.channel_time_falling_3_3, self.channel_time_falling_3_4))
        data.append((self.channel_time_falling_4_0, self.channel_time_falling_4_1, self.channel_time_falling_4_2,
                    self.channel_time_falling_4_3, self.channel_time_falling_4_4))
        data.append((self.channel_time_falling_5_0, self.channel_time_falling_5_1, self.channel_time_falling_5_2,
                    self.channel_time_falling_5_3, self.channel_time_falling_5_4))
        data.append((self.channel_time_falling_6_0, self.channel_time_falling_6_1, self.channel_time_falling_6_2,
                    self.channel_time_falling_6_3, self.channel_time_falling_6_4))
        data.append((self.channel_time_falling_7_0, self.channel_time_falling_7_1, self.channel_time_falling_7_2,
                    self.channel_time_falling_7_3, self.channel_time_falling_7_4))
        data2['falling']=data
        return data2

        try:
            for k in data2.keys():
                data2k=data2[k]
                for dxr in data2k:
                    for dxyr in dxr:
                        dxyr+=self.time_offset
        except Exception as e:
            print("ee",e)

        print (data2)
#        print("<>"*80)

        return data2

    def channel_time(self, channel, rising):
        if rising:
            name = "channel_time_rising_{}_{}".format(channel, 4)
#            return getattr(self, name)+self.time_offset
            return getattr(self, name)#+self.overflows*4294967295
        else:
            name = "channel_time_falling_{}_{}".format(channel, 4)
#            return getattr(self, name)+self.time_offset
            return getattr(self, name)#+self.overflows*4294967295

    @property
    def last_trigger_usec(self):
#        print(self.time_offset)
        try:
            if not self.extended_header_id > 6003:
                return self.last_kiln_trigger_time_usec
            else:
                return self.channel_time(self.__triggerchannel, True) #/ 1e6

        except Exception:
            return self.channel_time(self.__triggerchannel, True)

    @property
    def last_trigger(self):
        if not self.extended_header_id > 6003:
            return self.last_kiln_trigger_time_usec / 1e6
        else:
            return self.channel_time(self.__triggerchannel, True) / 1e6


    @property
    def next_to_last_trigger(self):
        return self.next_to_last_kiln_trigger_time_usec / 1e6


    @property
    def scanner_offline(self):
        return self.operation_state & 0x0001

    @property
    def tireslip_offline(self):
        return self.operation_state & 0x0002

    @property
    def status(self):
        return self.status_information

    @property
    def status_formatted(self):
        if self.status_information == 0:
            return "OK"
        codes = []
        if self.status_information & 0x0001:
            codes.append("OF")  # SSP_FIFO_OVERFLOW
        if self.status_information & 0x0002:
            codes.append("TO")  # SSP_READ_TIMEOUT
        if self.status_information & 0x0004:
            codes.append("KS")  # CONTAINS_KILN_SYNC
        if self.status_information & 0x0008:
            codes.append("NS")  # IS_NOT_SYNCHRONIZED
        if self.status_information & 0x0010:
            codes.append("EKS")  # CONTAINS_EXTERNAL_KILN_SYNC
        return "|".join(codes)

    @property
    def data(self):
        return self.__data

    def no_data(self):
        """Return true if all data is 0 -> Scanner with no data line connected"""
        return not numpy.any(self.data+1)

    def is_first(self):
        return self.block_id == 0

    def is_first_line(self):
        return self.line_id == 0

    def __extract_data(self, data,lastmbedTime,startTime,offset,lasttime=0,overflows=0):
        self._accumulated_header_len = 0
        self.__extract_base_header(data)
        self.__extract_extended_header(data,lastmbedTime,startTime,offset,lasttime=lasttime,overflows=overflows)

        self.__extract_extra_header(data)

        self.__extract_video_data(data)

    def __extract_video_data(self, data):
        n_pixel = self.num_data_words
        dt = "<u%d" % self.data_word_length
#        print(n_pixel,self._accumulated_header_len)
        self.__data = numpy.frombuffer(data, dtype=dt, count=n_pixel, offset=self._accumulated_header_len)
#        if self.extended_header_id == 6007:
#            self.__data = numpy.frombuffer(data, dtype=dt, count=n_pixel, offset=412)
#            print('6007','412',self._accumulated_header_len)
#        else:
#            self.__data = numpy.frombuffer(data, dtype=dt, count=n_pixel, offset=self._accumulated_header_len)

    def __extract_base_header(self, data):
        base_header.base_header_parser.parse_into_raw_segment(self, data, offset=self._accumulated_header_len)
        if self.dali_packet_identifier != base_header.valid_dali_packet_identifier:
            raise ValueError("Invalid dali_packet_identifier.")
        self._accumulated_header_len += base_header.base_header_parser.size

    def __extract_extended_header(self, data,lastmbedTime,startTime,offset,lasttime=0,overflows=0):
        eh_parser = extended_header.extended_header_parser[self.extended_header_id]
        toffset,lastmbedTime,overflows=eh_parser.parse_into_raw_segment(self, data,lastmbedTime,startTime, offset=self._accumulated_header_len,offset2=offset,lasttime=lasttime,overflows=overflows)
        self.overflows=overflows
        anas=[]
        if self.extended_header_id==6007:
            for i in range(6):
                prop=f"analog_ins_{i}"
                anas.append(getattr(self, prop))
            self.analogValues=anas
        self.time_offset=toffset
        self.lastTime=lastmbedTime
        # Avoid performance problems/crashes
        #print(self.num_data_words)
        if self.num_data_words > MAX_WORDS:
            raise ValueError("num_data_words too high.")

        self._accumulated_header_len += eh_parser.size

    def __extract_extra_header(self, _data):
        # Just skip this header for now
        try:
            self._accumulated_header_len += int(self.receiver_specific_extended_header_len)
        except AttributeError:
            return


    def __str__(self, *args, **kwargs):
        return "RawSegment(gid={};id={};lid={};nw_id={};vbits={};l={})".format(self.global_block_id,
                                                                 self.block_id,
                                                                 self.line_id,
                                                                 self.network_id,
                                                                 self.video_bits,
                                                                 self.num_data_words)

    def __repr__(self, *args, **kwargs):
        return "RawSegment({})".format(["{}: {}".format(k, v) for k, v in self.__dict__.items()])
