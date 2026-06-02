"""
Bau von DaLi-NETA UDP-Paketen (Scanner-Datenstrom).

Wiederverwendet die *echten* Header-Parser aus ``daq_net.daq.headers``, damit die
erzeugten Pakete byte-genau zu dem passen, was ``RawSegment`` / ``DaLiReceiver``
erwartet (gleiche struct-Definition -> gleiches Alignment).

Ein Scanner sendet pro Linie (= eine Umdrehung) mehrere Segmente:
  - base header (16 B): packet-id 9182, laengen, extended_header_id
  - extended header (z.B. 6007, 388 B): metadaten + analog-werte
  - num_data_words * uint16 video-daten

Die Segmente einer Linie haben aufsteigende ``block_id`` (0..N), wobei block_id==0
den Linienanfang markiert (``RawSegment.is_first()``).
"""

import numpy

from daq_net.daq.headers import base as base_header
from daq_net.daq.headers import extended as extended_header

# Standard-Header-Variante: enthaelt Zeit-Kanaele (8x5) + 6 Analog-Eingaenge.
DEFAULT_EXTENDED_HEADER_ID = 6007

VIDEO_DTYPE = "<u2"          # uint16 little-endian, passend zu RawSegment "<u2"
DATA_WORD_LENGTH = 2         # bytes pro video-wort
DEFAULT_VIDEO_BITS = 14      # nutzbare bits pro wort (0..16383)


class SegmentBuilder:
    """Baut einzelne RawSegment-kompatible UDP-Datagramme."""

    def __init__(self, extended_header_id=DEFAULT_EXTENDED_HEADER_ID,
                 video_bits=DEFAULT_VIDEO_BITS, device_id=1, scanner_type=1):
        self.base_parser = base_header.base_header_parser
        self.ext_id = extended_header_id
        self.ext_parser = extended_header.extended_header_parser[extended_header_id]
        self.video_bits = video_bits
        self.device_id = device_id
        self.scanner_type = scanner_type
        # Welche Felder sind float ('f') -> muessen 0.0 statt 0 sein.
        self._float_fields = {
            name for name in self.ext_parser.names if name.startswith("analog_ins")
        }

    def build_segment(self, video_words, *, image_id, line_id, block_id,
                      global_block_id, network_id, block_time_usec,
                      trigger_time_usec=0, status_information=0,
                      analog_ins=None):
        """
        Baut ein komplettes Datagramm (bytes) fuer ein Segment.

        ``video_words``: 1D-numpy-array (uint16) der Videowerte dieses Segments.
        """
        video = numpy.asarray(video_words, dtype=VIDEO_DTYPE)
        num_words = int(video.size)

        fields = {name: 0 for name in self.ext_parser.names}
        for name in self._float_fields:
            fields[name] = 0.0

        fields["data_word_length"] = DATA_WORD_LENGTH
        fields["video_bits"] = self.video_bits
        fields["num_data_words"] = num_words
        if "scanner_type" in fields:
            fields["scanner_type"] = self.scanner_type
        if "device_id" in fields:
            fields["device_id"] = self.device_id
        fields["image_id"] = image_id
        fields["line_id"] = line_id
        fields["block_id"] = block_id
        fields["global_block_id"] = global_block_id
        fields["network_id"] = network_id
        fields["status_information"] = status_information
        fields["last_image_line_num"] = 0
        fields["block_time_usec"] = block_time_usec & 0xFFFFFFFF

        # Trigger (Ofen-Sync) ueber channel_time_rising_<ch>_4. RawSegment liest
        # bei 6007 last_trigger_usec = channel_time(triggerchannel, rising).
        if trigger_time_usec:
            for name in fields:
                if name.startswith("channel_time_rising_") and name.endswith("_4"):
                    fields[name] = trigger_time_usec & 0xFFFFFFFF

        if analog_ins is not None:
            for i, val in enumerate(analog_ins):
                key = "analog_ins_{}".format(i)
                if key in fields:
                    fields[key] = float(val)

        ext_bytes = self.ext_parser.pack(*[fields[n] for n in self.ext_parser.names])

        total_len = self.base_parser.size + self.ext_parser.size + video.nbytes
        base_bytes = self.base_parser.pack(
            base_header.valid_dali_packet_identifier,
            total_len,
            self.ext_parser.size,
            self.ext_id,
        )
        return base_bytes + ext_bytes + video.tobytes()


def split_line_into_segments(line_words, words_per_segment):
    """Teilt ein Linien-Array in Bloecke von je <= words_per_segment Worten."""
    n = len(line_words)
    return [line_words[i:i + words_per_segment]
            for i in range(0, n, words_per_segment)]
