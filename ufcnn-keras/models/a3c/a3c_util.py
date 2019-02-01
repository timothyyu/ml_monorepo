import numpy as np

# Sample from the policy distribution
# (requires pi_values to be a normalized probabilities vector)
def choose_action(pi_values, use_argmax=False):
    if use_argmax:
        return np.argmax(pi_values)

    return np.random.choice(len(pi_values), p=pi_values)

# Original equivalent code was:
#def choose_action_old(pi_values):
#    values = []
#    sum = 0.0
#    for rate in pi_values:
#        sum = sum + rate
#        value = sum
#        values.append(value)
#
#    r = random.random() * sum
#    for i in range(len(values)):
#        if values[i] >= r:
#            return i;
#    #fail safe
#    return len(values)-1

