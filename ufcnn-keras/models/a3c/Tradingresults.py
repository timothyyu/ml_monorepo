# -*- coding: utf-8 -*-
import tensorflow as tf
import numpy as np
import random

from a3c_util import choose_action
from game_state import GameState
from game_ac_network import GameACFFNetwork, GameACLSTMNetwork, GameACDilatedNetwork

from constants import ACTION_SIZE
from constants import PARALLEL_SIZE
from constants import CHECKPOINT_DIR
from constants import USE_GPU
from constants import NETWORK_TYPE

from constants import TESTING_DAYS

# use CPU for display tool
device = "/cpu:0"

if NETWORK_TYPE == 'LSTM':
    global_network = GameACLSTMNetwork(ACTION_SIZE, -1, device)
elif NETWORK_TYPE == 'DILATED':
    global_network = GameACDilatedNetwork(ACTION_SIZE, device)
elif NETWORK_TYPE == 'CONV':
    global_network = GameACFFNetwork(ACTION_SIZE, device)
else:
    raise SystemExit('NETWORK_TYPE must be LSTM, CONV or DILATED.')

sess = tf.Session()
init = tf.initialize_all_variables()
sess.run(init)

saver = tf.train.Saver()
checkpoint = tf.train.get_checkpoint_state(CHECKPOINT_DIR)
if checkpoint and checkpoint.model_checkpoint_path:
  saver.restore(sess, checkpoint.model_checkpoint_path)
  print ("checkpoint loaded:", checkpoint.model_checkpoint_path)
else:
  print ("Could not find old checkpoint")

game_state = GameState(0, display=True, no_op_max=0, testing=True, show_trades=True)

testing_days = TESTING_DAYS
total_pnl = 0

for i in range(testing_days):
    print("Working on day ",i)
    terminal = False
    daily_pnl = 0

    #new
    if i > 0:
        game_state.environment.reset() 

    while not terminal:
        pi_values = global_network.run_policy(sess, game_state.s_t)

        action = choose_action(pi_values, use_argmax=True)
        game_state.process(action)

        reward = game_state.reward
        terminal = game_state.terminal

        game_state.update()

    game_state.environment.create_plot(game_state.environment.iday)
    daily_pnl = sum(t.pnl() for t in game_state.environment.trades)
    total_pnl += daily_pnl
    game_state.environment.daily_pnl = 0

    print("Day", i, ",Realized PnL:", daily_pnl)

print("Total Realized PnL:", total_pnl)


for i in range(testing_days):
    print("Potting day", i)
    

