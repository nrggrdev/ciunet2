#!/usr/bin/env python3
"""
Scanner-Simulator: sendet einen DaLi-NETA-kompatiblen UDP-Datenstrom.

Erzeugt fortlaufend Scanner-"Linien" (je eine Umdrehung), zerteilt sie in
Segmente und verschickt jedes Segment als UDP-Datagramm -- byte-genau so, wie
es ``daq_net.daq.receiver.DaLiReceiver`` (und damit die echte ciunet-Anwendung)
erwartet.

Beispiele:
  # Unicast an localhost, Standardmuster "kiln", 20 Linien/s
  python -m simulator.scanner_simulator --host 127.0.0.1 --port 51002

  # Multicast wie eine echte DaLi-NETA
  python -m simulator.scanner_simulator --multicast 239.1.1.1 --port 51002

  # anderes Muster + andere Linienlaenge / Rate
  python -m simulator.scanner_simulator --pattern stripes --length 4096 --fps 30

Wichtig: ``DaLiReceiver`` akzeptiert nur Datagramme, deren Absender-IP der in der
Scanner-Config eingestellten ``source`` entspricht. Fuer lokale Tests also in der
Scanner-.ini ``source = 127.0.0.1`` (oder die IP dieses Rechners) setzen.
"""

import argparse
import socket
import struct
import sys
import time

import numpy

# Erlaube sowohl "python -m simulator.scanner_simulator" als auch direkten Aufruf.
if __package__ in (None, ""):
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from simulator.dali_protocol import SegmentBuilder, split_line_into_segments
    from simulator.patterns import PATTERNS
else:
    from .dali_protocol import SegmentBuilder, split_line_into_segments
    from .patterns import PATTERNS


def build_socket(args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if args.multicast:
        ttl = struct.pack("b", args.ttl)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        if args.interface:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                            socket.inet_aton(args.interface))
        # Auch lokal empfangbar machen
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    return sock


def run(args):
    target = (args.multicast or args.host, args.port)
    sock = build_socket(args)
    builder = SegmentBuilder(extended_header_id=args.header_id,
                             video_bits=args.video_bits)
    pattern_fn = PATTERNS[args.pattern]

    line_interval = 1.0 / args.fps
    line_id = 0
    global_block_id = 0
    network_id = 0
    image_id = 0
    t0 = time.time()
    last_trigger_usec = 0
    next_trigger_line = args.trigger_period

    print("Scanner-Simulator -> {}:{}  ({})  Muster='{}'  Laenge={}  {:.0f} Linien/s"
          .format(target[0], target[1],
                  "multicast" if args.multicast else "unicast",
                  args.pattern, args.length, args.fps))
    print("Header-ID={}  video_bits={}  words/segment={}  Strg+C zum Beenden"
          .format(args.header_id, args.video_bits, args.words_per_segment))

    try:
        while True:
            line_start = time.time()
            block_time_usec = int((line_start - t0) * 1e6)

            # Trigger (Ofen-Sync) periodisch setzen
            if args.trigger_period and line_id >= next_trigger_line:
                last_trigger_usec = block_time_usec
                next_trigger_line += args.trigger_period

            video = pattern_fn(args.length, line_id, video_bits=args.video_bits)
            analog = [25.0, 26.0, float(video.min()), float(video.max()), 0.0, 0.0]

            segments = split_line_into_segments(video, args.words_per_segment)
            for block_id, seg_words in enumerate(segments):
                pkt = builder.build_segment(
                    seg_words,
                    image_id=image_id,
                    line_id=line_id,
                    block_id=block_id,
                    global_block_id=global_block_id,
                    network_id=network_id,
                    block_time_usec=block_time_usec,
                    trigger_time_usec=last_trigger_usec,
                    analog_ins=analog,
                )
                sock.sendto(pkt, target)
                global_block_id += 1
                network_id += 1

            line_id += 1
            if args.lines and line_id >= args.lines:
                break

            # Linienrate einhalten
            elapsed = time.time() - line_start
            sleep = line_interval - elapsed
            if sleep > 0:
                time.sleep(sleep)
            if line_id % max(1, int(args.fps)) == 0:
                sys.stdout.write("\r  gesendete Linien: {}   ".format(line_id))
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nBeendet. {} Linien gesendet.".format(line_id))
    finally:
        sock.close()


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DaLi-NETA Scanner UDP-Simulator")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--host", default="127.0.0.1",
                     help="Ziel-IP fuer Unicast (default 127.0.0.1)")
    grp.add_argument("--multicast", default=None,
                     help="Multicast-Gruppe (z.B. 239.1.1.1) statt Unicast")
    p.add_argument("--port", type=int, default=51002, help="Ziel-UDP-Port")
    p.add_argument("--interface", default=None,
                   help="lokale IF-IP fuer Multicast-Versand")
    p.add_argument("--ttl", type=int, default=1, help="Multicast-TTL")
    p.add_argument("--pattern", choices=sorted(PATTERNS), default="kiln",
                   help="Testmuster")
    p.add_argument("--length", type=int, default=4096,
                   help="Videowerte pro Linie (FoV-Aufloesung)")
    p.add_argument("--words-per-segment", type=int, default=2000,
                   help="max. Videowerte pro UDP-Segment (<=2000)")
    p.add_argument("--fps", type=float, default=20.0, help="Linien pro Sekunde")
    p.add_argument("--video-bits", type=int, default=14,
                   help="nutzbare Bits pro Wort")
    p.add_argument("--header-id", type=int, default=6007,
                   help="Extended-Header-ID (6002..6010)")
    p.add_argument("--trigger-period", type=int, default=0,
                   help="Ofen-Trigger alle N Linien (0=aus)")
    p.add_argument("--lines", type=int, default=0,
                   help="nach N Linien stoppen (0=endlos)")
    args = p.parse_args(argv)
    if args.words_per_segment > 2000:
        p.error("words-per-segment darf maximal 2000 sein (RawSegment MAX_WORDS).")
    return args


if __name__ == "__main__":
    run(parse_args())
