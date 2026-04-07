import logging

from Qt import QtCore, QtGui, QtWidgets

from python_util import util as util
from ..processing.networkTrigger import udpTriggerSender
class LogFilterMenu(QtWidgets.QMenu):
    signal_Filter_changed=QtCore.Signal(object)
    signal_log_pause=QtCore.Signal(object)
    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.filterClasses=set()
        self.actiongroup=QtWidgets.QActionGroup(self)
        self.actiongroup.setExclusive(False)
        self.allAction=QtWidgets.QAction('all')
        self.allAction.triggered.connect(self.setAll)
        self.addAction(self.allAction)
        self.resetAction=QtWidgets.QAction('reset')
        self.resetAction.triggered.connect(self.reset)
        self.addAction(self.resetAction)

        self.addSeparator()

    def setAll(self,data):
        for a in self.actiongroup.actions():
            a.setChecked(True)
        self.setFilter()

    def reset(self,data):
        for a in self.actiongroup.actions():
            a.setChecked(False)
        self.setFilter()

    def addClass(self,classname):
        a=QtWidgets.QAction(classname)
        a.setCheckable(True)
        self.actiongroup.addAction(a)
        self.addAction(a)
        a.triggered.connect(self.setFilter)



    def setFilter(self):
        print(self.sender())
        filters=[]
        for a in self.actiongroup.actions():
            if a.isChecked():
                print(a.text())
                filters.append(a.text())
        self.signal_Filter_changed.emit(filters)

class LoglevelMenu(QtWidgets.QMenu):
    signal_loglevel_changed = QtCore.Signal(object)

    def __init__(self, name, parent,config):
        self.logger = logging.getLogger()
        self.config=config["logging"]
        super().__init__(name, parent)
        action_group = QtWidgets.QActionGroup(self)
        action_group.setExclusive(True)
        self.logging_level_actions = [(logging.DEBUG, QtWidgets.QAction(self.tr("DEBUG"), action_group)),
                                      (logging.INFO, QtWidgets.QAction(self.tr("INFO"), action_group)),
                                      (logging.WARNING, QtWidgets.QAction(self.tr("WARNING"), action_group)),
                                      (logging.ERROR, QtWidgets.QAction(self.tr("ERROR"), action_group)),
                                      (logging.CRITICAL, QtWidgets.QAction(self.tr("CRITICAL"), action_group)),
                                      ]
        for _level, action in self.logging_level_actions:
            action.setCheckable(True)
            action.triggered.connect(self._loglevel_changed)
            self.addAction(action)
            if self.logger.level==_level:
                action.setChecked(True)
            else:
                pass
                # self.logging_level_actions[3][1].setChecked(True)

    def _get_logging_level(self):
        for level, action in self.logging_level_actions:
            if action.isChecked():
                print (level)
                return level
        raise RuntimeError("No logging level checked.")

    @QtCore.Slot()
    @util.guiNoExcept()
    def _loglevel_changed(self):
        self.signal_loglevel_changed.emit(self._get_logging_level())

class DialogMovement(QtWidgets.QDialog):
    signalSetPosition=QtCore.Signal(float)
    def __init__(self,parent=None,title="new Pos",pos=0):
        super().__init__(parent=parent)
        l=QtWidgets.QGridLayout()
        self.valEdit=QtWidgets.QLineEdit(f"{pos}")
        valLabel=QtWidgets.QLabel(title)
        self.validatorPos=QtGui.QDoubleValidator()
        self.valEdit.setValidator(self.validatorPos)
        self.buttons=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        l.addWidget(valLabel,0,0)
        l.addWidget(self.valEdit,0,1)
        l.addWidget(self.buttons,1,0,1,2)
        self.buttons.rejected.connect(self.close)
        self.buttons.accepted.connect(self.setPosition)
        self.setLayout(l)
#        self.buttons.clicked.connect(self.updateCalib)
#        self.buttons.clicked.connect(self.close)
#        self.buttons.rejected.connect(self.close)
#        self.buttons.accepted.connect(self.updateCalib)
    def setPosition(self):
        try:
            if(self.valEdit.hasAcceptableInput()):
                try:
                    self.signalSetPosition.emit(float(self.valEdit.text()))
                    self.close()
                    return
                except Exception as e:print(e)
            QtWidgets.QMessageBox.warning(self,'invalid Position','invalid Position',QtWidgets.QMessageBox.Ok)
        except Exception as e:
            print(e)

