import json
import matplotlib.pyplot as plt
import numpy as np
import time
import sys


from Models import Models
from ExperienceReplay import ExperienceReplay
from Trading import Trading
import DataStore as ds

from keras.models import model_from_json


if __name__ == "__main__":
    # Make sure this grid size matches the value used fro training

    batch_size = 25 # 50
    sequence_length = 250 # 500

    features_list = list(range(1,33))  ## FULL
    features_list = list(range(1,6))  ## SHORT!!

    training_days = 1
    testing_days = 1
    max_memory = 500000




    training_store = ds.DataStore(training_days=training_days, features_list=features_list, sequence_length=sequence_length)
    testing_store = ds.DataStore(training_days=training_days, testing_days=testing_days, features_list=features_list, sequence_length=sequence_length, mean=training_store.mean, std=training_store.std)

    features_length = training_store.get_features_length()

    env = Trading(data_store=testing_store, sequence_length=sequence_length, features_length=features_length)
    num_actions = env.get_action_count() # [sell, buy, flat] # get From TRADING!!

    mo = Models()
  
    start_time = time.time()
    best_pnl = -99999. 
    exp_replay = ExperienceReplay(max_memory=max_memory, env=env, sequence_dim=(sequence_length, features_length))

    if len(sys.argv) == 2:
        model_name = sys.argv[1]
    else:
        model_name = None


    if model_name is not None:
        model = mo.load_model(model_name)
        model.compile(optimizer='rmsprop', loss='mse')
    else:
        print ("usage python analyze_net.py model_name (e.g.atari_rl_training)")
        raise "Value Error"

    input_t = env.reset()
    total_reward = 0

    win_cnt = 0
    loss_cnt = 0
    loss = 0.

    for e in range(testing_days):
        game_over = False

        # get initial input

        while not game_over:

            input_tm1 = input_t

            # get next action
            q = model.predict(exp_replay.resize_input(input_tm1))
            action = np.argmax(q[0])

            # apply action, get rewards and new state
            input_t, reward, game_over, idays, lineindex = env.act(action) 

            if reward > 0:
                win_cnt += 1

            if reward < 0:
                loss_cnt += 1

            total_reward += reward

        print("Epoch {:05d}/{} | Time {:.1f} | Loss {:.4f} | Win trades {:5d} | Loss trades {:5d} | Total PnL {:.2f} | Eps {:.4f} ".format(e, testing_days, time.time()-start_time, 0, win_cnt, loss_cnt, total_reward, 0.))

