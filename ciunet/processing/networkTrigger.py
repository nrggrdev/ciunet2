import logging
import json
import datetime
import time
from PyQt5 import QtCore, QtNetwork

from daq_net.daq.TriggerReceiver import TriggerReceiver
from python_util import util as util



class udpTrigger(QtCore.QObject):
    signal_trigger = QtCore.pyqtSignal(object)

    def __init__(self, trigger_config, parent,local=False):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        if local:
            self.host=QtNetwork.QHostAddress("127.0.0.1")
            self.port = int(trigger_config["local_port"])

        else:
            self.host = QtNetwork.QHostAddress(str(trigger_config["host"]))
            self.port = int(trigger_config["ext_port"])
        self.message=str.encode(trigger_config["message"])
        self.last_tireslip_trigger = None
        self.socket=QtNetwork.QUdpSocket()
    def start(self):
        self.socket.bind(self.port)
        self.socket.readyRead.connect(self.processPendingDatagrams)

    def checkMessage(self,datagram):
        return (datagram.find(self.message) >= 0)

    def processPendingDatagrams(self):
        t=datetime.datetime.now()

        while self.socket.hasPendingDatagrams():
            try:
                datagram, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
                # print ("received datagram from {} on port {}:{}".format(host,port,datagram))
                self.logger.debug("received datagram from {} on port {}:{}".format(host,port,datagram))

                found=self.checkMessage(datagram)

                # print (found)
                self.logger.debug("message gefunden: {}".format(found))
                # print ("message gefunden: {}".format(found))

                hostok=self.host.isEqual(host)
                # print ("host passt:{}".format(hostok))
                self.logger.debug("message gefunden: {}".format(found))

                if not (hostok and found):
                    # print ("sender not verifed :ignored")
                    self.logger.debug("sender not verifed :ignored")
                    continue



                if (hostok and found):
                    self.logger.debug("udp trigger detected")
                    if self.last_tireslip_trigger:
                        interval = t - self.last_tireslip_trigger
                    else:
                        interval=None
                    self.sendTrigger(interval)
                    self.last_tireslip_trigger = t


            except Exception as e:
                print (e)
                # return

    def sendTrigger(self,interval=None):
        self.signal_trigger.emit(interval)


class adamTrigger(udpTrigger):
    def __init__(self, trigger_config, parent):
        super().__init__(trigger_config, parent)

    def checkMessage(self,datagram):
        try:
            # print (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            # print(datagram)
            start=datagram[:9]
            if start!=b"#01RdFFFF":
                self.logger.debug ("no adam p2p")
                return False
            mask=datagram[9]<<3*8+datagram[10]<<2*8+datagram[11]<<1*8+datagram[12] # mit 1 sind daten maskiert
            l=datagram[13] #laenge, bei advanced modus 6
            slave_add=datagram[14] #Slave Adress: In the case of Adam-6050/6051/6052/6060/6066, this byte is 0x01.
            fun=datagram[15] #function code :In the case of Adam-6050/6051/6052/6060/6066, this byte is 0x05 (Advanced Mode).
            target=datagram[16]<<8+datagram[17]#Target Start Coil Address (High byte) +Target Start Coil Address (Low byte) :n the case of Adam-6050/6051/6052/6060/6066, this item means the (target Modbus address-1) (Advanced Mode). For example, the Modbus address of ADAM-6000 DIO module's DO channel 0 is 17. But, this item shall be set to 16.
            value=datagram[18:20]# IO Data 0xFF00=>ON,    0x0000=>OFF (Advanced Mode)
            # print (start)
            # print(mask)
            # print(l)
            # print(slave_add)
            # print (fun)
            # print (target)
            # print(value)
            # print ("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        except:
            return False
        self.logger.info(" p2p  Trigger received")
        return True

        #   #01RdFFFF\x00\x00\x00\x01\x06\x01\x05\x00\x10\xff\x00'


from PyQt5 import QtNetwork, QtGui, QtWidgets


class udpTriggerSender(QtNetwork.QUdpSocket):


    def __init__(self, parent=None,config=None):
        super(udpTriggerSender, self).__init__(parent)
        self.udpSocket = QtNetwork.QUdpSocket(self)
        ip="127.0.0.1"
        port=5168
        # print (config)
        message="test"
        try:
            c=config["kiln"]
            trigger_config=c["trigger"]
            # print (trigger_config)

            # ip=trigger_config["host"]
            port=int(trigger_config["local_port"])
            message=(trigger_config["message"])
        except Exception as e:
            print ("udp knopp ging ned mit ini")
            print(e)
        self.host=QtNetwork.QHostAddress("127.0.0.1")
        self.port=port
        self.message=message

    def sendTrigger(self):
        try:

            my_str_as_bytes = str.encode(self.message)
            # print (self.port)
            self.udpSocket.writeDatagram(my_str_as_bytes,self.host,self.port)
            # print ("trigger")
        except Exception as e:
            print (e)


    def processPendingDatagrams(self):

        while self.udpSocket.hasPendingDatagrams():
            datagram, host, port = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
            print ("H",datagram,host,port)


if __name__ == '__main__':
        import sys
        a = QtWidgets.QApplication(sys.argv)
        # graphRun = graphUDP()

        a.exec_()
