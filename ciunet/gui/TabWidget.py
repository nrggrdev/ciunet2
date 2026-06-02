import logging
import copy

from PyQt5 import QtCore, QtWidgets

from python_util import util as util
from . import LogView
from . import DeviceStatus
from . import ScannerInfo


LOGGING_FORMAT = "%(asctime)s %(levelname)7s: %(name)10s: %(message)s"
LOGGING_FORMATTER = util.datetime_helper.LoggingFormatter(fmt=LOGGING_FORMAT)
LOGGING_FORMATTER.hide_subseconds = True


class TabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent,loglevel=20,config=None):
        super().__init__(parent)
        self.config=config
        self.filter=MyFilter(loglevel)
        self.logger = logging.getLogger(self.__class__.__name__)
        print ("parent",parent,parent.parent)
        # LogViewer
        self.logViewer = LogView.LogViewWidget(self)
        self.logviewhandler = logging.StreamHandler(self.logViewer)
        self.logviewhandler.setFormatter(LOGGING_FORMATTER)
        self.logviewhandler.setLevel(logging.INFO)

        logging.getLogger().addHandler(self.logviewhandler)
        self.addTab(self.logViewer, self.tr("Log Viewer"))
        self.set_display_loglevel(loglevel)
        self.deviceStatus = DeviceStatus.DeviceStatus(self)
        self.addTab(self.deviceStatus, self.tr("Status Viewer"))
    @QtCore.pyqtSlot(object)

    def setLoggingPause(self,data):
        self.logViewer.setPause(data)
    @QtCore.pyqtSlot(object)
    @util.noexcept
    def set_display_loglevel(self, logging_level):
        self.logger.info("Setting logging level to {}.".format(logging_level))
        self.logviewhandler.setLevel(logging_level)
        self.logviewhandler.setLevel(0)
        self.filter.setLevel(logging_level)
#        print('='*80)
#        self.logviewhandler.addFilter(logging.Filter('TCEMManager'))
        self.logviewhandler.addFilter(self.filter)
        self.parent().parent.fileHandler.setLevel(logging_level)
#        self.parent().parent.queue_handler.setLevel(logging_level)
        print (self.parent().parent.rootLogger)
        self.parent().parent.rootLogger.setLevel(logging_level)
        self.parent().parent.rootLogger.setLevel(0)
        print (self.parent().parent,self.parent().parent.fileHandler,logging_level)

    def clear(self):
        self.logViewer.clear()

    def register_kiln(self, kiln):
        for scanner in kiln.scanners:
#            s = ScannerInfo.ScannerInfo(scanner, self)
            s = ScannerInfo.ScannerInfo1(scanner, self,config=self.config)
            self.addTab(s, str(scanner))

    def setLoggingfilter(self,data):
        self.filter.reset()
        self.filter.setaktiv(True)

        for item in data:
            self.filter.setFilterclass(item)

class MyFilter(logging.Filter, QtCore.QObject):
    newLoggingCLass=QtCore.pyqtSignal(object)
    def __init__(self,level=20):
        QtCore.QObject.__init__(self)
        self.loggingTypes=set()
        self.loggingFilter=set()
        self.filterClass=''
        self.aktiv=False
        self.level=level
    def reset(self):
        self.aktiv=False
#        self.loggingTypes=set()
        self.loggingFilter=set()

    def setaktiv(self,aktiv):
        self.aktiv=aktiv
    def setFilterclass(self,filterName):
        if not filterName in self.loggingFilter:
            self.loggingFilter.add(filterName)
        self.aktiv=True

    def setLevel(self,level):
 #       print(logging.BASIC_FORMAT)

 #       print ('loglevel',level,logging.WARNING)
        self.level=level

    def filter(self, record2):
        record = copy.copy(record2)
#        print (record)
        fields=['msg', 'filename', 'funcName', 'levelname', 'module',
                      'name', 'pathname', 'processName', 'threadName','levelno']
        data = str(getattr(record,'name'))
        datal = str(getattr(record,'levelno'))
  #      print ('level',datal,self.level)
        if not data in self.loggingTypes:
            self.loggingTypes.add(data)
            self.newLoggingCLass.emit(data)

#        print (self.loggingTypes)
#        print(data)
        if int(datal)<self.level:return
        if not self.aktiv:
            return record
        if data in self.loggingFilter:
              return record
