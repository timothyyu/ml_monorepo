#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from datetime import datetime, date
import yaml

from source.event.event import EventType
from source.event.backtest_event_engine import BacktestEventEngine
from source.data.backtest_data_feed_quandl import BacktestDataFeedQuandl
from source.data.backtest_data_feed_local_single_symbol import BacktestDataFeedLocalSingleSymbol
from source.data.backtest_data_feed_local_multiple_symbols import BacktestDataFeedLocalMultipleSymbols
from source.data.data_board import DataBoard
from source.brokerage.backtest_brokerage import BacktestBrokerage
from source.position.portfolio_manager import PortfolioManager
from source.performance.performance_manager import PerformanceManager
from source.risk.risk_manager import PassThroughRiskManager
from source.strategy.mystrategy import strategy_list

class BacktestEngine(object):
    """
    Event driven backtest engine
    """
    def __init__(self, config):
        """
        1. read in configs
        2. Set up backtest event engine
        """
        self._current_time = None

        ## 0. read in configs
        self._initial_cash = config['cash']
        self._symbols = config['symbols']
        self._benchmark = config['benchmark']
        #self.start_date = datetime.datetime.strptime(config['start_date'], "%Y-%m-%d")
        #self.end_date = datetime.datetime.strptime(config['end_date'], "%Y-%m-%d")
        start_date = config['start_date']
        send_date = config['end_date']
        params = config['params']
        strategy_name = config['strategy']
        datasource = str(config['datasource'])
        batch_tag = config['batch_tag']
        root_multiplier = config['root_multiplier']
        self._hist_dir = config['hist_dir']
        self._fvp_file = config['fvp_file']
        self._output_dir = config['output_dir']

        ## 1. data_feed
        symbols_all = self._symbols[:]   # copy
        if self._benchmark is not None:
            symbols_all.append(self._benchmark)
        self._symbols = [str(s) for s in self._symbols]
        symbols_all = set([str(s) for s in symbols_all])  # remove duplicates

        if (datasource.upper() == 'LOCAL'):
            print('Using local single symbol data feed')
            self._data_feed = BacktestDataFeedLocalSingleSymbol(
                hist_dir=self._hist_dir,
                start_date=start_date, end_date=send_date
            )
        elif (datasource.upper() == 'MULTI_LOCAL'):
            print('Using local multiple symbol data feed')
            self._data_feed = BacktestDataFeedLocalMultipleSymbols(
                hist_dir=self._hist_dir,
                start_date=start_date, end_date=send_date
            )
        else:
            print('Using Quandl data feed')
            self._data_feed = BacktestDataFeedQuandl(
                start_date=start_date, end_date=send_date
            )

        self._data_feed.subscribe_market_data(self._symbols)         # not symbols_all

        ## 2. event engine
        self._events_engine = BacktestEventEngine(self._data_feed)

        ## 3. brokerage
        self._data_board = DataBoard(hist_dir=self._hist_dir, syms=symbols_all)
        self._backtest_brokerage = BacktestBrokerage(
            self._events_engine, self._data_board
        )

        ## 4. portfolio_manager
        self._df_fvp = None
        if self._fvp_file is not None:
            self._df_fvp = pd.read_csv(self._hist_dir+self._fvp_file, index_col=0)

        self._portfolio_manager = PortfolioManager(self._initial_cash, self._df_fvp)

        ## 5. performance_manager
        self._performance_manager = PerformanceManager(self._symbols, self._benchmark, batch_tag, root_multiplier, self._df_fvp)

        ## 6. risk_manager
        self._risk_manager = PassThroughRiskManager()

        ## 7. load all strategies
        strategyClass = strategy_list.get(strategy_name, None)
        if not strategyClass:
            print(u'can not find strategy：%s' % strategy_name)
            return
        else:
            print(u'backtesting strategy：%s' % strategy_name)
        self._strategy = strategyClass(self._events_engine, self._data_board)
        self._strategy.set_symbols(self._symbols)
        self._strategy.set_capital(self._initial_cash)
        self._strategy.on_init(params)
        self._strategy.on_start()

        ## 8. trade recorder
        #self._trade_recorder = ExampleTradeRecorder(output_dir)

        ## 9. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        self._events_engine.register_handler(EventType.BAR, self._bar_event_handler)
        self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    # ------------------------------------ private functions -----------------------------#
    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        # performance update goes before position updates because it updates previous day performance
        self._performance_manager.update_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._portfolio_manager.mark_to_market(self._current_time, tick_event.full_symbol, tick_event.price, self._data_board)
        self._data_board.on_tick(tick_event)
        self._strategy.on_tick(tick_event)

    def _bar_event_handler(self, bar_event):
        self._current_time = bar_event.bar_end_time()

        # performance update goes before position updates because it updates previous day
        self._performance_manager.update_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._portfolio_manager.mark_to_market(self._current_time, bar_event.full_symbol, bar_event.adj_close_price, self._data_board)
        self._data_board.on_bar(bar_event)
        self._strategy.on_bar(bar_event)

    def _order_event_handler(self, order_event):
        self._backtest_brokerage.place_order(order_event)

    def _fill_event_handler(self, fill_event):
        self._portfolio_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)

    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def run(self, tear_sheet=True):
        """
        Run backtest
        """
        self._events_engine.run()
        self._performance_manager.update_final_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._performance_manager.save_results(self._output_dir)

        return self._performance_manager.caculate_performance(tear_sheet)

    # ------------------------------- end of public functions -----------------------------#

if __name__ == '__main__':
    config = None
    try:
        path = os.path.abspath(os.path.dirname(__file__))
        # config_file = os.path.join(path, 'config_backtest_buy_hold.yaml')
        # config_file = os.path.join(path, 'config_backtest_moving_average_cross.yaml')
        # config_file = os.path.join(path, 'config_backtest_simple_linear_scaling.yaml')
        # config_file = os.path.join(path, 'config_backtest_mean_reversion_spread.yaml')
        config_file = os.path.join(path, 'config_backtest_kalman_filter_pairs_trading.yaml')
        with open(os.path.expanduser(config_file)) as fd:
            config = yaml.load(fd)
    except IOError:
        print("config.yaml is missing")

    backtest_engine = BacktestEngine(config)
    results, results_dd, monthly_ret_table, ann_ret_df = backtest_engine.run()
    if results is None:
        print('Empty Strategy')
    else:
        print(results)
        print(results_dd)
        print(monthly_ret_table)
        print(ann_ret_df)