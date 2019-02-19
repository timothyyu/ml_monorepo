#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ..strategy_base import StrategyBase
from ...order.order_event import OrderEvent
from ...order.order_type import OrderType


class BuyAndHoldStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """
    def __init__(self, events_engine, data_board):
        super(BuyAndHoldStrategy, self).__init__(events_engine, data_board)
        self.invested = False

    def on_bar(self, event):
        print(event.bar_start_time)
        symbol = self.symbols[0]
        if event.full_symbol == symbol:
            if not self.invested:
                o = OrderEvent()
                o.full_symbol = symbol
                o.order_type = OrderType.MARKET
                o.order_size = int(self.capital/event.close_price)
                self.place_order(o)
                self.invested = True