import logging

from Qt import QtNetwork
from Qt import QtCore

from python_util import util as util


class TriggerReceiver(QtCore.QObject):
    """Grabs data from network socket and sends it as a signal, thus allowing to enqueue it"""
    signal_got_trigger = QtCore.Signal(object, object)

    def __init__(self, groupaddr, sourceIP, networkInterface, port):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__")
        self.groupaddr = QtNetwork.QHostAddress(groupaddr)
        self.ip = QtNetwork.QHostAddress(sourceIP)
        self.networkInterface = networkInterface
        self.__port = port
        self.socket = None
        self.reset()

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, value):
        self.__ip = QtNetwork.QHostAddress(value)

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, value):
        self.stop()
        self.__port = value
        QtCore.QMetaObject.invokeMethod(self, "start")

    @QtCore.Slot()
    @util.noexcept
    def start(self):
        self.logger.debug("Starting")
        if self.socket is None:
            self.socket = QtNetwork.QUdpSocket()
            self.socket.readyRead.connect(self.__handleIncomingData)
        self.socket.setSocketOption(QtNetwork.QAbstractSocket.MulticastTtlOption, 32)  # why?
        if not self.socket.bind(QtNetwork.QHostAddress.AnyIPv4,
                                self.port,
                                QtNetwork.QUdpSocket.ShareAddress | QtNetwork.QUdpSocket.ReuseAddressHint):
            self.logger.error("Receiver could not bind to socket.")
        if self.networkInterface is not None:
            self.logger.info("Joining multicast group {} on interface: {}".
                             format(self.groupaddr.toString(), self.networkInterface.name()))
            if not self.socket.joinMulticastGroup(self.groupaddr, self.networkInterface):
                raise Exception("Could not join multicast group {} on if {}. error={}".
                                format(self.groupaddr.toString(), self.networkInterface.name(),
                                       self.socket.errorString()))
        else:
            self.logger.info("Joining multicast group {}, no specific interface.".format(self.groupaddr.toString()))
            if not self.socket.joinMulticastGroup(self.groupaddr):
                raise Exception("Could not join multicast group {}. error={}".
                                format(self.groupaddr, self.socket.errorString()))

    @QtCore.Slot()
    @util.noexcept
    def stop(self):
        self.logger.debug("Stopping.")
        self.socket.close()
        self.socket.readyRead.disconnect()
        self.reset()
        self.socket = None
        self.logger.debug("Stopped.")

    def reset(self):
        self.logger.info("Resetting.")

    def quit(self):
        try:
            self.stop()
        except Exception:
            pass

    @QtCore.Slot()
    def __handleIncomingData(self):
        if self.socket.hasPendingDatagrams():
            len_to_read = self.socket.pendingDatagramSize()
            if len_to_read <= 0:
                return
            data, host, __port = self.socket.readDatagram(len_to_read)
            if host != self.ip:
                return
            self.signal_got_trigger.emit(data, host)


def print_data(data, host):
    print("data={} host={}".format(data, host))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    import sys
    a = QtCore.QCoreApplication(sys.argv)
    r = TriggerReceiver("239.1.1.1", "192.168.10.82", None, 50011)
    r.signal_got_trigger.connect(print_data)
    r.start()
    a.exec_()