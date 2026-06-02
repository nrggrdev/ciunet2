"""
Schlanker UDP-Empfaenger, der den Scanner-Datenstrom zu kompletten Linien
zusammensetzt -- gemeinsam genutzt von data_viewer und geometry_tool.

Nutzt den echten ``RawSegment``-Parser. Linien werden an den ``is_first()``-
Segmentgrenzen (block_id==0) getrennt. Emittiert pro Linie ein numpy-Array der
Videowerte (bereits auf ``video_bits`` maskiert).
"""

import logging

import numpy
from PyQt5 import QtCore, QtNetwork

from daq_net.daq.RawSegment import RawSegment


class LineReceiver(QtCore.QObject):
    # (video_data: ndarray[uint], meta: dict)
    signalGotLine = QtCore.pyqtSignal(object, object)
    signalGotTrigger = QtCore.pyqtSignal(object)

    def __init__(self, port, source=None, multicast_group=None, interface=None,
                 trigger_channel=4, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.port = int(port)
        self.source = QtNetwork.QHostAddress(source) if source else None
        self.multicast_group = (QtNetwork.QHostAddress(multicast_group)
                                if multicast_group else None)
        self.interface = interface
        self.trigger_channel = trigger_channel

        self.socket = QtNetwork.QUdpSocket(self)
        self._segments = []          # video-arrays der aktuellen Linie
        self._have_line = False
        self._last_trigger = None
        self.lines_received = 0
        self.segments_received = 0

    def start(self):
        ok = self.socket.bind(QtNetwork.QHostAddress.AnyIPv4, self.port,
                              QtNetwork.QUdpSocket.ShareAddress
                              | QtNetwork.QUdpSocket.ReuseAddressHint)
        if not ok:
            raise RuntimeError("Konnte UDP-Port {} nicht binden.".format(self.port))
        if self.multicast_group is not None:
            iface = self._find_interface()
            if iface is not None:
                self.socket.joinMulticastGroup(self.multicast_group, iface)
            else:
                self.socket.joinMulticastGroup(self.multicast_group)
        self.socket.setSocketOption(
            QtNetwork.QAbstractSocket.ReceiveBufferSizeSocketOption, 64 * 1024 * 1024)
        self.socket.readyRead.connect(self._read)
        self.logger.info("LineReceiver lauscht auf Port %s", self.port)

    def _find_interface(self):
        if not self.interface:
            return None
        for iface in QtNetwork.QNetworkInterface.allInterfaces():
            if iface.humanReadableName() == self.interface:
                return iface
            for entry in iface.addressEntries():
                if entry.ip().toString().split("%")[0] == self.interface:
                    return iface
        return None

    def _read(self):
        while self.socket.hasPendingDatagrams():
            dg = self.socket.receiveDatagram()
            sender = dg.senderAddress()
            if self.source is not None and sender != self.source:
                continue
            self._handle(bytes(dg.data()))

    def _handle(self, data):
        try:
            seg = RawSegment(data, triggerchannel=self.trigger_channel)
        except Exception:
            self.logger.debug("Ungueltiges Datagramm verworfen", exc_info=True)
            return
        self.segments_received += 1

        bits = seg.video_bits
        video = numpy.bitwise_and(numpy.asarray(seg.data), (1 << bits) - 1)

        trig = seg.last_trigger_usec
        if trig and trig != self._last_trigger:
            self._last_trigger = trig
            self.signalGotTrigger.emit(trig)

        if seg.is_first():
            if self._have_line and self._segments:
                line = numpy.concatenate(self._segments)
                self.lines_received += 1
                self.signalGotLine.emit(line, {"line_id": seg.line_id,
                                               "time_usec": seg.block_time_usec,
                                               "trigger": self._last_trigger})
            self._segments = [video]
            self._have_line = True
        else:
            if self._have_line:
                self._segments.append(video)
