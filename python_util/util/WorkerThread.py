import logging

from PyQt5 import QtCore


class WorkerThread(QtCore.QThread):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        self.logger.debug("starting.")
        self.exec_()
        self.logger.debug("ending.")
