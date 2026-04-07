import logging
import datetime
import sys
import traceback
from queue import Queue
import math
from Qt import QtCore, QtNetwork
import numpy_ringbuffer

from daq_net.daq.RawSegment import RawSegment
from daq_net.daq.RawLine import RawLine
from python_util.util.noexcept import noexcept
from python_util.util import datetime_helper
from python_util import util


class DaLiGrabber(QtCore.QObject):
    """Grabs data from network socket and sends it as a signal, thus allowing to enqueue it"""
    signalGotData = QtCore.Signal(object, object)

    def __init__(self, parent, groupaddr, sourceIP, networkInterface, port,multicast=True):
        super().__init__(parent)
        self.multicast=multicast
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("__init__")
        self.groupaddr = groupaddr
        self.ip = sourceIP
        self.networkInterface = networkInterface
        self.__port = port
        self.socket = QtNetwork.QUdpSocket(self)

        self.socket.readyRead.connect(self.__handleIncomingData)

        self.reset()

    @property
    def state(self):
        return self.socket.state()

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
        self.start()

    @QtCore.Slot()
    @noexcept
    def start(self):
        self.logger.debug("Starting.")
        if not self.socket.bind(QtNetwork.QHostAddress.AnyIPv4,
                                self.port,
                                QtNetwork.QUdpSocket.ShareAddress | QtNetwork.QUdpSocket.ReuseAddressHint):
            raise Exception("Receiver could not bind to socket.")
        if self.networkInterface is not None:
            if self.multicast:
                self.logger.info("Joining multicast group {} on interface: {}".
                                 format(self.groupaddr.toString(), self.networkInterface.humanReadableName()))
            if self.multicast:
                if not self.socket.joinMulticastGroup(self.groupaddr, self.networkInterface):
                    raise Exception("Could not join multicast group {} on if {}. error={}".
                                    format(self.groupaddr.toString(), self.networkInterface.humanReadableName(),
                                           self.socket.errorString()))
                else:
                    self.logger.info("Successfully joined multicast group.")
        else:
            if self.multicast:
                self.logger.info("Joining multicast group {}, no specific interface.".format(self.groupaddr.toString()))
                if not self.socket.joinMulticastGroup(self.groupaddr):
                    raise Exception("Could not join multicast group {}. error={}".
                                    format(self.groupaddr, self.socket.errorString()))
                else:
                    self.logger.info("Successfully joined multicast group.")
        #self.socket.readyRead.connect(self.__handleIncomingData)
        self.logger.debug("Started.")
        self.socket.setSocketOption(QtNetwork.QUdpSocket.ReceiveBufferSizeSocketOption,64*1024*1024)

    @QtCore.Slot()
    @noexcept
    @util.assert_equal_thread()
    def stop(self):
        self.logger.debug("Stopping.")
        self.socket.close()
#         try:
#             self.socket.readyRead.disconnect()
#         except TypeError as e:
#             self.logger.error("Could not disconnect socket readyRead: {}".format(e))
#             # Ignore disconnect error if there is no connection
#             pass
        self.reset()
        self.logger.debug("Stopped.")

    def reset(self):
        self.logger.info("Resetting.")
        self.received_datagrams = 0
        self.socket.setSocketOption(QtNetwork.QUdpSocket.ReceiveBufferSizeSocketOption,64*1024*1024)

    def quit(self):
        try:
            self.stop()
        except Exception:
            pass

    @QtCore.Slot()
    @noexcept
    def __handleIncomingData(self):


        while self.socket.hasPendingDatagrams():
            len_to_read = self.socket.pendingDatagramSize()
            if len_to_read <= 0:
                return
            # data, host, __port = self.socket.readDatagram(len_to_read)
            datagram = self.socket.receiveDatagram()
            host=datagram.senderAddress()
            data=datagram.data()
            if host != self.ip:
                return
            self.received_datagrams += 1
            self.signalGotData.emit(data, host)


