import logging
import logging.handlers
import sys
import queue
import os
import warnings
import traceback
import signal
import datetime
import influxpy
from PyQt5 import QtCore, QtGui, QtWidgets
import pprint
#from  configobj import  ConfigObj
from python_util.util import configobj
ConfigObj = configobj.myConfigObj
import validate


# # Disable QThreads, get single-threaded application for profiling
# def new_move(self, _other):
#     print("Disabled moveToThread for single-threaded profiling.")
# QtCore.QObject.moveToThread = new_move


from daq_net.deviceStatus.receiver import StatusReader
from python_util import util as util
from ciunet import resources
from ciunet import version
from ciunet.writer.status_socket import StatusTransmitter
from ciunet.processing.kiln import Kiln
from ciunet.gui import MainWindow
from ciunet.writer import status_file
from ciunet.db import influxwriter
from ciunet.db import tireslip

LOGGING_FORMAT = "%(asctime)s;%(levelname)s;%(name)s;%(message)s"
LOGGING_FORMATTER = logging.Formatter(fmt=LOGGING_FORMAT)
DEFAULT_CONFIG_FILE = "./config/config_defaults.ini"
DEFAULT_CONFIG_SPEC_FILE = "./config/specs/configspec.ini"
CONFIG_FILE = "./config/config.ini"
CONFIG_DEVICE_STATUS = "./config/statusviewer.ini"


