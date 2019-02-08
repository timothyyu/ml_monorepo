import sys
from PyQt4 import QtGui
from mainGui import GuiMainWindow

class MainWindow(QtGui.QMainWindow):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        # obiekt Gui
        self.gui = GuiMainWindow()
        self.gui.setupGui(self)


    
    


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())
    
