import sys
from PyQt4 import QtGui,QtCore
def Calendar():
        cal = QtGui.QCalendarWidget()
        cal.setGridVisible(True)
        cal.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        cal.setFirstDayOfWeek(QtCore.Qt.Monday)
        cal.setHorizontalHeaderFormat(QtGui.QCalendarWidget.ShortDayNames)
        return cal
