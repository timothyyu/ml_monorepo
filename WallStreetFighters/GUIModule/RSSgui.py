# -*- coding: utf-8 -*-
import sys
import os

from PyQt4 import QtGui ,QtCore
from RSS import *


class RSSSite:
    """An RSS Site"""
    def __init__(self, Url=""):
        self.rssReader = RSSReader(Url)
        self.Name = self.rssReader.name
class RSSWidget(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
       
        self.initUi()
        self.rssSite = []
        os.chdir("../../WallStreetFighters/GUIModule")
        self.rssFile = open('rss.txt','r+b')
        for line in  self.rssFile: 
            rssReader = RSSSite(line)
            self.rssSite.append(rssReader)
        self.descriptionList = []
        self.showRSS()   
    def initUi(self):
        self.gridLayout = QtGui.QGridLayout(self)

        #przyciski
        self.groupBox = QtGui.QGroupBox("Select site:",self)
        self.groupBox.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setKerning(True)
        self.groupBox.setFont(font)
        self.horizontalLayout = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setMargin(2)
        self.addButton = QtGui.QPushButton("add",self.groupBox)
        self.horizontalLayout.addWidget(self.addButton)
        self.removeButton = QtGui.QPushButton("remove",self.groupBox)
        self.horizontalLayout.addWidget(self.removeButton)
        self.editButton= QtGui.QPushButton("edit",self.groupBox)
        self.horizontalLayout.addWidget(self.editButton)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        #wyswietlanie rss
        self.gridLayout.setHorizontalSpacing(6)
        self.gridLayout.setVerticalSpacing(0)

        self.rssList = QtGui.QListWidget(self)
        self.rssList.setMaximumSize(QtCore.QSize(450, 200))
        self.gridLayout.addWidget(self.rssList, 3, 0, 1, 3)
        

        # wyswietlanie artykułów
        self.itemsLabel = QtGui.QLabel("Select Article:",self)
        self.gridLayout.addWidget(self.itemsLabel, 5, 0, 1, 1)
        
        self.itemsList = QtGui.QListWidget(self)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.itemsList.sizePolicy().hasHeightForWidth())
        self.itemsList.setSizePolicy(sizePolicy)
        self.itemsList.setWordWrap(True)
        #setWrapping (self, bool enable)
        self.itemsList.setMaximumSize(QtCore.QSize(450, 16777215))
        self.itemsList.setMinimumSize(QtCore.QSize(440, 0))

        self.gridLayout.addWidget(self.itemsList, 6, 0, 1, 3)

        # text browser
        self.textBrowser = QtGui.QTextBrowser(self)
        self.textBrowser.setOpenExternalLinks(True)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textBrowser.sizePolicy().hasHeightForWidth())
        #self.textBrowser.setSizePolicy(sizePolicy)
        self.gridLayout.addWidget(self.textBrowser, 0, 3, 7, 1)

        
        #QtCore.QObject.connect(self.urlView,QtCore.SIGNAL("itemClicked(QListWidgetItem*)"),self.showItems)
        self.itemsList.itemClicked.connect(self.showDescription)
        self.rssList.itemClicked.connect(self.showItems)
        self.addButton.clicked.connect(self.addRSS)
        self.removeButton.clicked.connect(self.removeRSS)
    def addRSS(self):
        text, ok = QtGui.QInputDialog.getText(self, 'Add RSS', 
            'Enter url:')
        
        if ok:
            self.rssFile.write((str(text))+'\n')
            rssReader = RSSSite(str(text))
            self.rssSite.append(rssReader)
            item = QtGui.QListWidgetItem(rssReader.Name,self.rssList)
            
            self.rssList.addItem(item)
    def removeRSS(self):
        index = self.rssList.currentRow()
        self.rssSite = map(lambda i: self.rssSite[i],filter(lambda i: i != index,range(len(self.rssSite))))
        item = self.rssList.takeItem(self.rssList.currentRow())
        item = None
        self.rssFile.seek(0)
        rssList = self.rssFile.readlines()
        del rssList[index]
        self.rssFile.close()
        self.rssFile = open('rss.txt','w+b')
        self.rssFile.writelines(rssList)
        self.rssFile.close()
        self.rssFile = open('rss.txt','r+b')
        
        
    def showRSS(self):
            for site in self.rssSite:
                if(site):
                    item = QtGui.QListWidgetItem(site.Name,self.rssList)
                    self.rssList.addItem(item)

        
    def showItems(self):
        self.itemsList.clear()
        index = self.rssList.currentRow()
        self.descriptionList = []
	for rssItem in self.rssSite[index].rssReader.GetItems():
	    if (rssItem):
                desc = ""
                desc = desc+rssItem.description
                #desc += "\n\n_______________________\n Article: \n"
                #desc += "<link href=\""
                #desc += rssItem.link
                #desc += "\" />"
                self.descriptionList.append(desc)
		item = QtGui.QListWidgetItem(rssItem.title,self.itemsList)
		self.itemsList.addItem(item)
		
		
    def showDescription(self):
       index = self.itemsList.currentRow()
       item = self.descriptionList[index]
       try:
           self.textBrowser.setText(item)
           #self.textBrowser.insertHtml(item)
       except IOError:
            pass
       except:
            pass
       
    
				

