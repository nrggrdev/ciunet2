import os
import configparser

from Qt import QtCore

from daq_net.daq import Temperature
from python_util import util as util
import logging

class StatusFileWriter(QtCore.QObject):
    def __init__(self, config, kiln, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger(QtCore.QCoreApplication.applicationName())
        self.status_file = str(config["general"]["status_file"])
        self.status_file = os.path.abspath(self.status_file)
        self.status_writer_timer = QtCore.QTimer(self)
        self.status_writer_timer.setInterval(1000 )
        self.status_writer_timer.timeout.connect(self._write_status_INI_file)
        self.kiln = kiln

    @QtCore.Slot()
    @util.noexcept
    def start(self):
        try:
            self.status_writer_timer.start()
        except Exception as e:
            print (e)

    @QtCore.Slot()
    @util.noexcept
    def _write_status_INI_file(self):
        try:
            # Checkout base dir
            baseDir = os.path.dirname(self.status_file)
            if not os.path.exists(baseDir):
                self.logger.info("Creating status INI file dir: {}".format(baseDir))
                os.makedirs(baseDir)

            s = configparser.RawConfigParser()
            s.add_section("Kiln")
            s.set("Kiln", "rpm", self.kiln.rpm)
            s.set("Kiln", "kiln_start", self.kiln.kiln_start)
            s.set("Kiln", "kiln_end", self.kiln.kiln_end)
            s.set("Kiln", "n_scanners", len(self.kiln.scanners))
            for scanner in self.kiln.scanners:
                try:
                    sn=f"{scanner.name}_{scanner.displayIndex}"
                    s.add_section(sn)
                    s.set(sn, "internal_temp_C", float(Temperature.kelvinToCelsius(scanner.internal_temperature)))
                except Exception as e:
                    print(e)

            with open(self.status_file, "w") as f:
                s.write(f)
        except Exception as e:
            self.logger.error("Could not write status INI Output File: {}".format(e), exc_info=True)
