#!/usr/bin/env python3
"""
Live-Geometrie-Einstellung mit Referenzpunkten (Passpunkten).

Empfaengt den Scanner-Datenstrom und zeigt links die Rohlinie ueber dem
FoV-Winkel und rechts/unten die mit der aktuellen Geometrie auf die
Ofenachse transformierte Linie. Die Referenzpunkte (phi1/pass1, phi2/pass2)
sowie tilt/fov koennen live veraendert werden -- die Transformation und die
berechneten Werte (l = Lotfusspunkt, h = Lotlaenge) aktualisieren sich sofort.

Geaenderte Werte koennen in die ``[geometry]``-Sektion einer Scanner-.ini
zurueckgeschrieben werden (mit .bak-Sicherung).

Beispiel:
  python -m simulator.geometry_tool --port 51002 --source 127.0.0.1 \
      --config config/scanner1.ini
"""

import argparse
import os
import shutil
import sys

import numpy
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from simulator.line_receiver import LineReceiver
else:
    from .line_receiver import LineReceiver

from ciunet.processing.transform.geometrical_transformation import GeoTransformator
from python_util.util import configobj

ConfigObj = configobj.myConfigObj


class FakeKiln:
    """Minimaler Ofen-Stub fuer GeoTransformator."""
    def __init__(self, kiln_start, kiln_end):
        self.kiln_start = kiln_start
        self.kiln_end = kiln_end

    @property
    def length(self):
        return self.kiln_end - self.kiln_start


