#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
from ..data.tick_event import TickEvent, TickType

class MarketWindow(QtWidgets.QTableWidget):
    tick_signal = QtCore.pyqtSignal(type(TickEvent()))

    def __init__(self, symbols, lang_dict, parent=None):
        super(MarketWindow, self).__init__(parent)

        self._symbols = symbols
        self._lang_dict = lang_dict
        self.setFont(lang_dict['font'])
        self.header = [lang_dict['Symbol'],
                       lang_dict['Name'],
                       lang_dict['Last_Price'],
                       lang_dict['Volume'],
                       lang_dict['Open_Interest'],
                       lang_dict['Bid_Size'],
                       lang_dict['Bid'],
                       lang_dict['Ask'],
                       lang_dict['Ask_Size'],
                       lang_dict['Yesterday_Close'],
                       lang_dict['Open_Price'],
                       lang_dict['High_Price'],
                       lang_dict['Low_Price'],
                       lang_dict['Time'],
                       lang_dict['Source']]

        self.init_table()
        self.tick_signal.connect(self.update_table)

    def init_table(self):
        row = len(self._symbols)
        self.setRowCount(row)
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

        for i in range(row):
            self.setItem(i, 0, QtWidgets.QTableWidgetItem(self._symbols[i]))
            for j in range(1,col):
                self.setItem(i, j, QtWidgets.QTableWidgetItem(0.0))

    def update_table(self,tickevent):
        if tickevent.full_symbol in self._symbols:
            row = self._symbols.index(tickevent.full_symbol)
            if (tickevent.price > 0.0):
                self.item(row, 13).setText(tickevent.timestamp)
                if (tickevent.tick_type == TickType.BID):
                    self.item(row, 5).setText(str(tickevent.size))
                    self.item(row, 6).setText(str(tickevent.price))
                elif (tickevent.tick_type == TickType.ASK):
                    self.item(row, 7).setText(str(tickevent.price))
                    self.item(row, 8).setText(str(tickevent.size))
                elif (tickevent.tick_type == TickType.TRADE):
                    self.item(row, 2).setText(str(tickevent.price))
                    self.item(row, 3).setText(str(tickevent.size))
                elif (tickevent.tick_type == TickType.FULL):
                    self.item(row, 2).setText(str(tickevent.price))
                    self.item(row, 3).setText(str(tickevent.size))
                    self.item(row, 4).setText(str(tickevent.open_interest))
                    self.item(row, 5).setText(str(tickevent.bid_size_L1))
                    self.item(row, 6).setText(str(tickevent.bid_price_L1))
                    self.item(row, 7).setText(str(tickevent.ask_price_L1))
                    self.item(row, 8).setText(str(tickevent.ask_size_L1))
                    self.item(row, 9).setText(str(tickevent.pre_close))
                    self.item(row, 10).setText(str(tickevent.open))
                    self.item(row, 11).setText(str(tickevent.high))
                    self.item(row, 12).setText(str(tickevent.low))