class movementMenu(QtWidgets.QMenu):
    signalSetLowPosition=QtCore.Signal(float)
    signalSetUpPosition=QtCore.Signal(float)

    def __init__(self, menubar,config):
        super().__init__(menubar)
        self.menubar = menubar
        self.movement=False
        if 'tireslip' in config:
            tsc=config['tireslip']
            if 'movement' in tsc:
                mc=tsc['movement']
                self.movement=True
                p0=float(mc['Pos0'])
                p1=float(mc['Pos1'])

                self.ActionSetP0 = QtWidgets.QAction('set lower point')
                self.ActionSetP1 = QtWidgets.QAction('set upper point')
                self.DialogLow=DialogMovement(self,"current Kiln Position",p0)
                self.DialogUp=DialogMovement(self,"current Kiln Position",p1)
                self.ActionSetP0.triggered.connect(self.DialogLow.show)
                self.ActionSetP1.triggered.connect(self.DialogUp.show)
                self.addAction(self.ActionSetP0)
                self.addAction(self.ActionSetP1)
                self.DialogLow.signalSetPosition.connect(self.signalSetLowPosition.emit)
                self.DialogUp.signalSetPosition.connect(self.signalSetUpPosition.emit)

class calibrationMenu(QtWidgets.QMenu):
    def __init__(self, menubar,config):
        super().__init__(menubar)
        self.menubar = menubar
        self.config=config
        print(config)
        self.setTitle(self.tr("Calibration"))
        self.movement_menu = movementMenu(self.tr("horizontal movement"),config )
        if self.movement_menu.movement:
            self.addMenu(self.movement_menu    )


class FileMenu(QtWidgets.QMenu):
    clearLogViewSignal=QtCore.Signal()
    signal_log_pause=QtCore.Signal(object)
    def __init__(self, menubar,config):
        super().__init__(menubar)
        self.menubar = menubar
        self.config=config
        self.setTitle(self.tr("File"))
        self.trigger=udpTriggerSender(config=config)

        self.loglevel_menu = LoglevelMenu(self.tr("Log level"), self,config=config)
        self.logfilter_menu = LogFilterMenu(self.tr("Log filter"), self)
        self.clearAction=QtWidgets.QAction('clear Logging')
        self.clearAction.triggered.connect(self.clearLogViewSignal.emit)
        self.clearAction.setShortcut(self.tr("CTRL+R"))
        self.pauseAction=QtWidgets.QAction('pause Logging')
        self.pauseAction.triggered.connect(self.signal_log_pause.emit)
        self.pauseAction.setShortcut(self.tr("CTRL+L"))
        self.pauseAction.setCheckable(True)

        self.addMenu(self.loglevel_menu)
        self.addMenu(self.logfilter_menu)
        self.addAction(self.clearAction)
        self.addAction(self.pauseAction)

        # quit_key = " (" + QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Q).toString() + ")"
        # self.quit_action = QtWidgets.QAction(self.tr("Quit") + quit_key, self)
        self.quit_action = QtWidgets.QAction(self.tr("Quit"),self)
        self.quit_action.setShortcut(self.tr("CTRL+Q"))
        self.addAction(self.quit_action)
        self.quit_action.triggered.connect(self.menubar.mainwindow.quitClicked)

        # trigger_key = " (" + QtGui.QKeySequence(QtCore.Qt.CTRL + QtCore.Qt.Key_Q).toString() + ")"
        # self.trigger_action = QtWidgets.QAction(self.tr("Trigger") + trigger_key, self)
        self.trigger_action = QtWidgets.QAction(self.tr("Trigger"), self)
        self.trigger_action.setShortcut(self.tr("CTRL+T"))
        self.addAction(self.trigger_action)
        self.trigger_action.triggered.connect(self.trigger.sendTrigger)



class HelpMenu(QtWidgets.QMenu):
    def __init__(self, menubar):
        super().__init__(menubar)
        self.menubar = menubar

        self.setTitle(self.tr("Help"))

        self.about_action = QtWidgets.QAction(self.tr("About"), self)
        self.addAction(self.about_action)
        self.about_action.triggered.connect(self.menubar.mainwindow.showAbout)

        self.aboutqt_action = QtWidgets.QAction(self.tr("About Qt"), self)
        self.addAction(self.aboutqt_action)
        self.aboutqt_action.triggered.connect(self.aboutqtClicked)

    @QtCore.Slot()
    def aboutqtClicked(self):
        QtWidgets.QMessageBox.aboutQt(self)

    @QtCore.Slot()
    def langClicked(self):
        pass


class MainWindowMenuBar(QtWidgets.QMenuBar):
    def __init__(self, mainwindow,config):
        super().__init__(mainwindow)
        self.mainwindow = mainwindow

        self.file_menu = FileMenu(self,config)
        self.calib_menu=calibrationMenu(self,config)
        self.addMenu(self.file_menu)
        self.addMenu(self.calib_menu)
        self.addMenu(HelpMenu(self))
