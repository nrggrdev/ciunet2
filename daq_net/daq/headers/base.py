import struct


class BaseHeader(struct.Struct):
    def __init__(self):
        super().__init__("iiii")

    def parse_into_raw_segment(self, segment, buffer, offset=0):
        (segment.dali_packet_identifier, segment.total_packet_length,
            segment.extended_header_length, segment.extended_header_id) = self.unpack_from(buffer, offset)


base_header_parser = BaseHeader()
valid_dali_packet_identifier = 9182