class GeometryTool(QtWidgets.QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.setWindowTitle("CIU-NET - Live-Geometrie (Referenzpunkte)")
        self.resize(1150, 720)
        self.config_path = args.config
        self.target_pixel = args.target_pixel
        self.last_line = None

        # --- Startwerte (aus Config laden falls vorhanden) -------------------
        self.params = {
            "phi1": 10.3, "pass1": 48.0,
            "phi2": 94.5, "pass2": 5.2,
            "tilt": 2.5, "fov_angle": 120.0,
            "kiln_start": 46.0, "kiln_end": 0.0,
        }
        if self.config_path and os.path.exists(self.config_path):
            self._load_config(self.config_path, announce=False)

        self._build_ui()
        self._rebuild_geometry()

        self.receiver = LineReceiver(port=args.port, source=args.source,
                                     multicast_group=args.multicast,
                                     interface=args.interface,
                                     trigger_channel=args.trigger_channel,
                                     parent=self)
        self.receiver.signalGotLine.connect(self.on_line)
        self.receiver.start()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)

        # Plots
        glw = pg.GraphicsLayoutWidget()
        root.addWidget(glw, 1)

        self.raw_plot = glw.addPlot(row=0, col=0)
        self.raw_plot.setTitle("Rohlinie ueber FoV-Winkel")
        self.raw_plot.setLabel("bottom", "Scanner-Winkel [deg]")
        self.raw_plot.setLabel("left", "Digit-Wert")
        self.raw_plot.showGrid(x=True, y=True, alpha=0.3)
        self.raw_curve = self.raw_plot.plot(pen=pg.mkPen("y", width=1))
        self.phi1_line = pg.InfiniteLine(angle=90, movable=False,
                                         pen=pg.mkPen("c", width=2),
                                         label="phi1", labelOpts={"position": 0.9})
        self.phi2_line = pg.InfiniteLine(angle=90, movable=False,
                                         pen=pg.mkPen("m", width=2),
                                         label="phi2", labelOpts={"position": 0.9})
        self.raw_plot.addItem(self.phi1_line)
        self.raw_plot.addItem(self.phi2_line)

        self.kiln_plot = glw.addPlot(row=1, col=0)
        self.kiln_plot.setTitle("Transformiert auf Ofenachse")
        self.kiln_plot.setLabel("bottom", "Ofenposition")
        self.kiln_plot.setLabel("left", "Digit-Wert")
        self.kiln_plot.showGrid(x=True, y=True, alpha=0.3)
        self.kiln_curve = self.kiln_plot.plot(pen=pg.mkPen("g", width=1))
        self.pass1_line = pg.InfiniteLine(angle=90, movable=False,
                                          pen=pg.mkPen("c", width=2),
                                          label="pass1", labelOpts={"position": 0.9})
        self.pass2_line = pg.InfiniteLine(angle=90, movable=False,
                                          pen=pg.mkPen("m", width=2),
                                          label="pass2", labelOpts={"position": 0.9})
        self.kiln_plot.addItem(self.pass1_line)
        self.kiln_plot.addItem(self.pass2_line)

        # Steuerung
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(300)
        root.addWidget(panel)
        form = QtWidgets.QFormLayout(panel)

        self.spins = {}
        spec = [
            ("phi1", "Passpunkt 1 Winkel [deg]", 0, 360, 0.1),
            ("pass1", "Passpunkt 1 Ofenposition", -1000, 1000, 0.1),
            ("phi2", "Passpunkt 2 Winkel [deg]", 0, 360, 0.1),
            ("pass2", "Passpunkt 2 Ofenposition", -1000, 1000, 0.1),
            ("tilt", "Tilt [deg]", -89.9, 89.9, 0.1),
            ("fov_angle", "FoV-Winkel [deg]", 1, 360, 0.5),
            ("kiln_start", "Ofen-Start", -1000, 1000, 0.5),
            ("kiln_end", "Ofen-Ende", -1000, 1000, 0.5),
        ]
        for key, label, lo, hi, step in spec:
            sb = QtWidgets.QDoubleSpinBox()
            sb.setRange(lo, hi)
            sb.setSingleStep(step)
            sb.setDecimals(2)
            sb.setValue(self.params[key])
            sb.valueChanged.connect(self._on_param_changed)
            form.addRow(label, sb)
            self.spins[key] = sb

        self.result_label = QtWidgets.QLabel("l = -, h = -")
        self.result_label.setStyleSheet("font-weight: bold;")
        form.addRow(self.result_label)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        form.addRow(self.error_label)

        btn_load = QtWidgets.QPushButton("Config laden ...")
        btn_load.clicked.connect(self._on_load_clicked)
        form.addRow(btn_load)

        btn_save = QtWidgets.QPushButton("In .ini speichern")
        btn_save.clicked.connect(self._on_save_clicked)
        form.addRow(btn_save)

        self.status_label = QtWidgets.QLabel("warte auf Daten ...")
        self.status_label.setWordWrap(True)
        form.addRow(self.status_label)

    # -------------------------------------------------------------- Logik
    def _on_param_changed(self):
        for key, sb in self.spins.items():
            self.params[key] = sb.value()
        self._rebuild_geometry()
        self._redraw()

    def _rebuild_geometry(self):
        p = self.params
        kiln = FakeKiln(p["kiln_start"], p["kiln_end"])
        geometry_config = {
            "mode": "tilt",
            "phi1": p["phi1"], "pass1": p["pass1"],
            "phi2": p["phi2"], "pass2": p["pass2"],
            "tilt": p["tilt"],
        }
        n = len(numpy.arange(kiln.kiln_start, kiln.kiln_end,
                             kiln.length / self.target_pixel)) if kiln.length else 0
        mask = numpy.ones(max(n, 1), dtype=bool)
        self.geo = None
        try:
            self.geo = GeoTransformator(
                kiln=kiln, target_pixel=self.target_pixel,
                fov_angle=p["fov_angle"], geometry_config=geometry_config,
                mask=mask, interpolation_mode="linear")
            self.error_label.setText("")
            self.result_label.setText(
                "l = {:.3f}   h = {:.3f}   tilt = {:.3f}"
                .format(self.geo.l, self.geo.h, self.geo.tilt))
        except Exception as e:
            self.error_label.setText("Geometrie ungueltig: {}".format(e))
            self.result_label.setText("l = -, h = -")

        # Markerpositionen
        self.phi1_line.setValue(p["phi1"])
        self.phi2_line.setValue(p["phi2"])
        self.pass1_line.setValue(p["pass1"])
        self.pass2_line.setValue(p["pass2"])

    @QtCore.pyqtSlot(object, object)
    def on_line(self, line, meta):
        self.last_line = numpy.asarray(line, dtype=float)
        self.status_label.setText(
            "Linien: {}   Laenge: {}".format(self.receiver.lines_received,
                                             len(self.last_line)))
        self._redraw()

    def _redraw(self):
        if self.last_line is None:
            return
        data = self.last_line
        n = len(data)
        angles = numpy.linspace(0, self.params["fov_angle"], n)
        self.raw_curve.setData(angles, data)

        if self.geo is None:
            self.kiln_curve.clear()
            return
        try:
            transformed = self.geo.convert(data, fov_mode=False,
                                           fov_angle=self.params["fov_angle"])
            positions = self.geo.interpolation_points
            m = min(len(positions), len(transformed))
            self.kiln_curve.setData(positions[:m], transformed[:m])
        except Exception as e:
            self.error_label.setText("Transformation fehlgeschlagen: {}".format(e))

    # ----------------------------------------------------------- Config IO
    def _load_config(self, path, announce=True):
        try:
            conf = ConfigObj(path, encoding="UTF8")
            geo = conf.get("geometry", {})
            for k in ("phi1", "pass1", "phi2", "pass2", "tilt"):
                if k in geo:
                    self.params[k] = float(geo[k])
            if "fov_angle" in conf:
                self.params["fov_angle"] = float(conf["fov_angle"]) % 360.0
            if announce:
                for key, sb in self.spins.items():
                    sb.blockSignals(True)
                    sb.setValue(self.params[key])
                    sb.blockSignals(False)
                self._rebuild_geometry()
                self._redraw()
            self.config_path = path
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Laden fehlgeschlagen", str(e))

    def _on_load_clicked(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Scanner-Config laden", os.getcwd(), "INI (*.ini);;Alle (*)")
        if path:
            self._load_config(path, announce=True)

    def _on_save_clicked(self):
        path = self.config_path
        if not path:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "In Scanner-Config speichern", os.getcwd(),
                "INI (*.ini);;Alle (*)")
            if not path:
                return
        try:
            if os.path.exists(path):
                shutil.copy2(path, path + ".bak")
            conf = ConfigObj(path, encoding="UTF8")
            if "geometry" not in conf:
                conf["geometry"] = {}
            geo = conf["geometry"]
            geo["mode"] = "tilt"
            for k in ("phi1", "pass1", "phi2", "pass2", "tilt"):
                geo[k] = round(self.params[k], 4)
            conf.write()
            self.config_path = path
            QtWidgets.QMessageBox.information(
                self, "Gespeichert",
                "Geometrie in {} geschrieben.\nSicherung: {}.bak".format(path, path))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Speichern fehlgeschlagen", str(e))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Live-Geometrie mit Referenzpunkten")
    p.add_argument("--port", type=int, default=51002, help="UDP-Port")
    p.add_argument("--source", default="127.0.0.1",
                   help="erwartete Absender-IP (leer = beliebig)")
    p.add_argument("--multicast", default=None, help="Multicast-Gruppe beitreten")
    p.add_argument("--interface", default=None, help="IF-IP fuer Multicast")
    p.add_argument("--trigger-channel", type=int, default=4)
    p.add_argument("--config", default=None,
                   help="Scanner-.ini fuer Startwerte / Speichern")
    p.add_argument("--target-pixel", type=int, default=9000,
                   help="Zielaufloesung der Ofenachse")
    args = p.parse_args(argv)
    if args.source == "":
        args.source = None
    return args


def main(argv=None):
    args = parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    pg.setConfigOptions(antialias=True)
    win = GeometryTool(args)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
