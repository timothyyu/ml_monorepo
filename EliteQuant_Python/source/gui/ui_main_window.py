#!/usr/bin/env python
# -*- coding: utf-8 -*-
# http://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt
import sys
import os
import webbrowser
import psutil
from queue import Queue, Empty
from PyQt5 import QtCore, QtWidgets, QtGui
from datetime import datetime

from source.event.event import EventType
from source.order.order_flag import OrderFlag
from .ui_market_window import MarketWindow
from .ui_order_window import OrderWindow
from .ui_fill_window import FillWindow
from .ui_position_window import PositionWindow
from .ui_account_window import AccountWindow
from .ui_strategy_window import StrategyWindow
from .ui_log_window import LogWindow
from source.strategy.mystrategy import strategy_list
from source.data.data_board import DataBoard
from source.order.order_manager import OrderManager
from source.strategy.strategy_manager import StrategyManager
from source.position.portfolio_manager import PortfolioManager
from source.risk.risk_manager import PassThroughRiskManager
from source.account.account_manager import AccountManager
from source.event.live_event_engine import LiveEventEngine
from source.event.client_mq import ClientMq
from ..order.order_event import OrderEvent
from ..order.order_type import OrderType

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config_server, config_client, lang_dict):
        super(MainWindow, self).__init__()

        ## member variables
        self._current_time = None
        self._config_server = config_server
        self._config_client = config_client
        self._symbols =  config_server[config_server['accounts'][0]]['tickers']
        self._lang_dict = lang_dict
        self._font = lang_dict['font']
        self._widget_dict = {}
        self.central_widget = None
        self.market_window = None
        self.message_window = None
        self.order_window = None
        self.fill_window = None
        self.position_window = None
        self.account_window = None
        self.strategy_window = None

        #  0. order_manager; some of ui_windows uses order_manager
        self._order_manager = OrderManager()

        ## 1. event engine
        self._outgoing_queue = Queue()                    # outgoing queue from client side
        self._ui_events_engine = LiveEventEngine()        # update ui
        self._outgoing_request_events_engine = LiveEventEngine()          # events/actions request from client
        self._schedule_timer = QtCore.QTimer()                  # task scheduler; TODO produce result_packet

        # 3. data board
        self._data_board = DataBoard()

        # 5. risk manager and compliance manager
        self.risk_manager = PassThroughRiskManager()

        # 6. account manager
        self.account_manager = AccountManager(self._config_server)

        # 7 portfolio manager and position manager
        self.portfolio_manager = PortfolioManager(self._config_client['initial_cash'])

        ## 4. strategy_manager
        self._strategy_manager = StrategyManager(self._config_client, self._outgoing_request_events_engine,self._order_manager,self.portfolio_manager, self._data_board)
        self._strategy_manager.load_strategy()

        ## 8. client mq
        self._client_mq = ClientMq(self._ui_events_engine, self._outgoing_queue)

        # 1. set up gui windows
        self.setGeometry(50, 50, 600, 400)
        self.setWindowTitle(lang_dict['Prog_Name'])
        self.setWindowIcon(QtGui.QIcon("gui/image/logo.ico"))
        self.init_menu()
        self.init_status_bar()
        self.init_central_area()

        ## 9. wire up event handlers
        self._ui_events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        self._ui_events_engine.register_handler(EventType.ORDERSTATUS, self.order_window.order_status_signal.emit)
        self._ui_events_engine.register_handler(EventType.FILL, self._fill_event_handler)
        self._ui_events_engine.register_handler(EventType.POSITION, self._position_event_handler)
        self._ui_events_engine.register_handler(EventType.ACCOUNT, self.account_window.account_signal.emit)
        self._ui_events_engine.register_handler(EventType.CONTRACT, self._contract_event_handler)
        self._ui_events_engine.register_handler(EventType.HISTORICAL, self._historical_event_handler)
        self._ui_events_engine.register_handler(EventType.GENERAL, self.log_window.msg_signal.emit)

        self._outgoing_request_events_engine.register_handler(EventType.ORDER, self._outgoing_order_request_handler)
        self._outgoing_request_events_engine.register_handler(EventType.ACCOUNT, self._outgoing_account_request_handler)
        self._outgoing_request_events_engine.register_handler(EventType.POSITION, self._outgoing_position_request_handler)
        self._outgoing_request_events_engine.register_handler(EventType.GENERAL, self._outgoing_general_msg_request_handler)

        ## 10. start
        self._ui_events_engine.start()
        self._outgoing_request_events_engine.start()
        self._client_mq.start()

    #################################################################################################
    # -------------------------------- Event Handler   --------------------------------------------#
    #################################################################################################
    def update_status_bar(self, message):
        self.statusBar().showMessage(message)

    def open_proj_folder(self):
        webbrowser.open('d:/workspace/elitequant_python/')

    def place_order(self):
        s = str(self.sym.text())
        n = self.direction.currentIndex()
        f = self.order_flag.currentIndex()
        p = str(self.order_price.text())
        q = str(self.order_quantity.text())
        t = self.order_type.currentIndex()

        # to be checked by risk manger
        try:
            o = OrderEvent()
            o.full_symbol = s
            o.order_size = int(q) if (n == 0) else -1 * int(q)
            o.order_flag = OrderFlag(f)
            o.create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

            if (t == 0):
                o.order_type = OrderType.MARKET
                self._outgoing_request_events_engine.put(o)
            elif (t == 1):
                o.order_type = OrderType.LIMIT
                o.limit_price = float(p)
                self._outgoing_request_events_engine.put(o)
            else:
                pass
        except:
            print('place order error')

    def start_strategy(self):
        self.strategy_window.update_status(self.strategy_window.currentRow(), True)

    def pause_strategy(self):
        pass

    def stop_strategy(self):
        self.strategy_window.update_status(self.strategy_window.currentRow(), False)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        print('closing main window')
        self._ui_events_engine.stop()
        self._outgoing_request_events_engine.stop()
        self._client_mq.stop()

    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        self._data_board.on_tick(tick_event)       # update databoard
        self._order_manager.on_tick(tick_event)     # check standing stop orders
        self._strategy_manager.on_tick(tick_event)  # feed strategies
        self.market_window.tick_signal.emit(tick_event)         # display

    def _order_status_event_handler(self, order_status_event):  # including cancel
        # this is moved to ui_thread for consistency
        pass

    def _fill_event_handler(self, fill_event):
        # update portfolio manager for pnl
        self._order_manager.on_fill(fill_event)  # update order manager with fill
        self._strategy_manager.on_fill(fill_event)  # feed fill to strategy
        self.fill_window.fill_signal.emit(fill_event)     # display
        self.order_window.update_order_status(fill_event.client_order_id,
                                              self._order_manager.retrieve_order(fill_event.client_order_id).order_status)

    def _position_event_handler(self, position_event):
        self.portfolio_manager.on_position(position_event)       # position received
        self.position_window.position_signal.emit(position_event)     # display

    def _account_event_handler(self, account_event):
        pass

    def _contract_event_handler(self, contract_event):
        self.portfolio_manager.on_contract(contract_event)

    def _historical_event_handler(self, historical_event):
        print(historical_event)

    def _general_event_handler(self, general_event):
        pass

    def _outgoing_order_request_handler(self, o):
        """
         process o, check against risk manager and compliance manager
        """
        self.risk_manager.order_in_compliance(o)  # order pointer; modify order directly
        self._order_manager.on_order(o)

        msg = o.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_account_request_handler(self, a):
        msg = a.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_position_request_handler(self, p):
        msg = p.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_general_msg_request_handler(self, g):
        self.log_window.update_table(g)           # append to log window
    #################################################################################################
    # ------------------------------ Event Handler Ends --------------------------------------------#
    #################################################################################################

    #################################################################################################
    # -------------------------------- User Interface  --------------------------------------------#
    #################################################################################################
    def set_font(self, font):
        self._font = font

    def init_menu(self):
        menubar = self.menuBar()

        sysMenu = menubar.addMenu(self._lang_dict['File'])
        # open folder
        sys_folderAction = QtWidgets.QAction(self._lang_dict['Folder'], self)
        sys_folderAction.setStatusTip(self._lang_dict['Open_Folder'])
        sys_folderAction.triggered.connect(self.open_proj_folder)
        sysMenu.addAction(sys_folderAction)

        sysMenu.addSeparator()

        # sys|exit
        sys_exitAction = QtWidgets.QAction(self._lang_dict['Exit'], self)
        sys_exitAction.setShortcut('Ctrl+Q')
        sys_exitAction.setStatusTip(self._lang_dict['Exit_App'])
        sys_exitAction.triggered.connect(self.close)
        sysMenu.addAction(sys_exitAction)

    def init_status_bar(self):
        self.statusthread = StatusThread()
        self.statusthread.status_update.connect(self.update_status_bar)
        self.statusthread.start()

    def init_central_area(self):
        self.central_widget = QtWidgets.QWidget()

        hbox = QtWidgets.QHBoxLayout()

        #-------------------------------- Top Left ------------------------------------------#
        topleft = MarketWindow(self._symbols, self._lang_dict)
        self.market_window = topleft

        # -------------------------------- Top right ------------------------------------------#
        topright = QtWidgets.QFrame()
        topright.setFrameShape(QtWidgets.QFrame.StyledPanel)
        topright.setFont(self._font)
        place_order_layout = QtWidgets.QFormLayout()
        self.sym = QtWidgets.QLineEdit()
        self.sym_name = QtWidgets.QLineEdit()
        self.sec_type = QtWidgets.QComboBox()
        self.sec_type.addItems([self._lang_dict['Stock'], self._lang_dict['Future'], self._lang_dict['Option'], self._lang_dict['Forex']])
        self.direction = QtWidgets.QComboBox()
        self.direction.addItems([self._lang_dict['Long'], self._lang_dict['Short']])
        self.order_flag = QtWidgets.QComboBox()
        self.order_flag.addItems([self._lang_dict['Open'], self._lang_dict['Close'], self._lang_dict['Close_Yesterday'], self._lang_dict['Close_Today']])
        self.order_price = QtWidgets.QLineEdit()
        self.order_quantity = QtWidgets.QLineEdit()
        self.order_type = QtWidgets.QComboBox()
        self.order_type.addItems([self._lang_dict['MKT'], self._lang_dict['LMT'], self._lang_dict['FAK'], self._lang_dict['FOK']])
        self.exchange = QtWidgets.QComboBox()
        self.exchange.addItems(['CFFEX','SHFE', 'DCE', 'HKFE','GLOBEX','SMART'])
        self.account = QtWidgets.QComboBox()
        self.account.addItems(['FROM', 'CONFIG'])
        self.btn_order = QtWidgets.QPushButton(self._lang_dict['Place_Order'])
        self.btn_order.clicked.connect(self.place_order)

        place_order_layout.addRow(QtWidgets.QLabel(self._lang_dict['Discretionary']))
        place_order_layout.addRow(self._lang_dict['Symbol'], self.sym)
        place_order_layout.addRow(self._lang_dict['Name'], self.sym_name)
        place_order_layout.addRow(self._lang_dict['Security_Type'], self.sec_type)
        place_order_layout.addRow(self._lang_dict['Direction'], self.direction)
        place_order_layout.addRow(self._lang_dict['Order_Flag'], self.order_flag)
        place_order_layout.addRow(self._lang_dict['Price'], self.order_price)
        place_order_layout.addRow(self._lang_dict['Quantity'], self.order_quantity)
        place_order_layout.addRow(self._lang_dict['Order_Type'], self.order_type)
        place_order_layout.addRow(self._lang_dict['Exchange'], self.exchange)
        place_order_layout.addRow(self._lang_dict['Account'], self.account)
        place_order_layout.addRow(self.btn_order)
        topright.setLayout(place_order_layout)

        # -------------------------------- bottom Left ------------------------------------------#
        bottomleft = QtWidgets.QTabWidget()
        bottomleft.setFont(self._font)
        tab1 = QtWidgets.QWidget()
        tab2 = QtWidgets.QWidget()
        tab3 = QtWidgets.QWidget()
        tab4 = QtWidgets.QWidget()
        tab5 = QtWidgets.QWidget()
        bottomleft.addTab(tab1, self._lang_dict['Log'])
        bottomleft.addTab(tab2, self._lang_dict['Order'])
        bottomleft.addTab(tab3, self._lang_dict['Fill'])
        bottomleft.addTab(tab4, self._lang_dict['Position'])
        bottomleft.addTab(tab5, self._lang_dict['Account'])

        self.log_window = LogWindow(self._lang_dict)
        tab1_layout = QtWidgets.QVBoxLayout()
        tab1_layout.addWidget(self.log_window)
        tab1.setLayout(tab1_layout)

        self.order_window = OrderWindow(self._order_manager,self._outgoing_queue, self._lang_dict)       # cancel_order outgoing nessage
        tab2_layout = QtWidgets.QVBoxLayout()
        tab2_layout.addWidget(self.order_window)
        tab2.setLayout(tab2_layout)

        self.fill_window =FillWindow(self._order_manager, self._lang_dict)
        tab3_layout = QtWidgets.QVBoxLayout()
        tab3_layout.addWidget(self.fill_window)
        tab3.setLayout(tab3_layout)

        self.position_window = PositionWindow(self._lang_dict)
        tab4_layout = QtWidgets.QVBoxLayout()
        tab4_layout.addWidget(self.position_window)
        tab4.setLayout(tab4_layout)

        self.account_window = AccountWindow(self.account_manager, self._lang_dict)
        tab5_layout = QtWidgets.QVBoxLayout()
        tab5_layout.addWidget(self.account_window)
        tab5.setLayout(tab5_layout)

        # -------------------------------- bottom right ------------------------------------------#
        bottomright = QtWidgets.QFrame()
        bottomright.setFrameShape(QtWidgets.QFrame.StyledPanel)
        bottomright.setFont(self._font)
        strategy_manager_layout = QtWidgets.QFormLayout()
        self.strategy_window = StrategyWindow(self._lang_dict, self._strategy_manager)
        self.btn_strat_start = QtWidgets.QPushButton(self._lang_dict['Start_Strat'])
        self.btn_strat_start.clicked.connect(self.start_strategy)
        self.btn_strat_pause = QtWidgets.QPushButton(self._lang_dict['Pause_Strat'])
        self.btn_strat_pause.clicked.connect(self.pause_strategy)
        self.btn_strat_stop = QtWidgets.QPushButton(self._lang_dict['Stop_Strat'])
        self.btn_strat_stop.clicked.connect(self.stop_strategy)
        self.btn_strat_liquidate = QtWidgets.QPushButton(self._lang_dict['Liquidate_Strat'])
        btn_strat_layout = QtWidgets.QHBoxLayout()
        btn_strat_layout.addWidget(self.btn_strat_start)
        btn_strat_layout.addWidget(self.btn_strat_pause)
        btn_strat_layout.addWidget(self.btn_strat_stop)
        btn_strat_layout.addWidget(self.btn_strat_liquidate)

        strategy_manager_layout.addRow(QtWidgets.QLabel(self._lang_dict['Automatic']))
        strategy_manager_layout.addRow(self.strategy_window)
        strategy_manager_layout.addRow(btn_strat_layout)
        bottomright.setLayout(strategy_manager_layout)

        # --------------------------------------------------------------------------------------#
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter1.addWidget(topleft)
        splitter1.addWidget(topright)
        splitter1.setSizes([400,100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter2.addWidget(bottomleft)
        splitter2.addWidget(bottomright)
        splitter2.setSizes([400, 100])

        splitter3 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter3.addWidget(splitter1)
        splitter3.addWidget(splitter2)
        splitter3.setSizes([400, 100])

        hbox.addWidget(splitter3)
        self.central_widget.setLayout(hbox)
        self.setCentralWidget(self.central_widget)

    #################################################################################################
    # ------------------------------ User Interface End --------------------------------------------#
    #################################################################################################

class StatusThread(QtCore.QThread):
    status_update = QtCore.pyqtSignal(str)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        while True:
            cpuPercent = psutil.cpu_percent()
            memoryPercent = psutil.virtual_memory().percent
            self.status_update.emit('CPU Usage: ' + str(cpuPercent) + '% Memory Usage: ' + str(memoryPercent) + '%')
            self.sleep(1)