class MyQtApplication(QtWidgets.QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception as e:
            print("Unhandled exception in QT event loop: {}".format(e))
            print(traceback.format_exc())
        return False

class tireThread(util.WorkerThread):
    pass
class KilnThread(util.WorkerThread):
    pass
class influxThread(util.WorkerThread):
    pass



class StatusWriterThread(util.WorkerThread):
    pass


class DeviceStatusReceiverThread(util.WorkerThread):
    pass


class MyFileHandler2(logging.handlers.TimedRotatingFileHandler):
    """Non-blocking file handler. Used to enable moveable log-files on windows."""
    terminator = '\n'

    def __init__(self, filename, history_dst_path, level=logging.NOTSET):
        super().__init__(filename, encoding="utf-8", when="M")
        self.setLevel(level)
        self.history_dst_path = history_dst_path
        self.filename = os.path.abspath(filename)
        try:
            dir_path = os.path.dirname(self.filename)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        except Exception:
            pass

    def rotation_filename(self, default_name):
        """
        Modify the filename of a log file when rotating.

        :param default_name: The default name for the log file.
        """
        now = datetime.datetime.now()
        _head, tail = os.path.split(self.filename)
        dst = os.path.join(self.history_dst_path, "{:Y%Y/M%m/D%d/H%H}".format(now), tail)
        dst = os.path.abspath(dst)
        try:
            if not os.path.exists(dst):
                os.makedirs(dst)
        except Exception:
            pass
        return dst


class MyFileHandler(logging.handlers.BufferingHandler):
    """Non-blocking file handler. Used to enable moveable log-files on windows."""
    terminator = '\n'

    def __init__(self, filename):
        super().__init__(capacity=10)
        self.filename = os.path.abspath(filename)
        try:
            dir_path = os.path.dirname(self.filename)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        except Exception:
            pass

    def flush(self):
        """
        Override to implement custom flushing behaviour.

        This version just zaps the buffer to empty.
        """
        self.acquire()
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                for entry in self.buffer:
                    msg = self.format(entry)
                    f.write(msg)
                    f.write(self.terminator)
            self.buffer = []
        finally:
            self.release()


class MainClass(QtCore.QObject):
    def __init__(self):
        super().__init__()
        # Ensure we have all relative imports from the exe-file / main script, from whereever we start it
        executable_path = os.path.realpath(os.path.dirname(sys.argv[0]))
        os.chdir(executable_path)
        self.threads = []
        self.logging_handlers = []
        self.status_data = None

        # Set warnings as exceptions
        warnings.simplefilter("error")

        # QtCore.QTextCodec.setCodecForTr(QtCore.QTextCodec.codecForName("UTF-8"))
        QtCore.QCoreApplication.setOrganizationName("Gesotec GmbH")
        QtCore.QCoreApplication.setOrganizationDomain("gesotec.de")
        QtCore.QCoreApplication.setApplicationVersion(version.VERSION)
        QtCore.QCoreApplication.setApplicationName(self.tr("CIUNET", "ApplicationName"))
        # Since we have a Tray Icon, do not terminate on last window closed
        QtWidgets.QApplication.setQuitOnLastWindowClosed(False)
        QtWidgets.QApplication.setWindowIcon(QtGui.QIcon(":/icon/scanner1.ico"))
        self.logger = logging.getLogger(QtCore.QCoreApplication.applicationName())

    ##@QtCore.Slot()
    @util.noexcept
    def aboutToQuit(self):
        self.logger.info("Quitting application.")
        self.stop()

    def stop(self):
        self.logger.debug("Stopping")
        self.mainWindow.stop()
        self.kiln.quit()
        for thread in self.threads:
            thread.quit()
            thread.wait()
        self.logger.debug("Stopped")

    def start(self):
        #QtCore.QMetaObject.invokeMethod(self.statusTransmitter, "start")


        QtCore.QMetaObject.invokeMethod(self.kiln, "start")

        QtCore.QMetaObject.invokeMethod(self.status_writer, "start")
        # self.status_writer
        QtCore.QMetaObject.invokeMethod(self.device_status_receiver, "start")
        self.logger.info("CWD={}".format(os.getcwd()))
        self.logger.info("Started.")

    def handle_interrupt_signal(self, _signal, _frame):
        """Handle interrupt signal (SIGINT; CTRL-C) and quit program"""
        self.logger.debug("Interrupt Signal captured. Quitting application")
        QtCore.QCoreApplication.quit()

    def _init_logging(self, conf):
        try:
            log_file = conf["logging"]["logging_file"]
        except KeyError:
            # Get default logfile name using the executable name
            root, _ext = os.path.splitext(os.path.basename(sys.argv[0]))
            log_file = ".".join((root, "log"))
        try:
            log_level = int(conf["logging"]["logging_level"])
            print ("LOGLEVEL {}".format(log_level))
        except KeyError:

            print ("LOGGING ERROR!!!!!!!!!!!!!!!!!!!!!!!!!")
            log_level = logging.INFO
        # logging.basicConfig(level=log_level)
        try:
            influx_log = conf["logging"]["log2influx"]=='True'
        except KeyError:
            influx_log='False'

        que = queue.Queue(500)
        #queue_handler = logging.handlers.QueueHandler(que)
        # fileHandler = logging.handlers.TimedRotatingFileHandler(log_file, encoding="utf-8", when="midnight", backupCount=1)
        # fileHandler = logging.FileHandler(log_file, encoding="utf-8")
        # fileHandler = MyFileHandler(log_file, "loghistory")
        fileHandler = MyFileHandler(log_file)
        if influx_log:
            influxHandler = influxpy.UDPHandler("127.0.0.1", 8089, "ggr_logs",
                                          global_tags={"app": "ciunet"})
            self.logging_handlers.append(influxHandler)
            logging.getLogger().addHandler(influxHandler)
            influxHandler.setLevel(20)

        self.fileHandler=fileHandler
        self.logging_handlers.append(fileHandler)
        #self.logging_handlers.append(queue_handler)

        root = logging.getLogger()
        formatter = util.datetime_helper.LoggingFormatter(LOGGING_FORMAT)

        fileHandler.setFormatter(formatter)
        fileHandler.setLevel(log_level)
        self.logging_listener = logging.handlers.QueueListener(que, fileHandler)
        self.logging_listener = logging.handlers.QueueListener(que, influxHandler)
        logging.getLogger().addHandler(fileHandler)
        #root.addHandler(queue_handler)
        #queue_handler.setLevel(log_level)
        self.logging_listener.start()
        root.setLevel(log_level)
        self.rootLogger=root
#        self.queue_handler=queue_handler

    def _init_translations(self, conf):
        lang = conf["general"].get("language", "en")
        # QtTranslator
        if lang == "system":
            lang = QtCore.QLocale.system().name().split("_")[0]
        self.logger.debug("selected language: %s" % (lang))
        if lang != "en":
            gui_language_file = "./languages/" + lang + ".qm"
            self.default_locale = QtCore.QLocale(lang)
            QtCore.QLocale.setDefault(self.default_locale)
            # Our translator
            self.gui_translator = QtCore.QTranslator()
            if not self.gui_translator.load(gui_language_file):
                self.logger.warning("Could not load GUI translator at " + gui_language_file)
            else:
                QtCore.QCoreApplication.installTranslator(self.gui_translator)

    def _init_config(self):
        conf = ConfigObj(DEFAULT_CONFIG_FILE, configspec=DEFAULT_CONFIG_SPEC_FILE, encoding='UTF8')

        conf_user = ConfigObj(CONFIG_FILE)
        conf.merge(conf_user)

        validator = validate.Validator()
        result = conf.validate(validator, preserve_errors=True)
        if result is True:
            self.logger.info("Config file successfully validated.")
        elif result is False:
            raise RuntimeError("No valid config options present.")
        else:
            self.logger.error("Config validation error: {}".format(result))
            errors = MainClass.get_configspec_errors(conf, result)
            error_messages = ["{}.{}: {}<br><br><i>{}</i>".
                              format(e["prefix"], e["key"], e["msg"], e["comments"]) for e in errors]

        #    raise SyntaxError("Invalid Config Validation: {}".format("<br><br>".join(error_messages)))

        self.logger.debug("parsed config:\n {}.".format(pprint.pformat(conf)))
        return conf

    def _init_icon(self, conf):
        try:
            specified_icon_path = conf["general"]["icon"]
            if os.path.exists(specified_icon_path):
                icon = QtGui.QIcon(specified_icon_path)
                QtWidgets.QApplication.setWindowIcon(icon)
            else:
                raise ValueError("Specified icon path does not exist.")
        except Exception as e:
            self.logger.warning("Could not set specified icon: {}".format(e))
            QtWidgets.QApplication.setWindowIcon(QtGui.QIcon(":/icon/scanner1.png"))

    @staticmethod
    def get_configspec_errors(conf, data, prefix=[]):
        """Recursively get config specification errors as nice error message"""
        errors = []
        for key, value in data.items():
            if type(value) is dict:
                errors += MainClass.get_configspec_errors(conf[key], value, prefix + [key])
            elif value is not True:
                comment = conf.comments[key]
                error = {"prefix": ".".join(prefix),
                         "key": key,
                         "msg": value,
                         "comments": "<br>".join(comment)}
                errors.append(error)
        return errors

    #@QtCore.Slot()
    @util.noexcept
    def write_status_data(self):
        if self.status_data is None:
            return
        self.logger.debug("Saving device status.")
        self.device_status_receiver.write_status(self.status_data, "logs/device_status.json")

    #@QtCore.Slot(object)
    @util.noexcept
    def save_status_data(self, data):
        self.status_data = data

    def run(self, block_on_error=True):
        try:
            self.logger.info("Initializing.")
            conf = self._init_config()
            self._init_logging(conf)
            self._init_translations(conf)
            self._init_icon(conf)
            signal.signal(signal.SIGINT, self.handle_interrupt_signal)

            self.mainWindow = MainWindow.MainWindow(config=conf,parent=self)
            from ciunet.db import tireslip
            self.tireslipCalculator = tireslip.rawWriter(config=conf["database"])
            self.tireslipCalculator2 = tireslip.kiln(config=conf)

            kilnThread = KilnThread()
            self.threads.append(kilnThread)
            self.kiln = Kiln(config=conf["kiln"])
            self.kiln.moveToThread(kilnThread)
            self.kiln.setTireslipReceiver(self.tireslipCalculator)
            self.kiln.setTireslipCalc(self.tireslipCalculator2)
            self.mainWindow.register_kiln(self.kiln)
            self.mainWindow.menuBar().calib_menu.movement_menu.signalSetLowPosition.connect(self.tireslipCalculator2.updateHP0)
            self.mainWindow.menuBar().calib_menu.movement_menu.signalSetUpPosition.connect(self.tireslipCalculator2.updateHP1)
            self.status_writer = status_file.StatusFileWriter(config=conf, kiln=self.kiln, parent=None)
            status_writer_thread = StatusWriterThread()
            self.threads.append(status_writer_thread)
            self.status_writer.moveToThread(status_writer_thread)
#            self.influxwriter=influxwriter.influxWriter(config=conf["database"])
            deviceStatusConfig = ConfigObj(CONFIG_DEVICE_STATUS)
            self.device_status_receiver = StatusReader(deviceStatusConfig)
            device_status_receiver_thread = DeviceStatusReceiverThread()
            self.threads.append(device_status_receiver_thread)
            self.device_status_receiver.moveToThread(device_status_receiver_thread)
            self.device_status_receiver.signalGotData.connect(self.mainWindow.centralTab.deviceStatus.receiveData)
#            self.device_status_receiver.signalGotData.connect(self.influxwriter.receiveStatusData)

            self.status_data_updater = QtCore.QTimer()
            self.status_data_updater.setInterval(1000)
            self.status_data_updater.timeout.connect(self.write_status_data)

            for thread in self.threads:
                thread.start()
            self.mainWindow.statusTray.signalToggleTemperatureTransformation.connect(self.kiln.toggle_temperature_transformation)
            self.mainWindow.statusTray.signalToggleFOVmode.connect(self.kiln.toggle_fov_mode)
            self.device_status_receiver.signalGotData.connect(self.kiln.signalGotStatusData)
            self.device_status_receiver.signal_combined_data.connect(self.save_status_data)
            self.status_data_updater.start()
            #self.statusTransmitter = StatusTransmitter(self.kiln)

            self.start()
            if not conf["general"]["start_minimized"]:
                self.mainWindow.show()
        except Exception as _e:
            exc_type, exc_value, _exc_traceback = sys.exc_info()
            exceptions = traceback.format_exception(exc_type, exc_value, None, 0)
            exceptions = [e for e in exceptions if e.find("Traceback") < 0]
            exceptions = [e for e in exceptions if e.find("The above") < 0]
            traceback.print_exc(file=sys.stderr)
            self.logger.warning("Startup error!", exc_info=True)
            if block_on_error:
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle(self.tr("Startup Error"))
                formatted_exception_msg = ""
                for i, excp in enumerate(reversed(exceptions)):
                    if i > 0:
                        indent = i * 50
                        formatted_exception_msg += "<br>The above exception was the direct cause of the following"
                        formatted_exception_msg += " exception:<br><p style=\"text-indent: {}px;\"".format(indent)
                        formatted_exception_msg += "> "
                    else:
                        formatted_exception_msg += "<p>"
                    formatted_exception_msg += "<b>" + excp + "<b></p><br>"
                msg.setText(self.tr("Error while starting program. See log for more details.<br><br>{}".
                                    format(formatted_exception_msg)))
                msg.setDetailedText(traceback.format_exc())
                _r = msg.exec_()
            try:
                self.mainWindow.statusTray.hide()
            except Exception:
                pass
            raise


def main():
    if __debug__:
        app = MyQtApplication(sys.argv)
    else:
        app = QtWidgets.QApplication(sys.argv)
    try:
        m = MainClass()
        app.aboutToQuit.connect(m.aboutToQuit)
        m.run()
        r = app.exec_()
        m.logging_listener.stop()
        sys.exit(1)
    except Exception:
        r = 1
    logging.shutdown()
    sys.exit(r)
    return r