class DaLiReceiver(QtCore.QObject):
    """XIOX DaLi WinIO or mbed Receiver"""
    signalGotSegment = QtCore.Signal(object)
    signalGotLine = QtCore.Signal(object)
    signalGotTrigger = QtCore.Signal(object)
    signalStarted = QtCore.Signal()
    signalStartError = QtCore.Signal(object)
    signalNewTimeData=QtCore.Signal(object)
    signalNewAnalogData=QtCore.Signal(object)

    def __init__(self, parent, grabber_parent, config, scanner,timechannels={}):
        super().__init__(parent=parent)
        self.lineAvg=12000
        self.maxlen=12000

        if 'maxlen' in config:

            try:
                self.maxlen = int(config["maxlen"])
            except Exception as e:
                pass
        self.lineAvg=self.maxlen

        self.davg=0
        self.sdavg = 0
        self.logger = logging.getLogger(self.__class__.__name__)
        self.minLineF=0.5
        self.minLineOffset=0.5
        self.rest = []
        self.hasOlddata = False
        self.timechannels=timechannels
        self.lastTime=0
        self.overflowCounter=0
        self.logger.info("Creating Receiver: {}".format(config))
        # QT5.8 does not respect "NO_PROXY" setting for local connections, thus causing problems with HOLCIM proxy config
        # See https://stackoverflow.com/q/42121008
        QtNetwork.QNetworkProxyFactory.setUseSystemConfiguration(False)
        self.scanner = scanner
        self.waited_for_line_sync = 0
        self.__groupaddr = None

        if "multicastGroup" in config:
            self.__parsedMulticastGroup = str(config["multicastGroup"])
            self.multicast=True
            self.__groupaddr = QtNetwork.QHostAddress(self.__parsedMulticastGroup)

        else:
            self.multicast=False
        self.__parsedSource = str(config["source"])
        self.__parsedPort = int(config["port"])
        self.__triggerchannel = int(config["triggerchannel"]) if "triggerchannel" in config else 2
        self.__parsedInterface = config["interface"] if "interface" in config else None

        self.__sourceIP = QtNetwork.QHostAddress(self.__parsedSource)
        self.__port = self.__parsedPort
        self.__startTime = None
        self.__lastPackageT = None
        self.__curLine = None
        self.validate_line_sync = False
        self.__lastImage_id = -1
        self.__lastInterval = None
        self.__lastTriggerTime = None
        self.__lastPeriod = datetime.timedelta(-1)
        self.max_line_length = 8192
        self.max_line_length = 15000
        self.max_line_length = 12010
        self.lastmbedTime=0
        self.minimum_words=8100
        self.minimum_words=100
        self.lastData=(0,)*8
        self.values=[(0,0)]*8
        self.lastTimer=dict()
        self.grabber = DaLiGrabber(grabber_parent, self.__groupaddr, self.__sourceIP,
                                   self.__getNetworkInterface(), self.__port,multicast=self.multicast)
        self.reset()
        self.connectSignals()

    def connectSignals(self):
        # Grabber should be able to always grab data from socket, and queue up
        # received data onto this receiver processing through a queued connection
        # Connect in start() so that ReceiverThread event loop handles the queue,
        # instead of the main gui-thread
        self.grabber.signalGotData.connect(self.__processDatagram, QtCore.Qt.QueuedConnection)
