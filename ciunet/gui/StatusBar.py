from PyQt5 import QtWidgets


class StatusBar(QtWidgets.QStatusBar):
    def __init__(self, mainwindow):
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
