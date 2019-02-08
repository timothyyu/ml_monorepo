# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import DataParserModule.dataParser as dataParser
from ChartsModule.LightweightChart import *
import datetime
import TechAnalysisModule.oscilators as indicators
import time

class Home (QtGui.QWidget):
    def __init__(self,topList = None,mostList = None,gainerList = None, loserList = None, finObjList = None):
        self.topList = topList
        self.mostList = mostList
        self.loserList = loserList
        self.gainerList = gainerList
	self.finObjList = finObjList
	self.updateThread = UpdateThread(self.finObjList)
	self.connect(self.updateThread, QtCore.SIGNAL("Update"), self.updateHome)
        QtGui.QWidget.__init__(self)
        self.initUi()
    def initUi(self):
        self.gridLayout = QtGui.QGridLayout(self)
        #ramka zawierajaca obiekty z góry yahoo 
        self.topFrame = QtGui.QFrame(self)
        self.topFrame.setMaximumSize(QtCore.QSize(16777215, 320))
        self.topFrame.setMinimumSize(QtCore.QSize(0, 320))
        self.topFrame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.topFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.topLayout = QtGui.QGridLayout(self.topFrame)
        #spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        #self.topLayout.addItem(spacerItem)
        k = 0
        if self.topList:
            for objList in self.topList:
                self.addTopObject(objList,k)
                k=k+1


        
        #spacerItem1 = QtGui.QSpacerItem(39, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        #self.topLayout.addItem(spacerItem1)
        self.gridLayout.addWidget(self.topFrame, 0, 1, 1, 1)
        #koniec top ramki
        
        #test update top list
        #self.updateTopList([['a','a','a','a'],['a','a','a','a']])
       

        #ramka zawierajaca Most Activities, Gainers i Losers
        self.scrollArea = QtGui.QScrollArea(self)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setMinimumSize(QtCore.QSize(255, 0))
        self.scrollArea.setMaximumSize(QtCore.QSize(255, 16777215))
        self.scrollArea.setWidgetResizable(True)
        self.leftFrame = QtGui.QWidget()
        self.leftLayout = QtGui.QVBoxLayout(self.leftFrame)
        
        self.label1 = QtGui.QLabel("Most Activities",self.leftFrame)
        self.leftLayout.addWidget(self.label1)
        self.addTable(self.mostList)
        self.label2 = QtGui.QLabel("Gainers",self.leftFrame)
        self.leftLayout.addWidget(self.label2)
        self.addTable(self.gainerList)
        self.label3= QtGui.QLabel("Losers",self.leftFrame)
        self.leftLayout.addWidget(self.label3)
        self.addTable(self.loserList)
        
        #spacerItem2 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        #self.leftLayout.addItem(spacerItem2)
        self.scrollArea.setWidget(self.leftFrame)
        self.gridLayout.addWidget(self.scrollArea, 0, 0, 2, 1)

        #test update Table
        #self.updateTable([['a','a','a','a'],['a','a','a','a']],[],[])


        #rssLayout
        self.rssFrame = QtGui.QFrame(self)
        self.rssFrame.setAutoFillBackground(True)
        self.rssFrame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.rssFrame.setFrameShadow(QtGui.QFrame.Raised)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rssFrame.sizePolicy().hasHeightForWidth())
        self.rssFrame.setSizePolicy(sizePolicy)
        self.rssLayout = QtGui.QHBoxLayout(self.rssFrame)
        self.gridLayout.addWidget(self.rssFrame, 1, 1, 1, 1)

    def addTopObject(self,objList,k):
        self.frame = MyFrame(self)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setMaximumSize(QtCore.QSize(100, 100))
        self.frame.setMinimumSize(QtCore.QSize(100, 100))
        verticalLayout = QtGui.QVBoxLayout(self.frame)
        self.frame.nameLabel = QtGui.QLabel(self.frame)
        self.frame.nameLabel.setText(objList[0])
        self.frame.nameLabel.setStyleSheet('QLabel {color: blue}')
        verticalLayout.addWidget(self.frame.nameLabel)
        prizeLabel = QtGui.QLabel(self.frame)
        prizeLabel.setText(objList[1])
        verticalLayout.addWidget(prizeLabel)
        changeLabel = QtGui.QLabel(self.frame)
        if objList[2][0] == '-':
            changeLabel.setStyleSheet('QLabel {color: red}')
        else:
            changeLabel.setStyleSheet('QLabel {color: green}')
        changeLabel.setText(objList[2])
        verticalLayout.addWidget(changeLabel)
        precentLabel = QtGui.QLabel(self.frame)
        if objList[3][0] == '-':
            precentLabel.setStyleSheet('QLabel {color: red}')
        else:
            precentLabel.setStyleSheet('QLabel {color: green}')
        precentLabel.setText(objList[3])
        verticalLayout.addWidget(precentLabel)
        self.topLayout.addWidget(self.frame,k/4,(2*k)%8)
        # tworzymy LightWeightChart
        if  self.finObjList:
            finObj = self.finObjList[k]
            d = finObj.getArray('daily')
            dates=d['date']
            values=d['close']
            #values=indicators.adLine(d['adv'], d['dec'])
            #values=indicators.mcClellanOscillator(zajebisteDane['adv'], zajebisteDane['dec'])        
            #values=indicators.TRIN(zajebisteDane['adv'], zajebisteDane['dec'], zajebisteDane['advv'], zajebisteDane['decv'])
            zajebistyWykres = LightweightChart(self,dates,values,'A/D line')                        
            self.topLayout.addWidget(zajebistyWykres,k/4,(2*k+1)%8)#zajebiste Dane1

            
        
        
                                  
    def addTable(self,objList2):
        self.tableWidget = QtGui.QTableWidget(self)
        self.tableWidget.setEnabled(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget.sizePolicy().hasHeightForWidth())
        self.tableWidget.setSizePolicy(sizePolicy)
        self.tableWidget.setMinimumSize(QtCore.QSize(220, 180))
        self.tableWidget.setMaximumSize(QtCore.QSize(220, 180))
        font = QtGui.QFont()
        font.setKerning(True)
        font.setStyleStrategy(QtGui.QFont.PreferDefault)
        self.tableWidget.setFont(font)
        self.tableWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableWidget.setAutoScroll(False)
        self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setProperty("showDropIndicator", False)
        self.tableWidget.setDragDropOverwriteMode(False)
        self.tableWidget.setAlternatingRowColors(True)
        self.tableWidget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.tableWidget.setShowGrid(False)
        self.tableWidget.setWordWrap(True)
        self.tableWidget.setCornerButtonEnabled(True)
        self.tableWidget.setRowCount(5)
        self.tableWidget.setColumnCount(3)
        item = QtGui.QTableWidgetItem("Name")
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem("Prize")
        self.tableWidget.setHorizontalHeaderItem(1, item)
        #item = QtGui.QTableWidgetItem('Change')
        #self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem('%Chg')
        self.tableWidget.setHorizontalHeaderItem(2, item)
        k = 0
        if objList2:
            for objList in objList2:
                item = QtGui.QTableWidgetItem(objList[0])
                brush = QtGui.QBrush(QtGui.QColor(0, 0, 255))
                brush.setStyle(QtCore.Qt.NoBrush)
                item.setBackground(brush)
                brush = QtGui.QBrush(QtGui.QColor(0, 0, 255))
                brush.setStyle(QtCore.Qt.BDiagPattern)
                item.setForeground(brush)
                self.tableWidget.setItem(k, 0, item)
                #Prize
                item = QtGui.QTableWidgetItem(objList[1])
                item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                self.tableWidget.setItem(k, 1, item)
                #Change
                #item = QtGui.QTableWidgetItem(objList[2])
                #item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                #if objList[2][0] =='-':
                    #brush = QtGui.QBrush(QtGui.QColor(255, 0, 0))
                #else:
                    #brush = QtGui.QBrush(QtGui.QColor(0,255, 0)) 
                #brush.setStyle(QtCore.Qt.NoBrush)
                #item.setForeground(brush)
                #item.setFlags(QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
                #self.tableWidget.setItem(k, 2, item)
                #%chg
                item = QtGui.QTableWidgetItem(objList[2])
                item.setTextAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
                if objList[2][0] == '-':
                    brush = QtGui.QBrush(QtGui.QColor(255, 0, 0))
                else:
                    brush = QtGui.QBrush(QtGui.QColor(0,255, 0)) 
                brush.setStyle(QtCore.Qt.NoBrush)
                item.setForeground(brush)
                item.setFlags(QtCore.Qt.ItemIsEnabled)
                self.tableWidget.setItem(k, 2, item)
                k+=1
        
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(False)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(74)
        self.tableWidget.horizontalHeader().setHighlightSections(False)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setCascadingSectionResizes(False)
        self.tableWidget.verticalHeader().setHighlightSections(True)
        self.tableWidget.itemClicked.connect(self.tableClicked)
        self.leftLayout.addWidget(self.tableWidget)
     
    def updateTopList(self):
       
	self.topList = self.updateThread.topList
	self.finObjList = self.updateThread.finObjList
        #zamykamy wszystkie ramki
        ran = range(self.topLayout.count())
        for i in ran:
            widget = self.topLayout.itemAt(i).widget().close()
            

        # tworzymy nowe ramki z nowymi wartościami
        k = 0
        for objList in self.topList:
            self.addTopObject(objList,k)
            k = k+1

    def updateTable(self):
	
	self.mostList = self.updateThread.mostList
	self.loserList = self.updateThread.loserList
	self.gainerList = self.updateThread.gainerList
	

        ran = range(self.leftLayout.count())
        for i in ran:
            self.leftLayout.itemAt(i).widget().close()
        label1 = QtGui.QLabel("Most Activities",self.leftFrame)
        self.leftLayout.addWidget(label1)
        self.addTable(self.mostList)
        label2 = QtGui.QLabel("Gainers",self.leftFrame)
        self.leftLayout.addWidget(label2)
        self.addTable(self.gainerList)
        label3= QtGui.QLabel("Losers",self.leftFrame)
        self.leftLayout.addWidget(label3)
        self.addTable(self.loserList)
	
    def updateHome(self):
	self.updateTopList()
	self.updateTable()

    def startUpdating(self): 
	self.updateThread.start()

    def tableClicked(self,a):
        if a.column() ==0:
            self.emit(QtCore.SIGNAL("tabFromHome"),(a.text()))
            
