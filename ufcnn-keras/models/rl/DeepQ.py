
import json
import numpy as np
import time

import DataStore as ds

from Models import Models
from ExperienceReplay import ExperienceReplay
from Trading import Trading

from keras.optimizers import SGD, RMSprop, Adagrad



class DeepQ(object):
    """
    create the trading state from the batchsize by extracting the last 500 frames from the DataStream plus the state from the environment replay...
    What needs to be done

      OK0) Add the real bid & ask unmodified to the state array. 
        set the mean = 0 and the std = 1 for the columns that should not be changed...

      OK1) Make sure that the trading stops at the end of day. How? Must be in the state. force an action "go flat" at the EOD
         get_count returns the length for this day..
         for range(training_days)
            day_len=get_length(day)
            for range (seq_len, day_len)
               if i == day_len-1 -> EOD -> force action go flat..., set EOD = true. das gar nicht ausprobieren...
            statt game_over auch trade_over ... -> um den Reward richtig zu berechnen...
      OK3) Loop through the days and the states

      2) STATE: 
        State: Position, initrate, game_over, action, 
        Array to store:  
	a) 32 Features
        b) Position
        c) initial rate fractional / real 
        add b) and c) to the net
        set the initial rates...
        envionment get_batch so umbauen, dass es daten liefert
      4) Send the right data to the nets. Add position and init rate to the net in this process... 
      5) Model in eigenes Modul
      6) RL in Eigenes Modul, für threading
      7) Epsillon skalieren...
      
    """
    def execute(self):  
        # parameters
        epsilon = .5  # exploration
        epsilon_decay = 0.95
        epsilon_min = 0.1

        epoch = 4000 # is number of cycles...
        max_memory = 2000 #  NEEDS TO BE AS BIG AS AT LEAST 1 TRADING DAY!!!
    
        batch_size = 50 # 50
        sequence_length = 250 # 500
        discount = 0.95

        training_days = 1
        testing_days = 1

        features_list = list(range(1,33))  ## FULL
        features_list = list(range(1,6))  ## SHORT!!

        training_store = ds.DataStore(training_days=training_days, features_list=features_list, sequence_length=sequence_length)
        features_length = training_store.get_features_length()
        env = Trading(data_store=training_store, sequence_length=sequence_length, features_length=features_length)

        num_actions = env.get_action_count() # [sell, buy, flat] # get From TRADING!!

        #testing_store = ds.DataStore(training_days=training_days, testing_days=10, features_list=features_list, sequence_length=sequence_length)

        mo = Models()
        rms = RMSprop(lr=0.0001, rho=0.9, epsilon=1e-06)

        use_ufcnn=True
        if use_ufcnn:
            model =  mo.model_ufcnn_concat(sequence_length=sequence_length,
                       features=features_length,
                       nb_filter=15,
                       filter_length=5,
                       output_dim=num_actions,
                       optimizer=rms,
                       loss='mse',
                       batch_size = batch_size,
                       init="normal")
            base_model_name = "ufcnn"
        else:
            model = mo.atari_conv_model(output_dim=num_actions, features=features_length, loss='mse', sequence_length=sequence_length, optimizer=rms, batch_size=batch_size, init="normal")
            base_model_name = "atari"

        testing_store = ds.DataStore(training_days=training_days, testing_days=testing_days, features_list=features_list, sequence_length=sequence_length, 
                                     mean=training_store.mean, std=training_store.std)

        test_env = Trading(data_store=testing_store, sequence_length=sequence_length, features_length=features_length)


        #model = mo.atari_conv_model(regression=False, output_dim=num_actions, features=features_length, nb_filter=50,
        #                           loss='mse', sequence_length=sequence_length, optimizer=rms, batch_size=batch_size)

        # If you want to continue training from a previous model, just uncomment the line bellow
        #mo.load_model("ufcnn_rl_training")

        # Define environment/game

        # Initialize experience replay object

        start_time = time.time()
        best_pnl = -99999. 
        best_rndless_pnl = -99999.

        exp_replay = ExperienceReplay(max_memory=max_memory, env=env, sequence_dim=(sequence_length, features_length), discount=discount)
        lineindex = 0

        # Train
        for e in range(epoch):
            loss = 0.
            game_over = False

            total_reward = 0

            win_cnt = 0
            loss_cnt = 0
            random_cnt = 0
            no_random_cnt = 0

            ### loop over days-...
            for i in range(training_days):
                input_t = env.reset()

                j = 0
                while not game_over: # game_over ... end of trading day...
                    input_tm1 = input_t
                    #print("INPUT ",input_tm1)
                    # get next action
                    if np.random.rand() <= epsilon:
                        action = np.random.randint(0, num_actions, size=1)[0]
                        random_cnt += 1
                        #print("RANDOM")
                    else:
                        q = model.predict(exp_replay.resize_input(input_tm1))
                        action = np.argmax(q[0])
                        no_random_cnt += 1
                        #print("SELECT")
                        ##action = np.argmax(q)

                    # apply action, get rewards and new state
                    input_t, reward, game_over, idays, lineindex = env.act(action) 

                    if reward > 0:
                        win_cnt += 1

                    if reward < 0:
                        loss_cnt += 1

                    total_reward += reward
                    if reward > 1.:
                        reward = 1.

                    if reward < -1.:
                        reward = -1.

                    # store experience
                    exp_replay.remember([action, reward, idays, lineindex-1], game_over)

                    # adapt model

                    if j  > batch_size :  # do not run exp_rep if the store is empty...
                        inputs, targets = exp_replay.get_batch(model, batch_size=batch_size)
                        curr_loss = model.train_on_batch(exp_replay.resize_input(inputs), targets)
                        loss += curr_loss

                    j += 1

            rndless_pnl = self.get_randomless_pnl(test_env=test_env, model=model, testing_days=testing_days)

            secs = time.time() - start_time
            print("Epoch {:05d}/{} | Time {:7.1f} | Loss {:11.4f} | Win trades {:5d} | Loss trades {:5d} | Total PnL {:8.2f} | Rndless PnL {:8.2f} | Eps {:.4f} | Rnd: {:5d}| No Rnd: {:5d}  ".format(e, epoch, secs, loss, win_cnt, loss_cnt, total_reward, rndless_pnl, epsilon, random_cnt, no_random_cnt), flush=True)
            if epsilon > epsilon_min:
                epsilon *= epsilon_decay 
            # Save trained model weights and architecture, this will be used by the visualization code
            
            if total_reward > best_pnl: 
                mo.save_model(model,base_model_name + "_rl_best")
                best_pnl = total_reward
            else:
                mo.save_model(model,base_model_name + "_rl_training")

            if rndless_pnl > best_pnl: 
                mo.save_model(model,base_model_name + "_rl_rndless_best")
                best_rndless_pnl = rndless_pnl

        # End of run
    
    

    def get_randomless_pnl(self, test_env=None, model=None, testing_days=None):
        """ get the PNL with the current model without being epsilon greedy """

        input_t = test_env.reset()
        total_reward = 0

        win_cnt = 0
        loss_cnt = 0

        for e in range(testing_days):
            game_over = False

            # get initial input

            while not game_over:

                input_tm1 = input_t

                # get next action
                q = model.predict(input_tm1.reshape((1,input_tm1.shape[0],input_tm1.shape[1],)))
                action = np.argmax(q[0])

                # apply action, get rewards and new state
                input_t, reward, game_over, idays, lineindex = test_env.act(action) 

                if reward > 0:
                    win_cnt += 1

                if reward < 0:
                    loss_cnt += 1

                total_reward += reward

        return total_reward 
