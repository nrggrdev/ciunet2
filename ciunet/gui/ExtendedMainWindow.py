from PyQt5 import QtCore, QtWidgets

_DEFAULT_SIZE = QtCore.QSize(600, 600)
_DEFAULT_POS = QtCore.QPoint(200, 200)


class ExtendedMainWindow(QtWidgets.QMainWindow):
    """ Simple QMainWindow wrapper offering automatic persistent size and position settings"""
    def __init__(self, parent=None, flags=QtCore.Qt.WindowFlags(0)):
        super().__init__(parent=parent, flags=flags)
        self.readSettings()

    def readSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup(type(self).__name__)
        self.resize(settings.value("size", _DEFAULT_SIZE))
        self.move(settings.value("pos", _DEFAULT_POS))
        settings.endGroup()

    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup(type(self).__name__)
        settings.setValue("size", QtWidgets.QMainWindow.size(self))
        settings.setValue("pos", QtWidgets.QMainWindow.pos(self))
        settings.endGroup()

    ' QWidget override '
    def moveEvent(self, event):
        self.writeSettings()
        QtWidgets.QMainWindow.moveEvent(self, event)

    ' QWidget override '
    def resizeEvent(self, event):
        self.writeSettings()
        QtWidgets.QMainWindow.resizeEvent(self, event)
