#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ..strategy_base import StrategyBase
from ...order.order_event import OrderEvent
from ...order.order_type import OrderType
from ...order.order_flag import OrderFlag


class OrderPerIntervalStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """
    def __init__(self, events_engine, data_board):
        super(OrderPerIntervalStrategy, self).__init__(events_engine, data_board)
        self.ticks = 0
        self.tick_trigger_threshold = 10
        self.sign = 1

    def on_tick(self, k):
        symbol = self.symbols[0]
        if k.full_symbol == symbol:
            print(k)
            if (self.ticks > self.tick_trigger_threshold):
                o = OrderEvent()
                o.full_symbol = symbol
                o.order_type = OrderType.MARKET
                o.order_flag = OrderFlag.OPEN
                o.order_size = 100 * self.sign
                print('place order')
                self.place_order(o)

                self.ticks = 0
                self.sign = self.sign * (-1)
            else:
                self.ticks += 1