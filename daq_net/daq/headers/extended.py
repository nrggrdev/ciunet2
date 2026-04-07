import struct

extended_header_parser = {}


class ExtendedHeaderParser(struct.Struct):
    c=2**32-1

    def __init__(self, conf):
        struct_format = "".join(code for _name, code in conf)
        self.time_offset=0
        self.last_time=0
        self.names = [name for name, _code in conf]
        super().__init__(struct_format)

    def parse_into_raw_segment(self, segment, buffer,lastmbedTime,startTime, offset=0,offset2=0,lasttime=0,overflows=0):
        results = self.unpack_from(buffer, offset)
        self.time_offset=offset2
        for i, result in enumerate(results):
            setattr(segment, self.names[i], result)
#            print(self.names[i],result)
#        if segment.block_time_usec<lasttime:
    #        segment.block_time_usec+=overflows*4294967295
        segment.block_time_usec+=overflows*4294967295
        segment.block2= segment.block_time_usec
#        if segment.block_time_usec<lastmbedTime:
#            self.time_offset=offset2+2**32-1
        segment.block2+=self.time_offset
#        print (segment.block2,segment.block_time_usec,lastmbedTime,self.time_offset)
        segment.block_time_usec+=self.time_offset

        return self.time_offset,segment.block_time_usec,overflows
        return 0
#            segment.block_time_usec+=round(lastmbedTime/self.c)*self.c
#        segment.block_time_usec+=(lt-st)


extended_header_parser[6002] = ExtendedHeaderParser([("scanner_type", "H"),
                                ("data_word_length", "H"),
                                ("num_data_words", "H"),
                                ("video_bits", "H"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("next_to_last_kiln_trigger_time_usec", "I"),
                                ("last_kiln_trigger_time_usec", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("receiver_specific_extended_header_len", "i"),
                                ("receiver_specific_extended_header_id", "i")
                                ])

extended_header_parser[6003] = ExtendedHeaderParser([("scanner_type", "H"),
                                ("data_word_length", "H"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                #("PADDING1", "V2"),
                                ("video_bits", "H"),
                                #("PADDING2", "V2"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("next_to_last_kiln_trigger_time_usec", "I"),
                                ("last_kiln_trigger_time_usec", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("receiver_specific_extended_header_len", "i"),
                                ("receiver_specific_extended_header_id", "i")
                                ])


extended_header_parser[6004] = ExtendedHeaderParser([("scanner_type", "H"),
                                ("data_word_length", "H"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                #("PADDING1", "V2"),
                                ("video_bits", "H"),
                                #("PADDING2", "V2"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "I"),
                                *(("channel_time_rising_{}".format(i), "I") for i in range(8)),
                                *(("channel_time_falling_{}".format(i), "I") for i in range(8)),
                                ])


extended_header_parser[6005] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                *(("channel_time_rising_{}".format(i), "I") for i in range(8)),
                                *(("channel_time_falling_{}".format(i), "I") for i in range(8)),
                                ])

extended_header_parser[6006] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                *(("channel_time_rising_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("channel_time_falling_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                ])
extended_header_parser[6007] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                *(("channel_time_rising_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("channel_time_falling_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("analog_ins_{}".format(i), "f") for i in range(6)),
                                ])

extended_header_parser[6008] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                ("property", "B"),
                                ("value", "10s"),
                                *(("channel_time_rising_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("channel_time_falling_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("analog_ins_{}".format(i), "f") for i in range(6)),
                                ])

extended_header_parser[6009] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("block_time_overflow", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                ("property", "B"),
                                ("value", "10s"),
                                *(("channel_time_rising_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("channel_time_falling_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("analog_ins_{}".format(i), "f") for i in range(6)),
                                ])



extended_header_parser[6010] = ExtendedHeaderParser([
                                ("data_word_length", "B"),
                                ("video_bits", "B"),
                                ("num_data_words", "H"),
                                ("device_id", "I"),
                                ("image_id", "I"),
                                ("line_id", "I"),
                                ("block_id", "I"),
                                ("global_block_id", "I"),
                                ("network_id", "I"),
                                ("status_information", "I"),
                                ("last_image_line_num", "i"),
                                ("block_time_usec", "I"),
                                ("operation_state", "H"),
                                ("general_state", "H"),
                                ("property", "B"),
                                ("value", "10s"),
    *(("channel_time_rising_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("channel_time_falling_{}_{}".format(i, j), "I") for i in range(8) for j in range(5)),
                                *(("analog_ins_{}_{}".format(i,j), "f") for i in range(6) for j in range(5)),
                                ])

if __name__=="__main__":
    start=6002
    for i in range(len(extended_header_parser)):
        print(f"header {i+start}: {(extended_header_parser[i+start].size)}")
