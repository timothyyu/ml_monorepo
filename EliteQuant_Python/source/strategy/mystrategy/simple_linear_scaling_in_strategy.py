#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import deque
import numpy as np

from ..strategy_base import StrategyBase
from ...order.order_event import OrderEvent
from ...order.order_type import OrderType


class SimpleLinearScalingInStrategy(StrategyBase):
    """
	SimpleLinearScalingInStrategy
    """

    def __init__(
            self, events_engine, data_board
    ):
        super(SimpleLinearScalingInStrategy, self).__init__(events_engine, data_board)
        self.lookback_window = 250
        self.symbols = ['USDCAD Curncy']
        self._current_size = 0  # negative means short

    def on_bar(self, bar_event):
        # retrieve price history up to now
        hist_data_to_date = self._data_board.get_hist_price(self.symbols[0], bar_event.bar_end_time())

        if hist_data_to_date.shape[0] < self.lookback_window:
            return

        rolling_avg = np.average(hist_data_to_date.iloc[-self.lookback_window:]['Price'])
        rolling_sd = np.std(hist_data_to_date.iloc[-self.lookback_window:]['Price'])
        rolling_z_score = (hist_data_to_date.iloc[-1] - rolling_avg) / rolling_sd
        rolling_z_score = rolling_z_score.values[0]
        # size is negatively proportional to z-score
        target_size = -1 * int(rolling_z_score * 10000)  # integer lots only
        lots_to_trade = target_size - self._current_size

        if lots_to_trade != 0:
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = lots_to_trade
            print('{} traded {} on z-score {}'.format(bar_event.bar_end_time(), lots_to_trade, rolling_z_score))
            self.place_order(o)

        self._current_size = target_size