#        self.signalGotSegment.connect(self.__processRawLineSegment, QtCore.Qt.DirectConnection)
        self.signalGotSegment.connect(self.__processRawLineSegment_2, QtCore.Qt.DirectConnection)
        # self.__udpSocket.disconnected.connect(self.disconnected)
        # self.__udpSocket.error.connect(self.printSocketError)

    @QtCore.Slot()
    def printSocketError(self, error):
        print("socket error!!!", error)

    @QtCore.Slot()
    @noexcept
    def start(self):
        """Start the DAQ-Receiver."""
        try:
            self.logger.debug("Starting")
            QtCore.QMetaObject.invokeMethod(self.grabber, "start")
            self.__startTime = datetime_helper.current_local_time()
            self.logger.info("Started at t={}, bound to port {}".format(self.__startTime, self.__port))
            self.signalStarted.emit()
            self.mbedStartTime=-1
            self.lastmbedTime+-1
        except Exception as e:
            self.logger.error("Could not start receiver: {}".format(e))
            self.logger.debug(traceback.format_exc())
            assert(e is not None)
            self.signalStartError.emit(e)

    @property
    def ip(self):
        return self.grabber.ip

    @ip.setter
    def ip(self, value):
        self.reset()
        self.grabber.ip = value

    @property
    def port(self):
        return self.grabber.port

    @QtCore.Slot(object)
    @noexcept
    def setPort(self, port):
        self.reset()
        self.grabber.port = port

    @property
    def current_line(self):
        return self.__curLine

    @property
    def period(self):
        return self.__lastInterval.total_seconds()

    @property
    def freq(self):
        return 7.3
        return 1.0 / self.__lastInterval.total_seconds()

    @QtCore.Slot(object)
    @noexcept
    @util.assert_equal_thread()
    def setMulticastGroup(self, mgroup):
        QtCore.QMetaObject.invokeMethod(self.grabber, "stop")
        self.reset()
        self.grabber.groupaddr = QtNetwork.QHostAddress(mgroup)
        self.grabber.start()

    @QtCore.Slot(object)
    @noexcept
    @util.assert_equal_thread()
    def setBindInterface(self, iface):
        self.logger.info("Setting bind interface to {}".format(iface))
        QtCore.QMetaObject.invokeMethod(self.grabber, "stop")
        self.reset()
        self.__parsedInterface = iface if len(iface) else None
        self.grabber.networkInterface = self.__getNetworkInterface()
        self.grabber.start()

    @QtCore.Slot()
    @noexcept
    def disconnected(self):
        """Socket got disconnected."""
        self.logger.info("Disconnected.")

    def quit(self):
        QtCore.QMetaObject.invokeMethod(self, "stop")

    @QtCore.Slot()
    @noexcept
    #@util.assert_equal_thread()
    def stop(self):
        """Stop the DAQ-Receiver."""
        self.logger.debug("Stopping.")
        QtCore.QMetaObject.invokeMethod(self.grabber, "stop")
        self.reset()

    def reset(self):
        self.logger.info("Resetting.")
        try:
            self.grabber.reset()
        except Exception:
            pass
        self.receivedPackets = 0
        self.missedNWPackets = self.missedGBPackets = 0
        self.last_network_id = self.last_global_block_id = -1
        self.receivedLines = 0
        self.missedPackages = 0
        self.rejectedLines = 0
        self.waited_for_line_sync = 0
        self.missed_trigger = 0
        self.missed_trigger_total = 0
        self.__curLine = None
        self.lastLineLens=numpy_ringbuffer.RingBuffer(20)

        self.mbedStartTime = 0
        self.lastmbedTime = 0
        self.time_offset = 0

    @property
    def received_datagrams(self):
        return self.grabber.received_datagrams

    @property
    def status(self):
        data = {}
        try:
            """Get status of the DAQ-Receiver formatted as JSON."""
            data["IP"] = self.ip.toString()
            data["port"] = self.port
            data["received_datagrams"] = int(self.received_datagrams)
            data["receivedPackets"] = int(self.receivedPackets)
            data["lines"] = {}
            data["lines"]["received"] = int(self.receivedLines)
            data["lines"]["rejected"] = int(self.rejectedLines)
            try:
                data["lines"]["period"] = str(self.__lastInterval)
                data["lines"]["freq"] = 1.0 / self.__lastInterval.total_seconds()
            except Exception:
                pass
            data["uptime"] = str(datetime_helper.current_local_time() - self.__startTime)
        except Exception:
            self.logger.debug("Could not build status.", exc_info=True)
        return data

    def __getNetworkInterface(self):
        """Get specific network interface if one is specified in the configuration"""
        try:
            if self.__parsedInterface is None:
                return None
            for iface in QtNetwork.QNetworkInterface.allInterfaces():
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

    @QtCore.Slot(object, object)
    def __processDatagram(self, data, host):
        """ process received datagram. """
        try:
            segment = RawSegment(data,triggerchannel=self.__triggerchannel,lastmbedTime=self.lastmbedTime,
                                 starttime=self.mbedStartTime,offset=self.time_offset,lasttime=self.lastTime,overflows=self.overflowCounter)
            self.lastTime=segment.block_time_usec
            self.overflowCounter=self.lastTime%4294967295
            lasttime=segment.time_offset
            self.lastmbedTime=lasttime
            self.time_offset=segment.time_offset
            if self.mbedStartTime<0:
                self.mbedStartTime=lasttime
