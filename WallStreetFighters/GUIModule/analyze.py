# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import DataParserModule.dataParser as dataParser
import time

class Analyze (QtGui.QWidget):
        def __init__(self):
                QtGui.QWidget.__init__(self)
                self.initUi()
        def initUi(self):
		self.layout = QtGui.QHBoxLayout(self)
		self.textBrowser = QtGui.QTextBrowser(self)
		self.layout.addWidget(self.textBrowser)
