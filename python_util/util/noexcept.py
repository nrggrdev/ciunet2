import logging
import traceback
import functools

from PyQt5 import QtCore, QtWidgets


def noexcept(func, logger=logging):
    """ decorator to catch all unhandled exceptions, log them and discard them"""
    @functools.wraps(func)  # adjusts function meta-data, required eg for QtCore.pyqtSlot() decorated functions
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                logger.error("Exception in '{}': {}\n{}".format(func.__qualname__, e, traceback.format_exc()))
            except:
                pass
    return inner


def guiNoExcept(description="Exception"):
    """ decorator to catch all unhandled exceptions, log them and discard them"""
    def outer(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                text = "{}:\n*** {} ***".format(description, e)
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Error")
                msg.setText(text)
                msg.setDetailedText(traceback.format_exc())
                _r = msg.exec_()
                logging.warning("Unhandled exception in '{}': {}".format(func.__qualname__, e), exc_info=True)
        return inner
    return outer


def assert_equal_thread():
    def outer(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            object_thread = args[0].thread()
            caller_thread = QtCore.QThread.currentThread()
            #print(func.__qualname__, object_thread, caller_thread)
            if caller_thread != object_thread:
                raise RuntimeError("Function {} called from invalid thread {} != {}.".format(func.__qualname__,
                                                                                             caller_thread,
                                                                                             object_thread))
            return func(*args, **kwargs)
        return inner
    return outer
