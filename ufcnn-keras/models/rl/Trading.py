
import json
import numpy as np
import random

import DataStore

from ExperienceReplay import ExperienceReplay


class Trading(object):

    def __init__(self, data_store=None, sequence_length=500, features_length=32 ):
     

        self.data_store = data_store
        self.training_days = data_store.get_number_days()
        self.sequence_length = sequence_length

        self.position_store = {}
        self.initrate_store = {}
        self.features_length = features_length
        # Will be broadcasted to the other Modules. Change if changing actions below...
        self.action_count = 3
        self.trading_fee = 0.2


    def reset(self):
        """
        start a new game 
        and return the first input....
        """
        # get a new day...
        self.iday = np.random.randint(0, self.training_days)
        
        self.day_length = self.data_store.get_day_length(self.iday)

        self.current_index = self.sequence_length 
        self.position = 0.
        self.initrate = 0.
        #print ("IDAY:" , self.iday)
        self.current_rate_bid=0
        self.current_rate_ask=0
      
        # and create the position store if necessary
        if self.iday not in self.position_store.keys():
            self.position_store[self.iday] = np.zeros(self.day_length)
            self.initrate_store[self.iday] = np.zeros(self.day_length)

        # feed current position and initial rate to the net...
        self.current_position_store = self.position_store[self.iday] 
        self.current_initrate_store = self.initrate_store[self.iday] 
   
        return self.observe(self.iday, self.current_index)

    def _update_state(self, action, game_over):
        """ 
        Actions can be 
             STAY/GO_SHORT = 0 
             STAY/GO_LONG = 1
             STAY/GO_FLAT = 2
 
        game over is the end of a day...

        We need to track in the EnvReplay and Trading

              0...last position
              1...initial rate
              2...Index in Dataframe
   
              On Demand: 3..36 states, row[2+2]=BID, row[4+2]=ASK. Do we need the last 500 ticks...
              
        """
        self.last_rate_bid = self.current_rate_bid
        self.last_rate_ask = self.current_rate_ask
        self.last_position_rate = 0

        self.current_rate_bid_norm, self.current_rate_bid,  self.current_rate_ask_norm, self.current_rate_ask = self.data_store.get_bid_ask(self.iday, self.current_index)

        #print("DATA for Rates ",self.iday, self.current_index)
        #print("INIT Rates:",self.current_rate_bid, self.current_rate_ask)

        # store old versions before loading new ones...
        self.last_position = self.position
        self.last_initrate = self.initrate

        if game_over:
            action = 2 # GO_FLAT at End

        self.trade_is_over = False 
        self.new_trade = False

        # and execute the trading action...
        if action == 0: # STAY/GO_SHORT
           if self.position > -0.1:
                self.initrate = self.current_rate_bid # SELL at the BID
                initrate_norm = self.current_rate_bid_norm # SELL at the BID
                self.position = -1. # only 1 contract 
                self.new_trade = True

        if action == 1: # STAY/GO_LONG 
            if self.position < 0.1:
                self.initrate = self.current_rate_ask # BUY at the ASK
                initrate_norm = self.current_rate_ask_norm # 
                self.position = 1. # only 1 contract 
                self.new_trade = True

        if action == 2: # STAY/GO_FLAT
            if abs(self.position) > 0.1:
                self.position = 0. 

        if self.position != self.last_position:
            self.trade_is_over = True
   
        if self.new_trade:
            self.current_initrate_store[self.current_index] = initrate_norm
        else:
            self.current_initrate_store[self.current_index] = 0. 

        self.current_position_store[self.current_index] = self.position 

    def _get_reward(self):
        """
        only when closing the position
        reward is the return of the position
      

        when old Position = 0 and new position = 0
            -> reward = 0
 
        when an old position was open at the beginning of the tick:
            reward + = rate - last rate * position

        when an new position was opened in the tick:
	    reward -= abs(position) * tradingfee
            reward -= position * Delta bid-ask  

         
        """
        reward = 0.
        delayed_reward = True
        if delayed_reward:
            # The old trade only pnl calculation
            if self.last_position != 0. and self.last_position != self.position:
                reward = self._value_position_at_close(self.last_position, self.last_initrate, self.current_rate_bid, self.current_rate_ask)
        else:
            if self.last_position != 0:
                reward += self._value_position(self.last_position, self.last_rate_bid, self.last_rate_ask, self.current_rate_bid, self.current_rate_ask)

            if self.last_position != self.position and self.position != 0:
                reward -= abs(self.position) * self.trading_fee
                reward += self._value_position(self.position, self.initrate, self.initrate, self.current_rate_bid, self.current_rate_ask)

        print("VALUATION ", self.last_position, self.last_initrate, self.current_rate_bid, self.current_rate_ask)

        print("Reward",reward)
        return reward

    def _value_position(self, position, last_rate_bid, last_rate_ask, current_rate_bid, current_rate_ask):
        value = 0.

        # LONG: CURRENT_BID - INITIAL_ASK
        if position > 0.1:
            value = position * (current_rate_bid - last_rate_bid)

        # SHORT: CURRENT_ASK - INITIAL_BID
        if position < -0.1:
            value = position * (current_rate_ask - last_rate_ask) 

        print("value: ",value, "pos: ", position, "last bid: ", last_rate_bid, "last ask: ", last_rate_ask, "curr bid: ", current_rate_bid, "curr ask: ", current_rate_ask)

        return value

    def _value_position_at_close(self, closed_position, initrate, current_rate_bid, current_rate_ask):
        """
        Row 2 is BID U2
        Row 4 is ASK U4
        """
        value = 0.

        # LONG: CURRENT_BID - INITIAL_ASK
        if closed_position > 0.1:
            value = closed_position * (current_rate_bid - initrate)

        # SHORT: CURRENT_ASK - INITIAL_BID
        if closed_position < -0.1:
            value = closed_position * (current_rate_ask - initrate) 

        value -= abs(closed_position) * self.trading_fee
        return value


    def observe(self, iday_, current_index_):
        """ 
        deliver next input for the net... 
        input: iday and current_index,
        output an array as input for the net...
        """
        input = self.data_store.get_sequence(iday_, current_index_)
 
        ## NOT USED - causing problems?? TODO
        ##for i in range(self.sequence_length):
        ##    input[i][self.features_length-2] = self.initrate_store[iday_][current_index_-self.sequence_length+i+1]
        ##    input[i][self.features_length-1] = self.position_store[iday_][current_index_-self.sequence_length+i+1]

        return input


    def act(self, action):
        """
        this does all the action
        """

        # points to the element currently treated
        self.current_index += 1
        sequence = self.data_store.get_sequence(self.iday,self.current_index)
 
        if self.current_index == self.day_length - 1:
            game_over = True
        else:
            game_over = False

        self._update_state(action, game_over)
        reward = self._get_reward()
        #game_over = self.game_ovegame_over # when the trade is executed??? # or at the end of the trading day..
        return self.observe(self.iday, self.current_index), reward, game_over, self.iday, self.current_index

    def _draw_state(self):
        """
        draws the canvas for the game, not needed...
        """
        pass

    def get_action_count(self):
        return self.action_count