#            if self.segmanet.
            self.signalNewAnalogData.emit(segment.analogValues)
            self.signalGotSegment.emit(segment)
        except Exception as e:
            self.logger.debug("Could not process datagram.\nhost={}\nException={}".format(host.toString(), data, e))
            self.logger.debug(traceback.format_exc())

    def __checkTriggerInterval(self, segment):
        if self.__lastTriggerTime and self.__lastTriggerTime != segment.last_trigger_usec:
            self.logger.info("emitting trigger: {}".format(segment.last_trigger_usec))
            self.signalGotTrigger.emit(segment)
        self.__lastTriggerTime = segment.last_trigger_usec

    def __checkLineInterval(self, segment):
        try:
            self.__lastInterval = segment.block_time - self.__lastLineTime
        except Exception:
            pass
        self.__lastLineTime = segment.block_time

    def __clearLineBuffer(self):
        self.__curLine = None
        self.__lastLineTime = None

    def collect_segment_statistics(self, linesegment):
        self.receivedPackets += 1
        if self.last_network_id != -1:
            missed_nw_packet = linesegment.network_id - 1 - self.last_network_id
            self.missedNWPackets += missed_nw_packet
        self.last_network_id = linesegment.network_id

        if self.last_global_block_id != -1:
            missed_gb_packets = linesegment.global_block_id - 1 - self.last_global_block_id
            self.missedGBPackets += missed_gb_packets
        self.last_global_block_id = linesegment.global_block_id

    def validate_current_line(self, line):
        if not self.validate_line_sync:
            return True
        minimum_words = self.minimum_words
        line_length = line._intermediate_length
        if len(self.lastLineLens)>0:
            import numpy
            lineAvg=numpy.average(self.lastLineLens)
#            print (f'lines: {len(self.lastLineLens)},linelength: {lineAvg}')
        else:lineAvg=minimum_words
        self.lastLineLens.append(line_length)
#        if line_length < minimum_words:
#        if line_length < lineAvg*0.99 -5:
        if line_length < lineAvg*self.minLineF -self.minLineOffset:
            self.logger.warning("Last Line too short {} < {}".format(line_length, minimum_words))
            return False
        return True

    def checkTimer(self,data):
        """

                :param data: RawSegment
                :return:
                """
        new_data = False
        d=(data.all_channel_times())
#        print(d)

        if self.lastTimer!=d:
            rising, falling =d['rising'],d['falling']
            if 'rising' in self.lastTimer:
                old_rising, old_falling =self.lastTimer['rising'],self.lastTimer['falling']
#                print ('rising',old_rising,rising)
                for channel,value in enumerate(rising):
                    if channel in self.timechannels:
                        old_channel=old_rising[channel]
                        for item in value:
                            if not item in old_channel:
