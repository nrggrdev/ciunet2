#!/usr/bin/env python3
"""
Live-Datenanzeige fuer den Scanner-Datenstrom.

Empfaengt den UDP-Strom (vom Scanner-Simulator oder einer echten DaLi-NETA),
setzt die Linien zusammen und zeigt sie fortlaufend an:
  - oben:  Wasserfall-Bild (Spalten = Linien ueber die Zeit)
  - unten: die aktuell empfangene Linie als Kurve
  - Statuszeile mit Linien-/Segmentzaehler und Rate.

Beispiel:
  python -m simulator.data_viewer --port 51002 --source 127.0.0.1
"""

import argparse
import sys
import time

import numpy
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

if __package__ in (None, ""):
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from simulator.line_receiver import LineReceiver
else:
    from .line_receiver import LineReceiver


class DataViewer(QtWidgets.QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("CIU-NET Scanner - Live-Datenanzeige")
        self.resize(1000, 700)
        self.history = args.history

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.status_label = QtWidgets.QLabel("warte auf Daten ...")
        layout.addWidget(self.status_label)

        glw = pg.GraphicsLayoutWidget()
        layout.addWidget(glw, 1)

        # Wasserfall
        self.wf_plot = glw.addPlot(row=0, col=0)
        self.wf_plot.setLabel("left", "FoV-Pixel")
        self.wf_plot.setLabel("bottom", "Linie (Zeit ->)")
        self.img = pg.ImageItem()
        self.wf_plot.addItem(self.img)
        self.cmap = pg.colormap.get("inferno") if hasattr(pg, "colormap") else None
        if self.cmap is not None:
            self.img.setLookupTable(self.cmap.getLookupTable())

        # aktuelle Linie
        self.line_plot = glw.addPlot(row=1, col=0)
        self.line_plot.setLabel("left", "Digit-Wert")
        self.line_plot.setLabel("bottom", "FoV-Pixel")
        self.line_plot.showGrid(x=True, y=True, alpha=0.3)
        self.curve = self.line_plot.plot(pen=pg.mkPen("y", width=1))

        self.buffer = None
        self.col = 0
        self.last_count = 0
        self.last_time = time.time()

        self.receiver = LineReceiver(port=args.port, source=args.source,
                                     multicast_group=args.multicast,
                                     interface=args.interface,
                                     trigger_channel=args.trigger_channel,
                                     parent=self)
        self.receiver.signalGotLine.connect(self.on_line)
        self.receiver.start()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(500)

    @QtCore.pyqtSlot(object, object)
    def on_line(self, line, meta):
        line = numpy.asarray(line, dtype=float)
        n = len(line)
        if n == 0:
            return
        if self.buffer is None or self.buffer.shape[0] != n:
            self.buffer = numpy.zeros((n, self.history), dtype=float)
            self.col = 0
        self.buffer[:, self.col] = line
        self.col = (self.col + 1) % self.history
        # so rollen, dass die neueste Linie rechts steht
        rolled = numpy.roll(self.buffer, -self.col, axis=1)
        self.img.setImage(rolled, autoLevels=False,
                          levels=(float(self.buffer.min()), float(self.buffer.max()) or 1.0))
        self.curve.setData(line)

    def update_status(self):
        now = time.time()
        dn = self.receiver.lines_received - self.last_count
        dt = now - self.last_time
        rate = dn / dt if dt > 0 else 0.0
        self.last_count = self.receiver.lines_received
        self.last_time = now
        self.status_label.setText(
            "Linien: {}   Segmente: {}   Rate: {:.1f} Linien/s"
            .format(self.receiver.lines_received,
                    self.receiver.segments_received, rate))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Live-Anzeige des Scanner-UDP-Stroms")
    p.add_argument("--port", type=int, default=51002, help="UDP-Port")
    p.add_argument("--source", default="127.0.0.1",
                   help="erwartete Absender-IP (leer = beliebig)")
    p.add_argument("--multicast", default=None, help="Multicast-Gruppe beitreten")
    p.add_argument("--interface", default=None, help="IF-IP fuer Multicast")
    p.add_argument("--trigger-channel", type=int, default=4)
    p.add_argument("--history", type=int, default=600,
                   help="Anzahl Linien im Wasserfall")
    args = p.parse_args(argv)
    if args.source == "":
        args.source = None
    return args


def main(argv=None):
    args = parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    pg.setConfigOptions(imageAxisOrder="row-major")
    viewer = DataViewer(args)
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
