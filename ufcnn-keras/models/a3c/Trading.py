
import json
import numpy as np
np.set_printoptions(threshold=np.inf)
import random

from constants import TRADING_FEE
from constants import SHOW_TRADES

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

class Trade:
    '''
    Encapsulate a trade
    Statistics can be calculated from a list of trades
    '''

    def __init__(self, position, entry_index, entry_bid_price, entry_ask_price):
        assert position is not None and position != 0
        self.position = position
        self.entry_index = entry_index
        self.exit_index = None
        self.entry_price = entry_ask_price if position > 0 else entry_bid_price
        self.exit_price = None
        self.entry_spread = entry_ask_price - entry_bid_price
        self.fee = TRADING_FEE

    def close(self, exit_index, exit_bid_price, exit_ask_price):
        self.exit_index = exit_index
        self.exit_price = exit_bid_price if self.position > 0 else exit_ask_price

    def is_long(self):
        return self.position > 0

    def is_short(self):
        return self.position < 0

    def pnl(self):
        if self.entry_price is None or self.exit_price is None:
            return None
        else:
            return self.position * (self.exit_price - self.entry_price) - abs(self.position)*self.fee


class Trading:

    def __init__(self, data_store=None, sequence_length=500, features_length=32, testing=False, show_trades=None):
     
        self.data_store = data_store
        self.training_days = data_store.get_number_days()
        self.sequence_length = sequence_length
        self.features_length = features_length
        self.testing = testing
        self.iday = -1 # for testing

        self.show_trades = SHOW_TRADES if show_trades is None else show_trades

        #print("TRADING: Testing is" ,self.testing)
        #for i in range (self.data_store.get_number_days()):
        #    print("Day ",i,", len: ", self.data_store.get_day_length(i))

    def reset(self):

        # randomize days
        if not self.testing: 
            self.iday = np.random.randint(0, self.training_days)
        else:
            self.iday += 1 # iterate over all idays
            if self.iday >= self.data_store.get_number_days():
                self.iday = 0

        self.day_length = self.data_store.get_day_length(self.iday)
        self.current_index = self.sequence_length
        print("IDAY:" , self.iday, self.current_index)

        # Current trade and daily trade history (see Trade class)
        self.trade = None
        self.trades = []
   
        _, self.current_rate_bid, _, self.current_rate_ask = self.data_store.get_bid_ask(self.iday, self.current_index)

    def create_plot(self, testday):
        self.iday = testday
        self.day_length = self.data_store.get_day_length(self.iday)

        # plot of the rates
        bid = np.zeros(self.day_length)
   
        for i in range(self.day_length):
            rate_bid_norm, rate_bid, rate_ask_norm, rate_ask = self.data_store.get_bid_ask(self.iday, i)
            bid[i] = rate_bid
            #print("I",i,", Bid: ",rate_bid, " norm", rate_bid_norm, rate_ask_norm, rate_ask )

        fig = plt.figure()
        plt.plot(bid, lw=1)
        plt.xlabel('ticks')
        plt.ylabel('Bid')
        plt.title('Bid Rate for day '+str(testday) + " : " + str(self.data_store.get_day(self.iday)))
        plt.savefig("Rate_"+str(testday)+".png")
        plt.close(fig)

        plot_x = []
        plot_y = []
        total_pnl = 0.

        # and create a plot of the trades
        for tr in self.trades:
            plot_x.append(tr.entry_index)
            total_pnl += tr.pnl()
            plot_y.append(total_pnl)

        #print(plot_x)
        #print(plot_y)

        fig = plt.figure()
        plt.plot(plot_x, plot_y, '.')

        plt.xlabel('ticks')
        plt.ylabel('Realized PnL')
        plt.title('Realized PnL for day '+str(testday) + " : " + str(self.data_store.get_day(self.iday)))
        plt.savefig("PnL_"+str(testday)+".png")
        plt.close(fig)

    def position(self):
        return 0 if self.trade is None else self.trade.position

    def get_reward(self, action):
        """ #reward, terminal, self._screen = get_reward(action)
        This is the version without sliding
        added a term in get_reward that adds winning trades twice to the reward - 
           once each tick it lasts (here winning and losing trades are treated equally), 
           and when closing a winning trade, the winning amount is credited again. 
           So reward != pnl. See daily_pnl instead.
        """
        debug = False   # enables some prints
     
        #store the last rates...
        last_rate_bid = self.current_rate_bid
        last_rate_ask = self.current_rate_ask

        terminal = False
        opened_trade = None
        closed_trade = None

        #print("day length ", self.day_length, self.iday,  self.current_index )

        if self.current_index >= self.day_length - 2:
            # Close our position at the end of the day
            if self.trade is not None:
                self.trade.close(self.current_index, self.current_rate_bid, self.current_rate_ask)
                closed_trade = self.trade
                self.trade = None
            terminal = True
        else:
            if action == 0: # STAY/GO_SHORT
                if self.position() >= 0:
                    if debug:
                        print("Going SHORT: ", self.current_index, self.current_rate_bid)

                    if self.position() > 0:
                        self.trade.close(self.current_index, self.current_rate_bid, self.current_rate_ask)
                        closed_trade = self.trade

                    self.trade = Trade(-1, self.current_index, self.current_rate_bid, self.current_rate_ask)
                    opened_trade = self.trade

            elif action == 1: # STAY/GO_LONG
                if self.position() <= 0:
                    if debug:
                        print("Going LONG:  ", self.current_index, self.current_rate_ask)

                    if self.position() < 0:
                        self.trade.close(self.current_index, self.current_rate_bid, self.current_rate_ask)
                        closed_trade = self.trade

                    self.trade = Trade(+1, self.current_index, self.current_rate_bid, self.current_rate_ask)
                    opened_trade = self.trade

            elif action == 2: # STAY/GO_FLAT
                if self.position() != 0:
                    if debug:
                        print("Going FLAT: ",index, self.current_rate_bid)

                    self.trade.close(self.current_index, self.current_rate_bid, self.current_rate_ask)
                    closed_trade = self.trade
                    self.trade = None

        # Close trade, append to history
        if closed_trade is not None:
            tr = closed_trade
            self.trades.append(tr)
            if self.show_trades:
                print("CLOSE: {:6} {:+2} entry {:9.5f} exit {:9.5f} = {:+8.5f}".format(tr.exit_index, tr.position, 
                    tr.entry_price, tr.exit_price, tr.pnl()))

        # New trade is opened
        if opened_trade is not None:
            tr = opened_trade
            if self.show_trades:
                print("OPEN:  {:6} {:+2} entry {:9.5f}".format(tr.entry_index, tr.position, tr.entry_price))

        # move to the next time step...
        self.current_index += 1

        # and get the rates...
        _, self.current_rate_bid, _, self.current_rate_ask = self.data_store.get_bid_ask(self.iday, self.current_index)

        # Calculate value and update reward from the current position
        # Use closing prices of position (BID for LONG, ASK for SHORT)
        # Note: The bid/ask spread is currently eliminated as a cost factor.
        #       This avoids "policy saturation" (aka PLOCK, see emails), but needs to be used again later.
        value = 0.
        if self.position() > 0:
            value = self.position() * (self.current_rate_bid - last_rate_bid)
        elif self.position() < 0:
            value = self.position() * (self.current_rate_ask - last_rate_ask)

        # Apply components of reward
        # TODO test reward clipping?
        reward = value
        if opened_trade is not None:
            pass
            #reward += opened_trade.entry_spread                        # credit back the bid/ask spread so opening cost is zero
            #reward -= abs(opened_trade.position) * opened_trade.fee    # apply fee
        if closed_trade is not None:
            reward -= abs(closed_trade.position) * closed_trade.fee     # apply fee
            #if closed_trade.pnl() > 0.:
            #    reward += closed_trade.pnl()                            # profits count twice :-)

        if debug:
            print('{} {:+2} {}/{} V {} R {}'.format(self.current_index, self.position(),
                self.current_rate_bid, self.current_rate_ask, value, reward))

        inputs = self.data_store.get_sequence(self.iday, self.current_index).copy()
        # TODO: Why do we set input[0,0] to self.position?
        inputs[0,0] = self.position()
        screen = np.resize(inputs, (self.sequence_length,1,self.features_length))

        if terminal:
            print ("Daily: iday/index/pnl/wins/losses/short/long/", self.iday, self.current_index,
                sum(t.pnl() for t in self.trades),
                sum(t.pnl() for t in self.trades if t.pnl() > 0),
                sum(t.pnl() for t in self.trades if t.pnl() <= 0),
                len([t for t in self.trades if t.is_short()]),
                len([t for t in self.trades if t.is_long()]) )

        return reward, terminal, screen

