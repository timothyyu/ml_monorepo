#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from ..strategy_base import StrategyBase
from ...order.order_event import OrderEvent
from ...order.order_type import OrderType


class MeanReversionSpreadStrategy(StrategyBase):
    """
	MeanReversionSpreadStrategy
    """

    def __init__(
            self, events_engine, data_board
    ):
        super(MeanReversionSpreadStrategy, self).__init__(events_engine, data_board)
        self.lookback_window = 250
        self.symbols = ['EWA US Equity', 'EWC US Equity']
        self.bollinger_scaler = 1.0
        self.current_ewa_size = 0
        self.current_ewc_size = 0
        self._lm_model = LinearRegression(copy_X=True, fit_intercept=True, normalize=False)

    def on_bar(self, bar_event):
        print(bar_event.bar_start_time)
        A = self._data_board.get_hist_price(self.symbols[0], bar_event.bar_start_time)
        B = self._data_board.get_hist_price(self.symbols[1], bar_event.bar_start_time)

        # linear regrssion
        AB = pd.merge(A[['Price']], B[['Price']], left_index=True, right_index=True, how='inner')

        if AB.shape[0] < self.lookback_window:
            return

        self._lm_model.fit(AB.iloc[-self.lookback_window:, 0].values.reshape(-1, 1), AB.iloc[-self.lookback_window:, 1].values.reshape(-1, 1))   # B ~ A
        coeff = self._lm_model.coef_                        # B ~ coeff * A
        #print(coeff[0][0])
        spread = self._lm_model.predict(AB.iloc[-self.lookback_window:, 0].values.reshape(-1, 1)) - AB.iloc[-self.lookback_window:, 1].values.reshape(-1, 1)   # coeff*A - B
        spread = spread.reshape(-1,)
        rolling_avg = np.average(spread)
        rolling_sd = np.std(spread)
        bollinger_ub = rolling_avg + self.bollinger_scaler * rolling_sd
        bollinger_lb = rolling_avg - self.bollinger_scaler * rolling_sd

        if (spread[-1] > bollinger_ub) and (self.current_ewa_size >= 0):
            print ('Hit upper band, short spread.')
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = int(-1000*coeff) - self.current_ewa_size
            self.place_order(o)
            self.current_ewa_size = int(-1000*coeff)

            o = OrderEvent()
            o.full_symbol = self.symbols[1]
            o.order_type = OrderType.MARKET
            o.order_size = 1000 - self.current_ewc_size
            self.place_order(o)
            self.current_ewc_size = 1000

        elif (spread[-1] < bollinger_lb) and (self.current_ewa_size <= 0):
            print('Hit lower band, long spread.')
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = int(1000 * coeff) - self.current_ewa_size
            self.place_order(o)
            self.current_ewa_size = int(1000 * coeff)

            o = OrderEvent()
            o.full_symbol = self.symbols[1]
            o.order_type = OrderType.MARKET
            o.order_size = -1000 - self.current_ewc_size
            self.place_order(o)
            self.current_ewc_size = -1000

        elif (spread[-1] < 0) and (spread[-1] > bollinger_lb) and (self.current_ewa_size < 0):
            print('spread crosses below average.cover short spread')
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size =  - self.current_ewa_size
            self.place_order(o)
            self.current_ewa_size = 0

            o = OrderEvent()
            o.full_symbol = self.symbols[1]
            o.order_type = OrderType.MARKET
            o.order_size =  - self.current_ewc_size
            self.place_order(o)
            self.current_ewc_size = 0

        elif (spread[-1] > 0) and (spread[-1] < bollinger_ub) and (self.current_ewa_size > 0):
            print('spread crosses above average.cover long spread')
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size =  - self.current_ewa_size
            self.place_order(o)
            self.current_ewa_size = 0

            o = OrderEvent()
            o.full_symbol = self.symbols[1]
            o.order_type = OrderType.MARKET
            o.order_size =  - self.current_ewc_size
            self.place_order(o)
            self.current_ewc_size = 0