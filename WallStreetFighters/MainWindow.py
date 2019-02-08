import sys
import os
from PyQt4 import QtGui
from mainGui import GuiMainWindow
import DataParserModule.dataParser as dataParser
import cPickle

class MainWindow(QtGui.QMainWindow):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        # obiekt Gui
        self.gui = GuiMainWindow()
        self.gui.setupGui(self)
        
    def closeEvent(self, event):

        FILE = open('data.wsf','w')
        dataParser.saveHistory(FILE)
        FILE.close()
        valueList = [self.gui.home.topList,self.gui.home.mostList,self.gui.home.loserList,self.gui.home.gainerList, self.gui.home.finObjList]
        cPickle.dump(valueList, open('save.wsf','w'))
        ran = range(self.gui.tabs.count())
        tabHistoryList = []
        for i in ran:
            if i >2:
                t=  self.gui.tabs.widget(i).getSettings()
                tabHistoryList.append(t)
        cPickle.dump(tabHistoryList, open('tabHistory.wsf','w'))
        settingsList = []
        settingsList = self.gui.tabs.widget(2).getVal()
        cPickle.dump(settingsList, open('settingsList.wsf','w'))
    def keyPressEvent (self, QKeyEvent):
        if QKeyEvent.key() == 16777274:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        if QKeyEvent.key() == 16777216:
            if self.isFullScreen():
                self.showNormal()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
   
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())
    print "ddd"
    while True:
        app.processEvents()
    
    
    
