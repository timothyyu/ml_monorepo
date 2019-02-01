
import json
import numpy as np

import DataStore as ds


class ExperienceReplay(object):
    def __init__(self, max_memory=100, discount=.9, env = None, sequence_dim=(1,1)):
        self.max_memory = max_memory
        self.memory = list()
        self.discount = discount
        self.environment = env
        self.sequence_dim = sequence_dim

    def remember(self, states, game_over):
        # memory[i] = [[state_t, action_t, reward_t, state_t+1], game_over?]
        self.memory.append([states, game_over])
        if len(self.memory) > self.max_memory:
            del self.memory[0]

    def get_batch(self, model, batch_size=10):
        len_memory = len(self.memory)
        num_actions = model.output_shape[-1]
        out_dim = self.environment.get_action_count()
        inputs = np.zeros((min(len_memory, batch_size),) + self.sequence_dim)
        targets = np.zeros((inputs.shape[0], num_actions))
        for i, idx in enumerate(np.random.randint(0, len_memory,
                                                  size=inputs.shape[0])):
            print("DIM ",i,idx,len_memory)
            #state_t, action_t, reward_t, state_tp1, idays_t, lineindex_t = self.memory[idx][0]

            action_t, reward_t, idays_t, lineindex_t = self.memory[idx][0]
            state_t = self.environment.observe(idays_t, lineindex_t)

            # State TP1 is the next state
            game_over = self.memory[idx][1]
            #print ("STATET",state_t)

            #inputs[i:i+1] = state_t
            inputs[i] = state_t

            # There should be no target values for actions not taken.
            # Thou shalt not correct actions not taken #deep

            a = model.predict(self.resize_input(state_t))[0]
            print("TARGET ",a)
            targets[i] = a
            if game_over:  # if game_over is True
                targets[i, action_t] = reward_t
            else:
                state_tp1 = self.environment.observe(idays_t, lineindex_t+1)
                # reward_t + gamma * max_a' Q(s', a')
                Q_sa = np.max(model.predict(self.resize_input(state_tp1))[0])
                targets[i, action_t] = reward_t + self.discount * Q_sa
            print("TARGET after",targets[i])

        print ("INPUTS SHAPE after get_batch",inputs.shape)
        return inputs, targets
    
    def resize_input(self, i):
        """ resize input for ufcnn """
        #return i.reshape((i.shape[0],i.shape[1],1))  # for Catch
        #print ("NET INPUT ",i)
        if i.ndim < 3:
            i = i.reshape((1,i.shape[0],i.shape[1]))
        return i


