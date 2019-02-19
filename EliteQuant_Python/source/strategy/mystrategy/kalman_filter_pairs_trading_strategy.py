#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pykalman import KalmanFilter

from ..strategy_base import StrategyBase
from ...order.order_event import OrderEvent
from ...order.order_type import OrderType


class KalmanFilterPairsTradingStrategy(StrategyBase):
    """
	MeanReversionSpreadStrategy
    """

    def __init__(
            self, events_engine, data_board
    ):
        super(KalmanFilterPairsTradingStrategy, self).__init__(events_engine, data_board)
        self.symbols = ['EWA US Equity', 'EWC US Equity']
        self.bollinger_scaler = 1.0
        self.state_cov_multiplier = np.power(0.01, 2)  # 0.1: spread_std=2.2, cov=16  ==> 0.01: 0.22, 0.16
        self.observation_cov = 0.001

        self.current_ewa_size = 0
        self.current_ewc_size = 0
        self._kf = None                # Kalman Filter
        self._current_state_means = None
        self._current_state_covs = None

    def on_bar(self, bar_event):
        print(bar_event.bar_start_time)
        A = self._data_board.get_hist_price(self.symbols[0], bar_event.bar_start_time)
        B = self._data_board.get_hist_price(self.symbols[1], bar_event.bar_start_time)

        x = A['Price'].iloc[-1]
        y = B['Price'].iloc[-1]
        observation_matrix_stepwise = np.array([[x, 1]])
        observation_stepwise = y
        spread = None
        spread_std = None

        if self._kf is None:
            self._kf = KalmanFilter(n_dim_obs=1, n_dim_state=2,
                              initial_state_mean=np.ones(2),  # initial value
                              initial_state_covariance=np.ones((2, 2)),  # initial value
                              transition_matrices=np.eye(2),  # constant
                              observation_matrices=observation_matrix_stepwise,  # depend on x
                              observation_covariance=self.observation_cov,  # constant
                              transition_covariance=np.eye(2) * self.state_cov_multiplier)  # constant
            P = np.ones((2, 2)) + np.eye(2)*self.state_cov_multiplier
            spread = y - observation_matrix_stepwise.dot(np.ones(2))[0]
            spread_std = np.sqrt(observation_matrix_stepwise.dot(P).dot(observation_matrix_stepwise.transpose())[0][0] + self.observation_cov)
            state_means_stepwise, state_covs_stepwise = self._kf.filter(observation_stepwise)  # depend on y
            self._current_state_means = state_means_stepwise[0]
            self._current_state_covs = state_covs_stepwise[0]
        else:
            state_means_stepwise, state_covs_stepwise = self._kf.filter_update(
                self._current_state_means, self._current_state_covs,
                observation=observation_stepwise,
                observation_matrix=observation_matrix_stepwise)
            P = self._current_state_covs + np.eye(2)*self.state_cov_multiplier                        # This has to be small enough
            spread = y - observation_matrix_stepwise.dot(self._current_state_means)[0]
            spread_std = np.sqrt(observation_matrix_stepwise.dot(P).dot(observation_matrix_stepwise.transpose())[0][0] + self.observation_cov)
            self._current_state_means = state_means_stepwise
            self._current_state_covs = state_covs_stepwise

        # residual is assumed to be N(0, spread_std)
        bollinger_ub = self.bollinger_scaler * spread_std
        bollinger_lb = - self.bollinger_scaler * spread_std
        coeff = self._current_state_means[0]
        print(spread, spread_std)

        if (spread > bollinger_ub) and (self.current_ewa_size >= 0):
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

        elif (spread < bollinger_lb) and (self.current_ewa_size <= 0):
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

        elif (spread < 0) and (spread > bollinger_lb) and (self.current_ewa_size < 0):
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

        elif (spread > 0) and (spread < bollinger_ub) and (self.current_ewa_size > 0):
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