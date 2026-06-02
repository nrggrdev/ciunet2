import logging

from PyQt5 import QtCore, QtWidgets
import pprint

from python_util import util as util


class DeviceStatusWorkerThread(util.WorkerThread):
    pass


class DeviceStatus(QtWidgets.QScrollArea):
    signal_multiple_devices_per_host = QtCore.pyqtSignal(object, object, object)

    def __init__(self, parent):
        super().__init__(parent)
        self.logger = logging.getLogger("DeviceStatus")
        self.label = QtWidgets.QLabel(self)
        self.setWidget(self.label)
        self.data = {}
        self.__serial_per_host = {}
        self.readSettings()
        self.updateTimer = QtCore.QTimer(self)
        self.updateTimer.setInterval(2 * 1000)
        self.updateTimer.timeout.connect(self.draw)
        self.updateTimer.start()

    def quit(self):
        pass

    def clear(self):
        pass

    @QtCore.pyqtSlot()
    @util.noexcept
    def stop(self):
        pass

    @QtCore.pyqtSlot(object, object)
    @util.assert_equal_thread()
    def receiveData(self, data, host):
        self.data[host] = {"received": str(util.datetime_helper.current_local_time()), "data": data}
        try:
            device_serial = data["device_serial"]
            if host in self.__serial_per_host:
                if device_serial != self.__serial_per_host[host]:
                    self.signal_multiple_devices_per_host.emit(host, device_serial, self.__serial_per_host[host])
                    self.logger.debug("Detected two different device serials {} != {} for host={}".
                                      format(device_serial, self.__serial_per_host[host], host))
            else:
                self.__serial_per_host[host] = device_serial
        except Exception as e:
            print(e)
            pass

    @QtCore.pyqtSlot()
    def draw(self):
        if self.isVisible():
            self.label.setText(pprint.pformat(self.data))
            self.label.adjustSize()

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("DeviceStatus")
        self.resize(settings.value("size", QtCore.QSize(600, 600)))
        self.move(settings.value("pos", QtCore.QPoint(200, 200)))
        settings.endGroup()

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("DeviceStatus")
        settings.setValue("size", QtWidgets.QMainWindow.size(self))
        settings.setValue("pos", QtWidgets.QMainWindow.pos(self))
        settings.endGroup()

    ' QWidget override '
    def moveEvent(self, event):
        self.writeSettings()
        super().moveEvent(event)

    ' QWidget override '
    def resizeEvent(self, event):
        self.writeSettings()
        super().resizeEvent(event)
