# coding: utf-8
import sys
import subprocess
import os

from PyQt5 import QtCore, QtWidgets
import logging


from python_util import util as util


def open_file(filename):
    if sys.platform == "win32":
        os.startfile(filename)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, filename])


class StatusTray(QtWidgets.QSystemTrayIcon):
    signalToggleTemperatureTransformation = QtCore.pyqtSignal()
    signalToggleFOVmode = QtCore.pyqtSignal()

    def __init__(self, mainWindow, config):
        super().__init__()
        self.logger = logging.getLogger("StatusTray")
        self.mw = mainWindow

        # Icon
        self.setIcon(QtWidgets.QApplication.windowIcon())
        desc = config["general"]["description"]
        self.setToolTip("{} - {} v{}".format(desc,
                                             QtCore.QCoreApplication.applicationName(),
                                             QtCore.QCoreApplication.applicationVersion()))

        # Menu
        self.menu = QtWidgets.QMenu()
        self.__initActions()
        self.setContextMenu(self.menu)

    def __initActions(self):
        about = self.menu.addAction(self.tr("About"))
        showlog = self.menu.addAction(self.tr("Show"))
        self.edit_configs = self.menu.addMenu(self.tr("Edit Configs"))
        edit_config = self.edit_configs.addAction(self.tr("Main Config"))
        edit_config.setData(os.path.abspath("./config/config.ini"))

#         self.export_menu = self.menu.addMenu(self.tr("Export"))

        self.toggleTemperatureTransformation = self.menu.addAction(self.tr("Digital Values"))
        self.toggleTemperatureTransformation.setCheckable(True)

        self.toggleFOVmode = self.menu.addAction(self.tr("Field of View"))
        self.toggleFOVmode.setCheckable(True)

        exit_action = self.menu.addAction(self.tr("Exit"))
        self.activated.connect(self.handleActivated)

        about.triggered.connect(self.mw.showAbout)
        showlog.triggered.connect(self.showMainWindow)
        edit_config.triggered.connect(self.edit_config)
        self.toggleTemperatureTransformation.triggered.connect(self.signalToggleTemperatureTransformation)
        self.toggleFOVmode.triggered.connect(self.signalToggleFOVmode)
        exit_action.triggered.connect(self.handleExit)

    def register_kiln(self, kiln):
        for scanner in kiln.scanners:
            self.add_scanner_config(scanner.name, scanner.config_path)

#         thermal_image = self.export_menu.addAction(self.tr("Thermal Image"))
#         thermal_image.triggered.connect(lambda self: self.export_thermal_image(kiln))

    @QtCore.pyqtSlot()
    @util.guiNoExcept()
    def export_thermal_image(self, kiln):
        filename = kiln.export_thermal_image()
        QtWidgets.QMessageBox.information(self.tr("Image saved"), self.tr("Image stored to {}").format(filename))

    def add_scanner_config(self, scanner_name, config_path):
        a = self.edit_configs.addAction(scanner_name)
        a.setData(config_path)
        a.triggered.connect(self.edit_config)

    @QtCore.pyqtSlot()
    @util.guiNoExcept()
    @util.assert_equal_thread()
    def edit_config(self):
        self.logger.info("Edit Config action triggered.")
        action = self.sender()
        path = action.data()
        self.logger.debug("Opening file: {}".format(path))
        open_file(path)

    @QtCore.pyqtSlot()
    def handleExit(self):
        self.logger.info("StatusTray Exit pressed.")
        print('exit')
        QtCore.QCoreApplication.quit()
        QtCore.QCoreApplication.exit(0)
        print('exit')
        sys.exit(0)

    @QtCore.pyqtSlot(QtWidgets.QSystemTrayIcon.ActivationReason)
    @util.guiNoExcept()
    def handleActivated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self._toggleMainWindow()

    @QtCore.pyqtSlot()
    @util.guiNoExcept()
    def showMainWindow(self):
        self.mw.setWindowState(self.mw.windowState() & ~QtCore.Qt.WindowMinimized)
        self.mw.show()
        self.mw.raise_()
        self.mw.activateWindow()

    def _toggleMainWindow(self):
        if not self.mw.isVisible():
            self.mw.show()
            if self.mw.isMinimized():
                if self.mw.isMaximized():
                    self.mw.showMaximized()
                else:
                    self.mw.showNormal()
        else:
            if self.mw.isMinimized():
                if self.mw.isMaximized():
                    self.mw.showMaximized()
                else:
                    self.mw.showNormal()
            else:
                self.mw.hide()