#                                print(f'channel {channel}: {item} >>rising')
                                self.logger.info(f'channel {channel}: {item} >>rising')
                                self.signalNewTimeData.emit((True,channel,self.timechannels[channel],item))

                for channel,value in enumerate(falling):
                    if channel in self.timechannels:
                        old_channel=old_falling[channel]
                        for item in value:
                            if not item in old_channel:
    #                            print(f'channel {channel}: {item} >>falling')
                                self.logger.info(f'channel {channel}: {item} >>falling')
                                self.signalNewTimeData.emit((False,channel,self.timechannels[channel],item))


            self.lastTimer=d




        return
#    @noexcept
    def __processRawLineSegment(self, linesegment):

        try:
            try:
                self.checkTimer(linesegment)
            except Exception as e:
                self.logger.debug(e)
#                print(e)
            self.collect_segment_statistics(linesegment)
            self.__checkTriggerInterval(linesegment)
            # Wait for the start of a line
            if self.__curLine is None and not linesegment.is_first():
                self.waited_for_line_sync += len(linesegment.data)
                if self.waited_for_line_sync > self.max_line_length:
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
                    self.waited_for_line_sync = 0
                return

            overflow = (self.max_line_length and self.__curLine and self.__curLine._intermediate_length > self.max_line_length)
            if linesegment.is_first() or overflow:
                if overflow:
                    self.logger.debug("Overflow.")
                if self.__curLine is None:
                    # If we do not yet have an existing Line, start a new one and return
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
                    return
                try:
                    if self.__curLine.last_segment:
                        if (linesegment.global_block_id - self.__curLine.last_segment.global_block_id) != 1:
                            raise RuntimeError("Last Line not complete.", "{}\n-->\n{}".format(repr(self.__curLine.last_segment), repr(linesegment)))
                    # From here on we already had a previous line, and have now received the first segment of a new one
                    if not self.validate_current_line(self.__curLine):
                        self.logger.warning('merge line!!!')
                        self.__curLine.add(linesegment,merge=True)
                    self.receivedLines += 1
                    self.lastLine = self.__curLine
                    self.__checkLineInterval(linesegment)
                    if len(self.__curLine.segments) and self.validate_current_line(self.__curLine):
                        self.__curLine.complete(self.rest)
                        self.rest=self.__curLine.rest
                        self.hasOlddata=self.__curLine.oversize
                        self.logger.info(self.__curLine.rawLen)
                        self.logger.debug(self.__curLine.ls)
                        self.lastLine.lastInterval = self.__lastInterval
                        self.signalGotLine.emit(self.lastLine)
                except Exception as e:
                    print('eeee',e)
                    self.logger.warning(e)
                    raise
                finally:
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
            else:
                # Append to existing Line
                self.__curLine.add(linesegment)
        except Exception as e:
            self.rejectedLines += 1
            self.__clearLineBuffer()
            self.logger.info("Rejected Line: {}".format(e.args[0]))
            if len(e.args) > 1:
                self.logger.debug("Rejected Line: {}".format(e.args[1]))
#    @noexcept
    def __processRawLineSegment_2(self, linesegment):
        try:
            self.checkTimer(linesegment)
            maxlen=self.maxlen
            if self.__curLine is None and not linesegment.is_first():
                self.hasFinLine=False
                return
            self.collect_segment_statistics(linesegment)
            self.__checkTriggerInterval(linesegment)
            if linesegment.is_first():
                if not self.__curLine is None:
                    self.lastLine = self.__curLine
                    if len(self.__curLine.data) > maxlen-400:
                        self.signalGotLine.emit(self.lastLine)
                        self.receivedLines += 1
                        import numpy
                        self.lastLineLens.append(len(self.__curLine.data) )

                        if len(self.lastLineLens) > 0:
                            avg = (numpy.average(self.lastLineLens))
                            self.davg= avg-int(avg)
                            self.sdavg= 0

                            self.lineAvg = int(numpy.average(self.lastLineLens))
                            self.logger.info(f'update avglen:{self.lineAvg}')
                self.__curLine = RawLine(linesegment, validate_line_sync=self.validate_line_sync)
                self.__curLine.data = linesegment.data

