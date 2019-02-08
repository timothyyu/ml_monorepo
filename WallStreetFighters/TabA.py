# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtGui,QtCore
from GUIModule.Tab import *
from GUIModule.Calendar import *
import datetime
import os
from ChartsModule.Chart import Chart
from ChartsModule.CompareChart import CompareChart
from ChartsModule.FormationDrawer import FormationDrawer
import DataParserModule.dataParser as dataParser
from TechAnalysisModule.strategy import Strategy
from GUIModule.analyze import Analyze

class TabA(QtGui.QWidget):
    def __init__(self,finObjType = None, indexModel=None,stockModel=None,forexModel=None,bondModel= None,
                 resourceModel = None,futuresModel = None, qModelIndex = None,settings = None,listName=None,showLists = True):
        self.finObjType = finObjType
        self.indexModel = indexModel
        self.stockModel = stockModel
        self.forexModel = forexModel
        self.bondModel = bondModel
        self.resourceModel = resourceModel
        self.futuresModel = futuresModel
        self.showLists = showLists
        self.settings = settings
        self.qModelIndex = qModelIndex #lista przy porównywaniu
        self.listName = listName
        self.indicatorList = []
        self.indicatorCheckBoxList = []
        self.oscilatorCheckBoxList = []
        self.oldStart = None
        self.oldEnd = None
        self.oldStep = None
        self.chart =None
        QtGui.QWidget.__init__(self)
        self.initUi()
    def initUi(self):
        
        
	#wywołujemy metodę z modułu GUIModule.Tab
        #która tworzy podstawowe elementy GUI
        tabUi(self,self.showLists)
        
	self.hasChart = False #sprawdzenie czy istnieje 
	self.currentChart = ""
	self.chart = None
	self.finObj = None
	
        self.setObjectName("tabA")

        #ustawiamy modele danych
        if self.showLists:
            self.indexListView.setModel(self.indexModel)
            self.stockListView.setModel(self.stockModel)
            self.forexListView.setModel(self.forexModel)
            self.bondListView.setModel(self.bondModel)
            self.resourceListView.setModel(self.resourceModel)
            self.futuresListView.setModel(self.futuresModel)
        
        if not isinstance( self.qModelIndex,list):#  and self.finObj != None:
            self.scrollArea = QtGui.QScrollArea(self.optionsFrame)
            self.scrollArea.setWidgetResizable(True)
            self.buttonsFrame = QtGui.QWidget()
            self.buttonsLayout = QtGui.QGridLayout(self.buttonsFrame)
            self.buttonsLayout.setContentsMargins(-1, 0, -1, -1)
            self.idicatorsLabel = QtGui.QLabel('Indicators:',self.optionsFrame)
            self.buttonsLayout.addWidget(self.idicatorsLabel,0,2,1,1)
            
            #check box dla SMA
            self.smaCheckBox = QtGui.QCheckBox("SMA",self.optionsFrame)
            self.buttonsLayout.addWidget(self.smaCheckBox,1,2,1,1)
            self.indicatorCheckBoxList.append(self.smaCheckBox)
            #check box dla WMA
            self.wmaCheckBox = QtGui.QCheckBox("WMA",self.optionsFrame)
            self.buttonsLayout.addWidget(self.wmaCheckBox,2,2,1,1)
            self.indicatorCheckBoxList.append(self.wmaCheckBox)
            #check box dla EMA
            self.emaCheckBox = QtGui.QCheckBox("EMA",self.optionsFrame)
            self.buttonsLayout.addWidget(self.emaCheckBox,3,2,1,1)
            self.indicatorCheckBoxList.append(self.emaCheckBox)
            #check box dla bollinger
            self.bollingerCheckBox = QtGui.QCheckBox("bollinger",self.optionsFrame)
            self.buttonsLayout.addWidget(self.bollingerCheckBox,0,3,1,1)
            self.indicatorCheckBoxList.append(self.bollingerCheckBox)

            self.oscilatorsLabel = QtGui.QLabel('Oscilators:',self.optionsFrame)
            self.buttonsLayout.addWidget(self.oscilatorsLabel,1,3,1,1)
            #check box dla wskaźnika momentum
            self.momentumCheckBox = QtGui.QRadioButton("momentum",self.optionsFrame)
            self.buttonsLayout.addWidget(self.momentumCheckBox,2,3,1,1)
            self.oscilatorCheckBoxList.append(self.momentumCheckBox)
            #check box dla CCI
            self.cciCheckBox = QtGui.QRadioButton("CCI",self.optionsFrame)
            self.buttonsLayout.addWidget(self.cciCheckBox,3,3,1,1)
            self.oscilatorCheckBoxList.append(self.cciCheckBox)
            #check box dla ROC
            self.rocCheckBox = QtGui.QRadioButton("ROC",self.optionsFrame)
            self.buttonsLayout.addWidget(self.rocCheckBox,0,4,1,1)
            self.oscilatorCheckBoxList.append(self.rocCheckBox)
            #check box dla RSI
            self.rsiCheckBox = QtGui.QRadioButton("RSI",self.optionsFrame)
            self.buttonsLayout.addWidget(self.rsiCheckBox,1,4,1,1)
            self.oscilatorCheckBoxList.append(self.rsiCheckBox)
            #check box dla Williams Oscilator
            self.williamsCheckBox = QtGui.QRadioButton("williams",
                                                         self.optionsFrame)
            self.buttonsLayout.addWidget(self.williamsCheckBox,2,4,1,1)
            self.oscilatorCheckBoxList.append(self.williamsCheckBox)

            #horizontal line
            self.line = QtGui.QFrame(self.buttonsFrame)
            self.line.setFrameShape(QtGui.QFrame.HLine)
            self.line.setFrameShadow(QtGui.QFrame.Sunken)
            self.buttonsLayout.addWidget(self.line, 4, 2, 1, 3)


            #check box dla drawTrend
            self.drawTrendCheckBox = QtGui.QCheckBox("show Trend",self.optionsFrame)
            self.buttonsLayout.addWidget(self.drawTrendCheckBox,5,2,1,1)
            #label dla grubosci lini
            self.lineWidthLabel = QtGui.QLabel("line Width",self)
            self.buttonsLayout.addWidget(self.lineWidthLabel,5,3,1,1)
            #spin box dla grubosci lini
            self.lineWidthSpinBox = QtGui.QDoubleSpinBox(self.optionsFrame)
            self.lineWidthSpinBox.setFrame(True)
            self.lineWidthSpinBox.setReadOnly(False)
            self.lineWidthSpinBox.setButtonSymbols(QtGui.QAbstractSpinBox.PlusMinus)
            self.lineWidthSpinBox.setDecimals(1)
            self.lineWidthSpinBox.setMinimum(0.5)
            self.lineWidthSpinBox.setMaximum(5.0)
            self.lineWidthSpinBox.setSingleStep(0.5)
            self.lineWidthSpinBox.setProperty("value", 1.0)
            self.buttonsLayout.addWidget(self.lineWidthSpinBox,5,4,1,1)            

            self.scrollArea.setWidget(self.buttonsFrame)
            if self.showLists != True:
                self.optionsLayout.addWidget(self.scrollArea, 0, 1, 4, 4)         
            else:
                self.chartsLayout.addWidget(self.scrollArea)

        #(przyciski dodajemy na sam koniec okna)wyswietlanie wykresu
        self.optionsLayout.addWidget(addChartButton(self),0,5,4,4)      
        if self.qModelIndex != None:
            if isinstance( self.qModelIndex,list):
                self.paintCompareChart()
                self.chartTypeComboBox.setEnabled(False)
                self.volumenCheckBox.setEnabled(False)
            else:
                self.paint2Chart()
            self.dateButton.clicked.connect(self.updateDate)
            self.stepComboBox.currentIndexChanged.connect(self.updateStep)
            self.logRadioButton.toggled.connect(self.updateScale)
            
            if not isinstance( self.qModelIndex,list):
                self.chartTypeComboBox.currentIndexChanged.connect(self.updateChartType)
                self.volumenCheckBox.stateChanged.connect(self.updateHideVolumen)
                self.paintCheckBox.stateChanged.connect(self.updateEnablePainting)
                for box in self.oscilatorCheckBoxList:
                    box.clicked.connect(self.updateOscilator)
                self.smaCheckBox.stateChanged.connect(self.smaChanged)
                self.emaCheckBox.stateChanged.connect(self.emaChanged)
                self.wmaCheckBox.stateChanged.connect(self.wmaChanged)
                self.drawTrendCheckBox.stateChanged.connect(self.updateDrawTrend)
                self.bollingerCheckBox.stateChanged.connect(self.bollingerChanged)
                self.analyzeButton.pressed.connect(self.newAnalyzeTab)
                self.showChartPatternsButton.pressed.connect(self.showChartPatterns)
            self.startDateEdit.dateChanged.connect(self.checkDate)
            self.endDateEdit.dateChanged.connect(self.checkDate)
        else:
            self.analyzeButton.setCheckable(False)
            self.compareCheckBox.stateChanged.connect(self.compareChanged)
            self.indexListView.clicked.connect(self.addSymbolToCompareLine)
            self.stockListView.clicked.connect(self.addSymbolToCompareLine)
            self.forexListView.clicked.connect(self.addSymbolToCompareLine)
            self.bondListView.clicked.connect(self.addSymbolToCompareLine)
            self.resourceListView.clicked.connect(self.addSymbolToCompareLine)
            self.futuresListView.clicked.connect(self.addSymbolToCompareLine)
            

    def newAnalyzeTab(self):
        strategy = Strategy(self.chart.data)
        text = strategy.analyze()
        self.analyzeTab = Analyze()
        nameTab = str(self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0])
        nameTab = "Analyze " + nameTab
        self.parent().parent().parent().parent().gui.tabs.setCurrentIndex(self.parent().parent().parent().parent().gui.tabs.addTab(self.analyzeTab,nameTab))
        self.analyzeTab.textBrowser.setText(text)
    def showChartPatterns(self):
        settings = self.parent().parent().parent().parent().gui.settingsTab.getVal()

        lineStyle = []
        for x in settings[1]:
            if x == 0:
                lineStyle.append('solid')
            elif x == 1:
                lineStyle.append('dashed')
            elif x == 2:
                lineStyle.append('dashdot')
            elif x == 3:
                lineStyle.append('dotted')
            else:
                lineStyle.append('-')
            
        color = []
        for x in settings[2]:
            if x == 0:
                color.append('r')
            elif x == 1:
                color.append('b')
            elif x == 2:
                color.append('y')
            elif x == 3:
                color.append('b')
            elif x == 4:
                color.append('g')
            elif x == 5:
                color.append('c')
            else:
                color.append('r')
        values = settings[0]
        enables = settings[3]
                
        strategy = Strategy(self.chart.data)
        strategy.setPositiveSignal(values[0])
        strategy.setNegativeSignal(values[1])
        #ustawiane wartości
        if enables[2]:
            strategy.setTrendVal(values[2])
        else:
            strategy.disableTrendVal()
            
        if enables[3]:
            strategy.setHeadAndShouldersVal(values[3])
        else:
            strategy.disableHeadAndShouldersVal()
            
        if enables[4]:
            strategy.setTripleTopVal(values[4])
        else:
            strategy.disableTripleTopVal()
            
        if enables[5]:
            strategy.setRisingWedgeVal(values[5])
        else:
            strategy.disableRisingWedgeVal()
            
        if enables[6]:
            strategy.setFallingTriangleVal(values[6])
        else:
            strategy.disableFallingTriangleVal()
            
        if enables[7]:
            strategy.setReversedHeadAndShouldersVal(values[7])
        else:
            strategy.disableReversedHeadAndShouldersVal()
            
        if enables[8]:
            strategy.setTripleBottomVal(values[8])
        else:
            strategy.disableTripleBottomVal()
            
        if enables[9]:
            strategy.setFallingWedgeVal(values[9])
        else:
            strategy.disableFallingWedgeVal()
            
        if enables[10]:
            strategy.setRisingTriangleVal(values[10])
        else:
            strategy.disableRisingTriangleVal()
            
        if enables[11]:
            strategy.setSymetricTriangleVal(values[11])
        else:
            strategy.disableSymetricTriangleVal()
            
        if enables[12]:
            strategy.setRectangleVal(values[12])
        else:
            strategy.disableRectangleVal()
            
        if enables[13]:
            strategy.setFlagPennantVal(values[13])
        else:
            strategy.disableFlagPennantVal()
            
        if enables[14]:
            strategy.setOscilatorsVal(values[14])
        else:
            strategy.disableOscilatorsVal()
            
        if enables[15]:
            strategy.setNewHighNewLowVal(values[15])
        else:
            strategy.disableNewHighNewLowVal()
            
        if enables[16]:
            strategy.setBollignerVal(values[16])
        else:
            strategy.disableBollignerVal()
            
        if enables[17]:
            strategy.setMomentumVal(values[17])
        else:
            strategy.disableMomentumVal()
            
        if enables[18]:
            strategy.setRocVal(values[18])
        else:
            strategy.disableRocVal()
            
        if enables[19]:
            strategy.setCciVal(values[19])
        else:
            strategy.disableCciVal()
            
        if enables[20]:
            strategy.setRsiVal(values[20])
        else:
            strategy.disableRsiVal()
            
        if enables[21]:
            strategy.setWilliamsVal(values[21])
        else:
            strategy.disableWilliamsVal()
            
        if enables[22]:
            strategy.setRisingBreakawayGapVal(values[22])
        else:
            strategy.disableRisingBreakawayGapVal()
            
        if enables[23]:
            strategy.setRisingContinuationGapVal(values[23])
        else:
            strategy.disableRisingContinuationGapVal()
            
        if enables[24]:
            strategy.setFallingExhaustionGapVal(values[24])
        else:
            strategy.disableFallingExhaustionGapVal()
            
        if enables[25]:
            strategy.setFallingBreakawayGapVal(values[25])
        else:
            strategy.disableFallingBreakawayGapVal()
            
        if enables[26]:
            strategy.setRisingExhaustionGapVal(values[26])
        else:
            strategy.disableRisingExhaustionGapVal()
            
        if enables[27]:
            strategy.setFallingContinuationGapVal(values[27])
        else:
            strategy.disableFallingContinuationGapVal()

        if enables[28]:
            strategy.setBull3Val(values[28])
        else:
            strategy.disableBull3Val()

        if enables[29]:
            strategy.setMornigStarVal(values[29])
        else:
            strategy.disableMornigStarVal()

        if enables[30]:
            strategy.setPiercingVal(values[30])
        else:
            strategy.disablePiercingVal()

        if enables[31]:
            strategy.setBear3Val(values[31])
        else:
            strategy.disableBear3Val()

        if enables[32]:
            strategy.setEveningStarVal(values[32])
        else:
            strategy.disableEveningStarVal()

        if enables[33]:
            strategy.setDarkCloudVal(values[33])
        else:
            strategy.disableDarkCloudVal()

        #ustawiamy
               
        self.formationDrawer = FormationDrawer(self.chart,strategy)
        #ustawiamy formation Drawer
        self.formationDrawer.setTrendColor(color[2])
        self.formationDrawer.setTrendLstyle(lineStyle[2])
        self.formationDrawer.setTrendLwidth(2.0)
        self.formationDrawer.setHeadAndShouldersColor(color[3])
        self.formationDrawer.setHeadAndShouldersLstyle(lineStyle[3])
        self.formationDrawer.setHeadAndShouldersLwidth(2.0)
        self.formationDrawer.setTripleTopColor(color[4])
        self.formationDrawer.setTripleTopLstyle(lineStyle[4])
        self.formationDrawer.setTripleTopLwidth(2.0)
        self.formationDrawer.setRisingWedgeColor(color[5])
        self.formationDrawer.setRisingWedgeLstyle(lineStyle[5])
        self.formationDrawer.setRisingWedgeLwidth(2.0)
        self.formationDrawer.setFallingTriangleColor(color[6])
        self.formationDrawer.setFallingTriangleLstyle(lineStyle[6])
        self.formationDrawer.setFallingTriangleLwidth(2.0)
        self.formationDrawer.setReversedHeadAndShouldersColor(color[7])
        self.formationDrawer.setReversedHeadAndShouldersLstyle(lineStyle[7])
        self.formationDrawer.setReversedHeadAndShouldersLwidth(2.0)
        self.formationDrawer.setTripleBottomColor(color[8])
        self.formationDrawer.setTripleBottomLstyle(lineStyle[8])
        self.formationDrawer.setTripleBottomLwidth(2.0)
        self.formationDrawer.setFallingWedgeColor(color[9])
        self.formationDrawer.setFallingWedgeLstyle(lineStyle[9])
        self.formationDrawer.setFallingWedgeLwidth(2.0)
        self.formationDrawer.setRisingTriangleColor(color[10])
        self.formationDrawer.setRisingTriangleLstyle(lineStyle[10])
        self.formationDrawer.setRisingTriangleLwidth(2.0)
        self.formationDrawer.setSymetricTriangleColor(color[11])
        self.formationDrawer.setSymetricTriangleLstyle(lineStyle[11])
        self.formationDrawer.setSymetricTriangleLwidth(2.0)
        #przerwa
        self.formationDrawer.setFlagPennantColor(color[13])
        self.formationDrawer.setFlagPennantLstyle(lineStyle[13])
        self.formationDrawer.setFlagPennantLwidth(2.0)
        #przerwa
        self.formationDrawer.setRisingBreakawayGapColor(color[22])
        self.formationDrawer.setRisingBreakawayGapLstyle(lineStyle[22])
        self.formationDrawer.setRisingBreakawayGapLwidth(2.0)
        self.formationDrawer.setRisingContinuationGapColor(color[23])
        self.formationDrawer.setRisingContinuationGapLstyle(lineStyle[23])
        self.formationDrawer.setRisingContinuationGapLwidth(2.0)
        self.formationDrawer.setFallingExhaustionGapColor(color[24])
        self.formationDrawer.setFallingExhaustionGapLstyle(lineStyle[24])
        self.formationDrawer.setFallingExhaustionGapLwidth(2.0)
        self.formationDrawer.setFallingBreakawayGapColor(color[25])
        self.formationDrawer.setFallingBreakawayGapLstyle(lineStyle[25])
        self.formationDrawer.setFallingBreakawayGapLwidth(2.0)
        self.formationDrawer.setRisingExhaustionGapColor(color[26])
        self.formationDrawer.setRisingExhaustionGapLstyle(lineStyle[26])
        self.formationDrawer.setRisingExhaustionGapLwidth(2.0)
        self.formationDrawer.setFallingContinuationGapColor(color[27])
        self.formationDrawer.setFallingContinuationGapLstyle(lineStyle[27])
        self.formationDrawer.setFallingContinuationGapLwidth(2.0)
        self.formationDrawer.setBull3Color(color[28])
        self.formationDrawer.setBull3Lstyle(lineStyle[28])
        self.formationDrawer.setBull3Lwidth(2.0)
        self.formationDrawer.setMornigStarColor(color[29])
        self.formationDrawer.setMornigStarLstyle(lineStyle[29])
        self.formationDrawer.setMornigStarLwidth(2.0)
        self.formationDrawer.setPiercingColor(color[30])
        self.formationDrawer.setPiercingLstyle(lineStyle[30])
        self.formationDrawer.setPiercingLwidth(2.0)
        self.formationDrawer.setBear3Color(color[31])
        self.formationDrawer.setBear3Lstyle(lineStyle[31])
        self.formationDrawer.setBear3Lwidth(2.0)
        self.formationDrawer.setEveningStarColor(color[32])
        self.formationDrawer.setEveningStarLstyle(lineStyle[32])
        self.formationDrawer.setEveningStarLwidth(2.0)
        self.formationDrawer.setDarkCloudColor(color[33])
        self.formationDrawer.setDarkCloudLstyle(lineStyle[33])
        self.formationDrawer.setDarkCloudLwidth(2.0)
        
        self.formationDrawer.setFormations(strategy)
        self.formationDrawer.drawFormations()
        
        
    
    def updateScale(self):
        if self.logRadioButton.isChecked():
            self.settings["scale"] = 'log'
        else:
            self.settings["scale"] = 'linear'
        
        if self.chart !=None:
            self.chart.setScaleType(self.settings["scale"])
            self.chart.repaint()
            self.chart.update()
            #self.chart.emit(QtCore.SIGNAL("movido"))
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
            
    def updateChartType(self):
        self.settings["ChartType"] = self.chartTypeComboBox.currentText()
        if self.chart !=None:
            self.chart.setMainType(self.settings["ChartType"])
            self.updateDrawTrend()
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
    def updateStep(self):
        self.settings["step"]= self.stepComboBox.currentText()
        if self.chart !=None:
            dateStart = self.startDateEdit.date()
            start = datetime.datetime(dateStart.year(),dateStart.month(),dateStart.day())
            dateEnd = self.endDateEdit.date()
            end = datetime.datetime(dateEnd.year(),dateEnd.month(),dateEnd.day())
            if isinstance( self.qModelIndex,list):
                for fin in self.finObj:
                    fin.updateArchive(self.settings['step'])
            else:
                self.finObj.updateArchive(self.settings["step"])
            self.chart.setData(self.finObj,start,end,self.settings["step"])
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
    def updateDate(self):
        print 'jestem w update date'
        dateStart = self.startDateEdit.date()
        self.settings["start"] = datetime.datetime(dateStart.year(),dateStart.month(),dateStart.day())
        dateEnd = self.endDateEdit.date()
        self.settings["end"] = datetime.datetime(dateEnd.year(),dateEnd.month(),dateEnd.day())
        if self.chart !=None:
            if isinstance( self.qModelIndex,list):
                for fin in self.finObj:
                    fin.updateArchive(self.settings['step'])
            else:
                self.finObj.updateArchive(self.settings["step"])
            self.chart.setData(self.finObj,self.settings["start"],self.settings["end"],self.settings["step"])
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
    def updateOscilator(self):
        self.settings["oscilator"] =" "
        for box in self.oscilatorCheckBoxList:
            if box.isChecked():
                self.settings["oscilator"] = str(box.text())
        if self.chart !=None:
            self.chart.setOscPlot(self.settings["oscilator"])
            self.chart.repaint()
            self.chart.update()
            #self.chart.emit(QtCore.SIGNAL("movido"))
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)

    def updateHideVolumen(self):
        hideVolumen =self.volumenCheckBox.isChecked()
        if self.chart !=None:
            if not self.chartsLayout.isEmpty():
                self.chartsLayout.removeWidget(self.chart)
            if hideVolumen:
                self.chart.rmVolumeBars()
            else:
                self.chart.addVolumeBars()

            self.chartsLayout.addWidget(self.chart)
            self.chart.repaint()
            self.chart.update()
            self.checkDrawTrend()
            #self.chart.emit(QtCore.SIGNAL("movido"))
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)

    def updateEnablePainting(self):
        painting =self.paintCheckBox.isChecked()
        if self.chart !=None:
            if not self.chartsLayout.isEmpty():
                self.chartsLayout.removeWidget(self.chart)
            self.chart.setDrawingMode(painting)
            self.chartsLayout.addWidget(self.chart)
            self.chart.repaint()
            self.chart.update()
            #self.chart.emit(QtCore.SIGNAL("movido"))
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
            
    def compareChanged(self,state):
        print 'xos tam'
        if state == 0:
            self.compareLineEdit.setEnabled(False)
            self.compareButton.setEnabled(False)
        if state == 2:
            self.compareLineEdit.setEnabled(True)
            self.compareButton.setEnabled(True)
            
    def smaChanged(self,state):
        if state == 0:
            self.settings['indicator'].remove('SMA')
        if state == 2:
            self.settings['indicator'].append('SMA')
        self.updateIndicator()
    def emaChanged(self,state):
        if state == 0:
            self.settings['indicator'].remove('EMA')
        if state == 2:
            self.settings['indicator'].append('EMA')
        self.updateIndicator()
    def wmaChanged(self,state):
        if state == 0:
            self.settings['indicator'].remove('WMA')
        if state == 2:
            self.settings['indicator'].append('WMA')
        self.updateIndicator()
    def bollingerChanged(self,state):
        if state == 0:
            self.settings['indicator'].remove('bollinger')
        if state == 2:
            self.settings['indicator'].append('bollinger')
        self.updateIndicator()
    def updateIndicator(self):
        if self.chart !=None:
            if self.settings['indicator']:
                self.chart.setMainIndicator(self.settings['indicator'][-1])
            else:
                self.chart.setMainIndicator("")
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
        font = QtGui.QFont()
        font.setBold(False)
        for box in self.indicatorCheckBoxList:
            box.setFont(font)
        font.setBold(True)
        #font.setWeight(75)
        if self.settings['indicator']:
            name = self.settings['indicator'][-1].lower()
            eval ('self.'+name+'CheckBox.setFont(font)')
            
    def updateDrawTrend(self):
        drawTrend =self.drawTrendCheckBox.isChecked()
        if self.chart !=None and drawTrend:
            self.chart.drawTrend()
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)
        else:
            self.chart.repaint()
            self.chart.update()
            m= self.parentWidget().parentWidget().parentWidget().parentWidget()
            m.resize(m.width() , m.height()-20)
            m.resize(m.width() , m.height()+20)

    def checkDrawTrend(self):
        drawTrend =self.drawTrendCheckBox.isChecked()
        if self.chart !=None and drawTrend:
            self.chart.drawTrend()


    def checkDate(self):
        if self.startDateEdit.date() >= self.endDateEdit.date():
            self.endDateEdit.setDate(self.startDateEdit.date())
    def addSymbolToCompareLine(self,a):
        if self.compareButton.isEnabled():
            self.compareLineEdit.setText(self.compareLineEdit.text() +a.data(QtCore.Qt.WhatsThisRole).toStringList()[0]+ ' vs ')

    def paint2Chart(self):
        index = int (self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[-1])

        if self.listName == "index":
            if dataParser.INDEX_LIST[index][2] == 'Yahoo':     
                self.finObj = dataParser.createWithArchivesFromYahoo(dataParser.INDEX_LIST[index][1],dataParser.INDEX_LIST[index][0],'index',dataParser.INDEX_LIST[index][3],self.settings["step"])
	    else:
                self.finObj = dataParser.createWithArchivesFromStooq(dataParser.INDEX_LIST[index][1],dataParser.INDEX_LIST[index][0],'index',dataParser.INDEX_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]

        if self.listName == "stock":
            if dataParser.STOCK_LIST[index][2] == 'Yahoo':
                self.finObj = dataParser.createWithArchivesFromYahoo(dataParser.STOCK_LIST[index][1],dataParser.STOCK_LIST[index][0],'stock',dataParser.STOCK_LIST[index][3],self.settings["step"])
	    else:
		self.finObj = dataParser.createWithArchivesFromStooq(dataParser.STOCK_LIST[index][1],dataParser.STOCK_LIST[index][0],'stock',dataParser.STOCK_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]
        
        if self.listName == "forex":
            self.finObj = dataParser.createWithArchivesFromStooq(dataParser.FOREX_LIST[index][1],dataParser.FOREX_LIST[index][0],'forex',dataParser.FOREX_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]

        if self.listName == "bond":
            if dataParser.BOND_LIST[index][2] == 'Yahoo':
                self.finObj = dataParser.createWithArchivesFromYahoo(dataParser.BOND_LIST[index][1],dataParser.BOND_LIST[index][0],'bond',dataParser.BOND_LIST[index][3],self.settings["step"])
	    else:
		self.finObj = dataParser.createWithArchivesFromStooq(dataParser.BOND_LIST[index][1],dataParser.BOND_LIST[index][0],'bond',dataParser.BOND_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]
        if self.listName == "resource":
            if dataParser.RESOURCE_LIST[index][2] == 'Yahoo':
                self.finObj = dataParser.createWithArchivesFromYahoo(dataParser.RESOURCE_LIST[index][1],dataParser.RESOURCE_LIST[index][0],'resource',dataParser.RESOURCE_LIST[index][3],self.settings["step"])
	    else:
		self.finObj = dataParser.createWithArchivesFromStooq(dataParser.RESOURCE_LIST[index][1],dataParser.RESOURCE_LIST[index][0],'resource',dataParser.RESOURCE_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]
            
        if self.listName == "futures":
            if dataParser.FUTURES_LIST[index][2] == 'Yahoo':
                self.finObj = dataParser.createWithArchivesFromYahoo(dataParser.FUTURES_LIST[index][1],dataParser.FUTURES_LIST[index][0],'futures',dataParser.FUTURES_LIST[index][3],self.settings["step"])
	    else:
		self.finObj = dataParser.createWithArchivesFromStooq(dataParser.FUTURES_LIST[index][1],dataParser.FUTURES_LIST[index][0],'resource',dataParser.FUTURES_LIST[index][3],self.settings["step"])
            self.currentChart = self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[0]

        self.chart = Chart(self, self.finObj)        
        self.cid = self.chart.mpl_connect('button_press_event', self.showChartsWithAllIndicators)
        self.chartsLayout.addWidget(self.chart)
        self.hasChart = True
    
        self.chart.setOscPlot(self.settings["oscilator"])
        self.chart.setDrawingMode(self.settings["painting"])
        if self.settings["indicator"]:
            self.chart.setMainIndicator(self.settings["indicator"][-1])
        self.chart.setData(self.finObj,self.settings["start"],self.settings["end"],self.settings["step"])                

        self.chart.setScaleType(self.settings["scale"])
        self.chart.setMainType(self.settings["chartType"])
        
        if self.settings['drawTrend']:
            lineWidth = self.settings['lineWidth']
            self.chart.drawTrend()
        
        if self.settings["hideVolumen"]:
            self.chart.rmVolumeBars()
        self.setOptions()

    def paintCompareChart(self):
        self.finObj = []
        print self.qModelIndex
        k = 0
        for x in self.listName:
            print self.qModelIndex[k]
            print x 
            if x == "index":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.INDEX_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.INDEX_LIST[index][1],dataParser.INDEX_LIST[index][0],'index',dataParser.INDEX_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.INDEX_LIST[index][1],dataParser.INDEX_LIST[index][0],'index',dataParser.INDEX_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
            if x == "stock":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.STOCK_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.STOCK_LIST[index][1],dataParser.STOCK_LIST[index][0],'stock',dataParser.STOCK_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.STOCK_LIST[index][1],dataParser.STOCK_LIST[index][0],'stock',dataParser.STOCK_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
            if x == "forex":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.FOREX_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.FOREX_LIST[index][1],dataParser.FOREX_LIST[index][0],'forex',dataParser.FOREX_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.FOREX_LIST[index][1],dataParser.FOREX_LIST[index][0],'forex',dataParser.FOREX_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
            if x == "bond":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.BOND_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.BOND_LIST[index][1],dataParser.BOND_LIST[index][0],'bond',dataParser.BOND_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.BOND_LIST[index][1],dataParser.BOND_LIST[index][0],'bond',dataParser.BOND_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
            if x == "resource":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.RESOURCE_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.RESOURCE_LIST[index][1],dataParser.RESOURCE_LIST[index][0],'resource',dataParser.RESOURCE_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.RESOURCE_LIST[index][1],dataParser.RESOURCE_LIST[index][0],'resource',dataParser.RESOURCE_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
                
            if x == "futures":
                index = int (self.qModelIndex[k].data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
                if dataParser.FUTURES_LIST[index][2] == 'Yahoo':
                    finObj = dataParser.createWithArchivesFromYahoo(dataParser.FUTURES_LIST[index][1],dataParser.FUTURES_LIST[index][0],'futures',dataParser.FUTURES_LIST[index][3],self.settings["step"])
                else:
                    finObj = dataParser.createWithArchivesFromStooq(dataParser.FUTURES_LIST[index][1],dataParser.FUTURES_LIST[index][0],'futures',dataParser.FUTURES_LIST[index][3],self.settings["step"])
                self.finObj.append(finObj)
            k=k+1
        
        self.chart = CompareChart(self)
        self.chart.setData(self.finObj,self.settings["start"],self.settings["end"],self.settings["step"])
        self.chartsLayout.addWidget(self.chart)

        #przywracamy opcje
        self.startDateEdit.setDate(QtCore.QDate(self.settings["start"].year,
                                   self.settings["start"].month,
                                   self.settings["start"].day))
        self.endDateEdit.setDate(QtCore.QDate(self.settings["end"].year,
                                 self.settings["end"].month,
                                 self.settings["end"].day))
        #step
        if self.settings["step"] == "daily":
            self.stepComboBox.setCurrentIndex(0)
        elif self.settings["step"] == "weekly":
            self.stepComboBox.setCurrentIndex(1)
        else:
            self.stepComboBox.setCurrentIndex(2)
        if self.settings["painting"]:
            self.paintCheckBox.setCheckState(2)


    def setOptions(self):
        #przywracamy odpowiednie ustawienia opcji w GUI
        #data
        self.startDateEdit.setDate(QtCore.QDate(self.settings["start"].year,
                                   self.settings["start"].month,
                                   self.settings["start"].day))
        self.endDateEdit.setDate(QtCore.QDate(self.settings["end"].year,
                                 self.settings["end"].month,
                                 self.settings["end"].day))
        if "SMA" in self.settings["indicator"]:
            self.smaCheckBox.setChecked(True)
            self.indicatorList.append('SMA')
        if 'WMA' in self.settings["indicator"]:
            self.wmaCheckBox.setChecked(True)
            self.indicatorList.append('WMA')
        if 'EMA' in self.settings["indicator"]:
            self.emaCheckBox.setChecked(True)
            self.indicatorList.append('EMA')
        if 'bollinger' in self.settings["indicator"]:
            self.bollingerCheckBox.setChecked(True)
            self.indicatorList.append('boolinger')

        font = QtGui.QFont()
        font.setBold(True)
        #font.setWeight(75)
        if self.settings["indicator"]:
            name = self.settings["indicator"][-1].lower()
            eval ('self.'+name+'CheckBox.setFont(font)')
            
        if self.settings["oscilator"] == "momentum":
            self.momentumCheckBox.setChecked(True)
        elif self.settings["oscilator"] == "CCI":
            self.cciCheckBox.setChecked(True)
        elif self.settings["oscilator"] == "ROC":
            self.rocCheckBox.setChecked(True)
        elif self.settings["oscilator"] == "RSI":
            self.rsiCheckBox.setChecked(True)
        elif self.settings["oscilator"] == "williams":
            self.williamsCheckBox.setChecked(True)
        #step
        if self.settings["step"] == "daily":
            self.stepComboBox.setCurrentIndex(0)
        elif self.settings["step"] == "weekly":
            self.stepComboBox.setCurrentIndex(1)
        else:
            self.stepComboBox.setCurrentIndex(2)
        #chartType
        if self.settings["chartType"] == "line":
            self.chartTypeComboBox.setCurrentIndex(0)
        elif self.settings["chartType"] == "point":
            self.chartTypeComboBox.setCurrentIndex(1)
        else:
            self.chartTypeComboBox.setCurrentIndex(2)
        #volumen
        if self.settings["hideVolumen"]:
            self.volumenCheckBox.setCheckState(2)
        #painting
        if self.settings["painting"]:
            self.paintCheckBox.setCheckState(2)

    def showChartsWithAllIndicators(self,x):
       
        if len(self.settings["indicator"]) >= 3:
            print 'opening popup'
            start = self.settings["start"]
            end = self.settings["end"]
            oscilator = self.settings["oscilator"]
            painting = self.settings["painting"]
            scale = self.settings['scale']
            chartType = self.settings["chartType"]
            step = self.settings["step"]
            hideVolumen = self.settings["hideVolumen"]
            
            self.chart.mpl_disconnect(self.cid)
            self.w = self.MyPopup(self)
            self.w.setGeometry(QtCore.QRect(100, 100, 1200, 900))
            k = 0
            for i in self.settings["indicator"]:
                chart2 = Chart(self, self.finObj)
                chart2.setData(self.finObj,start,end,step)
                chart2.setOscPlot(oscilator)
                chart2.setDrawingMode(painting)
                chart2.setMainIndicator(i)
                chart2.setScaleType(scale)
                chart2.setMainType(chartType)
                if hideVolumen:
                    chart2.rmVolumeBars()
                self.w.layout.addWidget(chart2,k/2,k%2,1,1)
                k+=1
                #self.cid = self.chart.mpl_connect('button_press_event', self.showChartsWithAllIndicators)
                self.w.show()
    def settingsTest(self):
        dateStart = self.startDateEdit.date()
        return dateStart
    def getSettings(self):
        #funkcja pobiera aktualnie zaznaczone opcje z tab
        dateStart = self.startDateEdit.date()  # początek daty
        start = datetime.datetime(dateStart.year(),dateStart.month(),dateStart.day())
        
        dateEnd = self.endDateEdit.date()     # koniec daty
        end = datetime.datetime(dateEnd.year(),dateEnd.month(),dateEnd.day())

        if not isinstance( self.qModelIndex,list):
            indicator = []
            if self.smaCheckBox.isChecked():
                indicator.append("SMA")
            if self.wmaCheckBox.isChecked():
                indicator.append("WMA")
            if self.emaCheckBox.isChecked():
                indicator.append("EMA")
            if self.bollingerCheckBox.isChecked():
                indicator.append("bollinger")
            oscilator = ''
            if self.momentumCheckBox.isChecked():
                oscilator = "momentum"
            elif self.cciCheckBox.isChecked():
                oscilator = "CCI"
            elif self.rocCheckBox.isChecked():
                oscilator = "ROC"
            elif self.rsiCheckBox.isChecked():
                oscilator = "RSI"
            elif self.williamsCheckBox.isChecked():
                oscilator = "williams"
            #draw trend
            drawTrend = self.drawTrendCheckBox.isChecked()
            #line width
            lineWidth = self.lineWidthSpinBox.value()
            index = int (self.qModelIndex.data(QtCore.Qt.WhatsThisRole).toStringList()[-1])
        else:
            index = []
            for model in self.qModelIndex:
                index.append( int (model.data(QtCore.Qt.WhatsThisRole).toStringList()[-1]))
        #step
        step = self.stepComboBox.currentText()
        #scale
        if self.logRadioButton.isChecked():
            scale = 'log'
        else:
            scale = 'linear'
        #chartType
        chartType = self.chartTypeComboBox.currentText()
        hideVolumen =self.volumenCheckBox.isChecked() 
        #painting
        painting = self.paintCheckBox.isChecked()
       

        if not isinstance( self.qModelIndex,list):
           t = {"finObjType":self.finObjType,"index":index,"start":start,"end":end,"indicator":indicator,"step":step,
                 "chartType":chartType,"hideVolumen":hideVolumen,
                 "painting":painting,"scale":scale,"oscilator":oscilator,
                 "drawTrend":drawTrend,'lineWidth':lineWidth}
        else:
            t = {"finObjType":self.finObjType,"index":index,"start":start,
                 "end":end,"step":step,
                 "chartType":chartType,"hideVolumen":hideVolumen,
                 "painting":painting,"scale":scale}
        return t

    
    class MyPopup(QtGui.QWidget):
        def __init__(self,parent):
            self.parent=parent
            QtGui.QWidget.__init__(self)
            self.initUI()
        def initUI(self):
            self.layout =  QtGui.QGridLayout(self)
        def closeEvent(self, event):
            self.parent.cid = self.parent.chart.mpl_connect('button_press_event', self.parent.showChartsWithAllIndicators)