class MyFrame(QtGui.QFrame):
    def __init__(self,parent):
        self.parent = parent
        QtGui.QWidget.__init__(self)
    def mouseDoubleClickEvent (self,event):
        if self.nameLabel.text() == "Dow":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('^DJI'))
        if self.nameLabel.text() == "Nasdaq":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('^IXIC'))
        if self.nameLabel.text() == "S&P 500":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('^GSPC'))
        if self.nameLabel.text() == "EUR/USD":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('EURUSD'))
        if self.nameLabel.text() == "10-Year Bond":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('^TNX'))
        if self.nameLabel.text() == "Gold":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('GCM12.CMX'))
        if self.nameLabel.text() == "Oil":
            self.parent.emit(QtCore.SIGNAL("tabFromHome"),('CLM12.NYM'))
    def mousePressEvent (self,event):
        if self.nameLabel.text() == "Dow":
            self.parent.topLayout.itemAtPosition(0,1).widget().show()
            self.parent.topLayout.itemAtPosition(0,3).widget().close()
            self.parent.topLayout.itemAtPosition(0,5).widget().close()
        if self.nameLabel.text() == "Nasdaq":
            self.parent.topLayout.itemAtPosition(0,3).widget().show()
            self.parent.topLayout.itemAtPosition(0,1).widget().close()
            self.parent.topLayout.itemAtPosition(0,5).widget().close()
        if self.nameLabel.text() == "S&P 500":
            self.parent.topLayout.itemAtPosition(0,5).widget().show()
            self.parent.topLayout.itemAtPosition(0,1).widget().close()
            self.parent.topLayout.itemAtPosition(0,3).widget().close()
        
class UpdateThread(QtCore.QThread):

    def __init__(self,finObjList):
        QtCore.QThread.__init__(self)
	self.mostList = []
	self.topList = []
	self.loserList = []
	self.gainerList = []
	self.finObjList = finObjList

    def __del__(self):
        self.wait()

    def run(self):
	while True:
		time.sleep(10)
		try:
			self.mostList = dataParser.top5Volume()
			self.loserList = dataParser.top5Losers()
			self.gainerList = dataParser.top5Gainers()
			self.topList = dataParser.getMostPopular()
			self.emit(QtCore.SIGNAL("Update"))	
			
			self.finObjListTemp = []
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("^DJI","index","Yahoo"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("^IXIC","index","Yahoo"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("^GSPC","index","Yahoo"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("EURUSD","forex","Stooq"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("10USY.B","bond","Stooq"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("XAUUSD","resource","Stooq"))
			self.finObjListTemp.append(dataParser.getDataToLightWeightChart("CL.F","resource","Stooq"))
                        self.finObjList = self.finObjListTemp
			array  = self.finObjList[1].getArray('daily')
		 			
		except dataParser.DataAPIException:
			pass
        
        
        