#                self.rest = self.__curLine.rest
#                self.hasOlddata = self.__curLine.oversize
            else:
                try:
                    self.__curLine.add2(linesegment)
                except:
                    self.rejectedLines+=1
                    self.logger.warning('missed package')
                    self.__curLine=None
                    return
 #               self.rest = self.__curLine.rest
                if len(self.__curLine.data)>=self.lineAvg:

                    #print(f'avglen:{self.lineAvg}')

                    self.lastLine = self.__curLine
                    self.sdavg+=self.davg
                    off=int(self.sdavg)
                    self.sdavg-=off

                    linecut=self.lineAvg+off+1
                    self.logger.info(f'avglen:{self.lineAvg}|{linecut}')
                    rest=self.lastLine.data[linecut:]
                    self.lastLine.data=self.lastLine.data[0:linecut]
                    self.signalGotLine.emit(self.lastLine)
                    self.receivedLines += 1
                    self.__curLine = RawLine(linesegment, validate_line_sync=self.validate_line_sync)
                    self.__curLine.data=rest
        except Exception as e:
            pass
#            import traceback
#            print(traceback.format_exc())
#            print(self.__curLine.data)
#            print(e)
#            import sys
#            sys.exit(0)
        return



        try:
            try:
                self.checkTimer(linesegment)
            except Exception as e:
                self.logger.debug(e)
#                print(e)
            self.collect_segment_statistics(linesegment)
            self.__checkTriggerInterval(linesegment)
            # Wait for the start of a line
            if self.__curLine is None and not linesegment.is_first():
                self.waited_for_line_sync += len(linesegment.data)
                if self.waited_for_line_sync > self.max_line_length:
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
                    self.waited_for_line_sync = 0
                return

            overflow = (self.max_line_length and self.__curLine and self.__curLine._intermediate_length > self.max_line_length)
            if linesegment.is_first() or overflow:
                if overflow:
                    self.logger.debug("Overflow.")
                if self.__curLine is None:
                    # If we do not yet have an existing Line, start a new one and return
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
                    return
                try:
                    if self.__curLine.last_segment:
                        if (linesegment.global_block_id - self.__curLine.last_segment.global_block_id) != 1:
                            raise RuntimeError("Last Line not complete.", "{}\n-->\n{}".format(repr(self.__curLine.last_segment), repr(linesegment)))
                    # From here on we already had a previous line, and have now received the first segment of a new one
                    if not self.validate_current_line(self.__curLine):
                        self.logger.warning('merge line!!!')
                        self.__curLine.add(linesegment,merge=True)
                    self.receivedLines += 1
                    self.lastLine = self.__curLine
                    self.__checkLineInterval(linesegment)
                    if len(self.__curLine.segments) and self.validate_current_line(self.__curLine):
                        self.__curLine.complete(self.rest)
                        self.rest=self.__curLine.rest
                        self.hasOlddata=self.__curLine.oversize
                        self.logger.info(self.__curLine.rawLen)
                        self.logger.debug(self.__curLine.ls)
                        self.lastLine.lastInterval = self.__lastInterval
                        self.signalGotLine.emit(self.lastLine)
                except Exception as e:
                    print('eeee',e)
                    self.logger.warning(e)
                    raise
                finally:
                    self.__curLine = RawLine(linesegment, self.validate_line_sync)
            else:
                # Append to existing Line
                self.__curLine.add(linesegment)
        except Exception as e:
            self.rejectedLines += 1
            self.__clearLineBuffer()
            self.logger.info("Rejected Line: {}".format(e.args[0]))
            if len(e.args) > 1:
                self.logger.debug("Rejected Line: {}".format(e.args[1]))
