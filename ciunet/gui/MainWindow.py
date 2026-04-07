import logging
import sys

from Qt import QtCore, QtGui, QtWidgets
import scipy
import numpy

from python_util import util as util
from . import MenuBar
from . import StatusBar
from . import StatusTray
from . import TabWidget
from . import ExtendedMainWindow


class MainWindow(ExtendedMainWindow.ExtendedMainWindow):
    close_signal = QtCore.Signal()
    printclicked = QtCore.Signal()
    openclicked = QtCore.Signal()
    saveclicked = QtCore.Signal()
    executeclicked = QtCore.Signal()

    def __init__(self, config,parent=None):
        super().__init__()
        self.parent=parent
        self.logger = logging.getLogger("MainWindow")
        # self.msgBox.buttonClicked.connect(self.timeout_message_clicked, QtCore.Qt.QueuedConnection)
#        self.setFixedHeight(300)
        try:
            loglevel = int(config["logging"]["logging_level"])
        except:loglevel=20
        self.centralTab = TabWidget.TabWidget(self,loglevel=loglevel,config=config['debug'])
        self.setCentralWidget(self.centralTab)

        desc = config["general"]["description"]
        self.show_timeouts = config["general"].get("show_timeouts", True)
        self.setWindowTitle("{} - {} v{}".format(desc,
                                                 QtCore.QCoreApplication.applicationName(),
                                                 QtCore.QCoreApplication.applicationVersion()))

        menu_bar = MenuBar.MainWindowMenuBar(self,config=config)
        menu_bar.file_menu.loglevel_menu.signal_loglevel_changed.connect(self.centralTab.set_display_loglevel)
        menu_bar.file_menu.logfilter_menu.signal_Filter_changed.connect(self.centralTab.setLoggingfilter)
        menu_bar.file_menu.logfilter_menu.signal_log_pause.connect(self.centralTab.setLoggingPause)
        menu_bar.file_menu.clearLogViewSignal.connect(self.centralTab.clear)
        menu_bar.file_menu.signal_log_pause.connect(self.centralTab.setLoggingPause)

        self.centralTab.filter.newLoggingCLass.connect(menu_bar.file_menu.logfilter_menu.addClass)

        self.setMenuBar(menu_bar)

        self.setStatusBar(StatusBar.StatusBar(self))

        self.timeout_boxes = []
        self.statusTray = StatusTray.StatusTray(mainWindow=self, config=config)
        self.statusTray.show()

    def register_kiln(self, kiln):
        kiln.signalTimeout.connect(self.showTimeout)
        self.centralTab.register_kiln(kiln)
        self.statusTray.register_kiln(kiln)

    @QtCore.Slot()
    @util.noexcept
    @util.assert_equal_thread()
    def stop(self):
        self.logger.debug("Stopping")
        self.centralTab.deviceStatus.stop()
        self.statusTray.hide()

    @QtCore.Slot(object)
    @util.noexcept
    @util.assert_equal_thread()
    def showTimeout(self, msg):
        if not self.show_timeouts:
            return
        for w in self.timeout_boxes:
            #w.close()
            del self.timeout_boxes[:]
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgBox.setModal(False)
        msgBox.setWindowTitle(self.tr("Timeout"))
        msgBox.setText("{}\n{}".format(util.datetime_helper.current_local_time(), msg))
        msgBox.open()
        self.timeout_boxes.append(msgBox)

    @QtCore.Slot()
    def timeout_message_clicked(self, _button):
        self.logger.debug("timeout_message_clicked")
        self.is_timeout_message_active = False

    @QtCore.Slot()
    @util.assert_equal_thread()
    def setTemporaryStatusBar(self, message):
        if type(message) == QtGui.QTextCursor:
            to_print = str(message.blockNumber() + message.positionInBlock())
        else:
            to_print = str(message)
        self.statusBar().showMessage(to_print, 2000)

    @QtCore.Slot()
    @util.assert_equal_thread()
    def setPermanentStatusBar(self, message):
        if type(message) == QtGui.QTextCursor:
            to_print = str(message.blockNumber() + message.positionInBlock())
        else:
            to_print = str(message)
        self.statusBar().showMessage(to_print)

    @QtCore.Slot()
    @util.guiNoExcept()
    @util.assert_equal_thread()
    def showAbout(self):
        QtWidgets.QMessageBox.about(self,
                                    self.tr("About {}").format(QtCore.QCoreApplication.applicationName()),
                                    self.tr("GESOTEC Data Aquisition Application.\n\nVersion {version}"
                                            "\n\nPython: {python}\nNumpy: {numpy}\nScipy: {scipy}").
                                    format(version=QtCore.QCoreApplication.applicationVersion(),
                                           python=sys.version,
                                           numpy=numpy.__version__,
                                           scipy=scipy.__version__))

    @QtCore.Slot()
    @util.guiNoExcept()
    def quitClicked(self):
        QtCore.QCoreApplication.quit()

    @QtCore.Slot()
    def printClicked(self):
        self.printclicked.emit()

    @QtCore.Slot()
    def openClicked(self):
        self.openclicked.emit()

    @QtCore.Slot()
    def saveClicked(self):
        self.saveclicked.emit()

    @QtCore.Slot()
    def executeClicked(self):
        self.executeclicked.emit()

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Print):
            self.printClicked()
        elif event.matches(QtGui.QKeySequence.Open):
            self.openClicked()
        elif event.matches(QtGui.QKeySequence.Save):
            self.saveClicked()
        elif event.modifiers() & QtCore.Qt.CTRL and event.key() == QtCore.Qt.Key_Q:
            self.quitClicked()
        elif event.modifiers() & QtCore.Qt.CTRL and event.key() == QtCore.Qt.Key_Enter:
            self.executeClicked()
        QtWidgets.QMainWindow.keyPressEvent(self, event)

    def closeEvent(self, event):
        QtWidgets.QMainWindow.closeEvent(self, event)
        QtCore.QCoreApplication.quit()
        sys.exit(0)

    def changeEvent(self, event):
        """QtGui.QWidget override"""
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowStateChange:
            # make sure we only do this for minimize events
            if (event.oldState() != QtCore.Qt.WindowMinimized) and self.isMinimized():
                QtCore.QCoreApplication.processEvents()
                # self.hide()
                QtCore.QTimer.singleShot(0, self.hide)
                event.ignore()

