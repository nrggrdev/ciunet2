import re

from Qt import QtCore, QtGui, QtWidgets

from python_util import util as util


class LogViewWidget(QtWidgets.QTextBrowser):
    signal_write = QtCore.Signal(str)
    signal_error = QtCore.Signal(str, str)

    def __init__(self, parent):
        super().__init__(parent)
        self.paused=False
        self.document().setMaximumBlockCount(200)
        self.signal_write.connect(self.__write, QtCore.Qt.QueuedConnection)
        self.setWindowTitle("{} - v{}".format(QtCore.QCoreApplication.applicationName(),
                                              QtCore.QCoreApplication.applicationVersion()))
        self.alive = True
        self.destroyed.connect(self.getting_destroyed)
        self.setTextColor(QtGui.QColor("green"))
        name=QtCore.QCoreApplication.applicationName()
        version=QtCore.QCoreApplication.applicationVersion()
        f=self.font()
#        myfont=QtGui.QFont("Monospace");
#        myfont.setStyleHint(QtGui.QFont.Monospace);
#        myfont.setPixelSize(20);
#        myfont.setBold(True);
#        self.setFont(myfont)
        f.setBold(True)

        self.write(f'<b>Starting {name} Version {version}</b>')
        self.write('*'*80)
 #       self.setFont(f)
    @QtCore.Slot(str)
    @util.noexcept
    @util.assert_equal_thread()

    def setPause(self,pause):
        self.paused=pause
    def __write(self, text):
        if self.paused:
            return
        if re.search("WARNING", text):
            self.setTextColor(QtGui.QColor("orange"))
        elif re.search("ERROR", text):
            self.setTextColor(QtGui.QColor("red"))
            self.signal_error.emit("ERROR", text)
        elif re.search("INFO", text):
            self.setTextColor(QtGui.QColor("green"))
        elif re.search("DEBUG", text):
            self.setTextColor(QtGui.QColor("grey"))
        else:
            self.setTextColor(QtGui.QColor("black"))
        self.append(text)

    @QtCore.Slot()
    @util.noexcept
    def getting_destroyed(self):
        self.alive = False

    def write(self, text):
        """
        Public interface, connected to the internal _write method through a queued connection,
        because we receive logmessages from different threads
        """
        if text == "\n":
            return
        if not self.alive:
            return
        assert(text is not None)
        self.signal_write.emit(text.rstrip())
