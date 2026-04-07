import logging
import json
import datetime

from Qt import QtCore, QtNetwork

from daq_net.daq.TriggerReceiver import TriggerReceiver
from python_util import util as util


class TireslipReceiverThread(util.WorkerThread):
    pass


class TireSlipTrigger(QtCore.QObject):
    signal_trigger = QtCore.Signal(object)

    def __init__(self, trigger_config, parent):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tireslip_channel = int(trigger_config["tireslip_channel"])
        group = str(trigger_config["tireslip_group"])
        ip = str(trigger_config["tireslip_ip"])
        self.__parsedInterface = trigger_config.get("tireslip_interface", None)
        port = int(trigger_config["tireslip_port"])
        self.last_tireslip_trigger = None
        interface = self.__getNetworkInterface()
        self.tireslip_receiver = TriggerReceiver(group, ip, interface, port)
        self.tireslip_receiver_thread = TireslipReceiverThread()
        self.tireslip_receiver_thread.start()
        self.tireslip_receiver.moveToThread(self.tireslip_receiver_thread)

    def __getNetworkInterface(self):
        """Get specific network interface if one is specified in the configuration"""
        try:
            if self.__parsedInterface is None:
                return None
            for iface in QtNetwork.QNetworkInterface.allInterfaces():
                for address in iface.addressEntries():
                    ips = address.ip().toString().split("%")
                    if self.__parsedInterface in ips:
                        self.logger.debug("Binding network to interface: {}".format(iface.name()))
                        return iface
            raise Exception("Network device {} not found".format(self.__parsedInterface))
        except Exception as e:
            self.logger.warning("Could not get binding network interface: {}".format(e))
            return None

    @QtCore.Slot(object, object)
    @util.noexcept
    def receive_tireslip_trigger(self, data, _host):
        # print(_host, data, QtCore.QThread.currentThread())
        try:
            decoded_data = data.decode("ascii")
            parsed_data = json.loads(decoded_data)
            channel = parsed_data["ch"]
            self.logger.debug("Received TireSlip trigger at channel {}".format(channel))
            if channel != self.tireslip_channel:
                return
            timestamp = parsed_data["t"]
            if self.last_tireslip_trigger:
                interval = datetime.timedelta(microseconds=timestamp - self.last_tireslip_trigger)
            else:
                interval = None
            self.last_tireslip_trigger = timestamp
            self.logger.info("Received matching TireSlip trigger at channel={} timestamp={} interval={}".
                             format(channel, timestamp, interval))
            self.signal_trigger.emit(interval)
        except json.JSONDecodeError as e:
            self.logger.error("Could not parse Tireslip received data: {}".format(e))

    def start(self):
        self.tireslip_receiver.signal_got_trigger.connect(self.receive_tireslip_trigger)
        QtCore.QMetaObject.invokeMethod(self.tireslip_receiver, "start")
