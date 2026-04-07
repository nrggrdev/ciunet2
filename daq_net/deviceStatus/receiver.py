import json
import logging

from Qt import QtNetwork as QTN
from Qt import QtCore

from python_util.util.noexcept import noexcept
from python_util import util


class StatusReader(QtCore.QObject):
    signalGotData = QtCore.Signal(object, object)
    signal_combined_data = QtCore.Signal(object)

    def __init__(self, config):
        super().__init__()
        self.logger = logging.getLogger("StatusReader")
        self.combined_data = {}
        # QT5.8 does not respect "NO_PROXY" setting for local connections, thus causing problems with HOLCIM proxy config
        # See https://stackoverflow.com/q/42121008
        QTN.QNetworkProxyFactory.setUseSystemConfiguration(False)

        self.logger.debug("config: {}".format(config))
        self.__port = int(config["StatusViewer"]["listenPort"])
        self.__udpSocket = QTN.QUdpSocket(self)
        self.__groupaddr = QTN.QHostAddress(config["StatusViewer"]["multicastGroup"])
        self.__parsedInterface = config["StatusViewer"]["interface"] if "interface" in config["StatusViewer"] else None
        print (self.__parsedInterface)
    @QtCore.Slot()
    @noexcept
    @util.assert_equal_thread()
    def start(self):
        self.logger.debug("Starting")
        self.__udpSocket.readyRead.connect(self.__readIncomingData)
        self.bindSocket()
        ni = QTN.QNetworkInterface()
        self.__udpSocket.joinMulticastGroup(self.__groupaddr, ni)

    @QtCore.Slot()
    @noexcept
    @util.assert_equal_thread()
    def stop(self):
        self.logger.debug("Stopping")
        self.__udpSocket.close()

    def quit(self):
        try:
            QtCore.QMetaObject.invokeMethod(self, "stop")
        except Exception:
            self.logger.error("Error when quitting", exc_info=True)
        self.thread().quit()

    def bindSocket(self):
        self.__udpSocket.setSocketOption(QTN.QAbstractSocket.MulticastTtlOption, 32)  # why?
        if not self.__udpSocket.bind(QTN.QHostAddress.AnyIPv4, self.__port, QTN.QUdpSocket.ShareAddress | QTN.QUdpSocket.ReuseAddressHint):
            self.logger.error("Receiver could not bind to socket.")
        networkInterface = self.__getNetworkInterface()
        if networkInterface is not None:
            self.logger.info("Joining multicast group {} on interface: {}".format(self.__groupaddr.toString(), networkInterface.humanReadableName()))
            #  udpSocket.setMulticastInterface(getNetworkInterfac eByAddress("10.7.7.140"));
            #  udpSocket.joinMulticastGroup(QHostAddress("224.0.0.1"));
            if not self.__udpSocket.joinMulticastGroup(self.__groupaddr, networkInterface):
                raise Exception("Could not join multicast group {} on if {}. error={}".format(self.__groupaddr.toString(), networkInterface.humanReadableName(), self.__udpSocket.errorString()))
        else:
            self.logger.info("Joining multicast group {}, no specific interface.".format(self.__groupaddr))
            if not self.__udpSocket.joinMulticastGroup(self.__groupaddr):
                raise Exception("Could not join multicast group {}. error={}".format(self.__groupaddr.toString(), self.__udpSocket.errorString()))

    def __getNetworkInterface(self):
        """Get specific network interface if one is specified in the configuration"""
        try:
            if self.__parsedInterface is None:
                return None
            for iface in QTN.QNetworkInterface.allInterfaces():
                if self.__parsedInterface == iface.humanReadableName():
                    return iface
                for address in iface.addressEntries():
                    ips = address.ip().toString().split("%")
                    if self.__parsedInterface in ips:
                        self.logger.debug("Binding network to interface: {}".format(iface.name()))
                        return iface
            raise Exception("Network device {} not found".format(self.__parsedInterface))
        except Exception as e:
            self.logger.warning("Could not get binding network interface: {}".format(e))
            return None

    @QtCore.Slot(object)
    @noexcept
    def setBindInterface(self, iface):
        self.logger.info("Setting bind interface to {}".format(iface))
        self.__udpSocket.close()
        self.__udpSocket.readyRead.disconnect()
        self.__parsedInterface = iface if len(iface) else None
        QtCore.QMetaObject.invokeMethod(self, "start")

    @QtCore.Slot()
    @noexcept
    def __readIncomingData(self):
        if not self.__udpSocket.hasPendingDatagrams():
            return
        (data, host, _port) = self.__udpSocket.readDatagram(self.__udpSocket.pendingDatagramSize())
        try:
            data_decoded = data.decode("UTF-8")
            json_data = json.loads(data_decoded)
            host_string = host.toString()
            self.signalGotData.emit(json_data, host_string)
            self.combined_data[host_string] = json_data
            self.signal_combined_data.emit(self.combined_data)
        except Exception as e:
            self.logger.debug("Could not read status data: {}".format(e), exc_info=True)
            self.logger.debug("{}".format(data))

    def _printData(self, json_data, host):
        self.logger.debug("{}: {}".format(host, json_data))

    def write_status(self, data, filename):
        if len(data) == 0:
            return
        with util.save_file.open_savefile(filename) as f:
            json.dump(data, f)
        self.logger.debug("Write status file to {}".format(filename))


if __name__ == '__main__':
    import sys
    q = QtCore.QCoreApplication(sys.argv)
    logging.basicConfig(level=10)
    config = {"StatusViewer": {"listenPort": 51000,
                               "ip": "239.1.1.1",
                               "multicastGroup": "239.1.1.1"}}
    s = StatusReader(config=config)
    s.signalGotData.connect(s._printData)
    s.start()
    q.exec_()
