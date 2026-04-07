import logging
import json

from Qt import QtCore
from Qt import QtNetwork

from python_util import util as util


class StatusTransmitter(QtCore.QObject):
    def __init__(self, kiln, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.logger = logging.getLogger("StatusTransmitter")
        self.kiln = kiln
        self.__udpSocket = QtNetwork.QUdpSocket()
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.setSingleShot(False)
        self.updateTimer.setInterval(5000)
        self.updateTimer.timeout.connect(self.__updateStatus)
        self.scm = {}
        self.md = {}
        self.enj = json.JSONEncoder()

    @QtCore.Slot()
    @util.noexcept
    def start(self):
        self.updateTimer.start()

    @QtCore.Slot()
    @util.noexcept
    def __updateStatus(self):
        try:
            status = {"error": "no status"}
            try:
                status = self.kiln.status
            except Exception as e:
                self.logger.debug("Could not get kiln status: {}".format(e))
            self.__udpSocket.writeDatagram(self.enj.encode(status).encode(), QtNetwork.QHostAddress("239.1.1.1"), 51000)
        except Exception as e:
            self.logger.error("Could not send status: {}".format(e))
            self.logger.debug("Could not send status: {}".format(e), exc_info=True)
