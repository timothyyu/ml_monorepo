
import matplotlib.pyplot as plt
import pandas as pd
import technical_trading as tt
import pyfolio as pf
import numpy as np
import talib as ta


from timeit import itertools
import operator
#import Strategy_Evalution_Tools.turtle_evalution as te


#import matplotlib.pyplot as py
def read_data() :
    data = pd.read_csv('/Users/jianboxue/Documents/Research_Projects/data/hs300.csv', 
                       index_col='date', parse_dates=True)
    data.vol = data.vol.astype(float)
    start = pd.Timestamp('2005-09-01')
    end = pd.Timestamp('2012-03-15')
    data = data[start:end]
    return data


def process_data(data):
    output = pd.DataFrame()
    output['open'] = data['open']
    output['high'] = data['high']
    output['low'] = data['low']
    output['close'] = data['close']
    output['price'] = data['close']
    
    
    ## add returns series
    for j in [1, 2, 5, 10] :
        output['ret' + str(j)] = (output['close']/output['close'].shift(j) - 1)
        
    ## add EMA 
    for j in [2, 5, 10, 20, 50, 100] :
        output['ema' + str(j)] = ta.EMA(np.array(output['price']), j)

    ## add lag price
    for i in range(1, 15) :
        output['price' + str(i)] = data['close'].shift(i)
    
    ### KDJ
    K,D,J = kdj(data)
    output['K'] = K
    output['D'] = D
    output['J'] = J
  
    return output
       

def kdj(HLC, n = 14, m = 3, l = 3, s = 3) :
    C = HLC['close'] # Close price
    L = HLC['low']
    H = HLC['high']

    L_n = pd.rolling_min(L, n)
    H_n = pd.rolling_max(H, n)
    RSV_n = (C - L_n)/(H_n - L_n) * 100
    K = ta.EMA(np.array(RSV_n), m)
    
    D = ta.EMA(np.array(K), l)
    J = s*D - (s-1)*K
    return K, D, J#, RSV_n, signal

import random
import operator
import csv
import itertools

import numpy

from deap import algorithms
from deap import base
from deap import creator
from deap import tools
from deap import gp

# Read the spam list features and put it in a list of lists.
# The dataset is from http://archive.ics.uci.edu/ml/datasets/Spambase
# This example is a copy of the OpenBEAGLE example :
# http://beagle.gel.ulaval.ca/refmanual/beagle/html/d2/dbe/group__Spambase.html
with open("spambase.csv") as spambase:
    spamReader = csv.reader(spambase)
    spam = list(list(float(elem) for elem in row) for row in spamReader)

# defined a new primitive set for strongly typed GP
pset = gp.PrimitiveSetTyped("MAIN", itertools.repeat(float, 57), bool, "IN")

# boolean operators
pset.addPrimitive(operator.and_, [bool, bool], bool)
pset.addPrimitive(operator.or_, [bool, bool], bool)
pset.addPrimitive(operator.not_, [bool], bool)

# floating point operators
# Define a protected division function
def protectedDiv(left, right):
    try: return left / right
    except ZeroDivisionError: return 1

pset.addPrimitive(operator.add, [float,float], float)
pset.addPrimitive(operator.sub, [float,float], float)
pset.addPrimitive(operator.mul, [float,float], float)
pset.addPrimitive(protectedDiv, [float,float], float)

# logic operators
# Define a new if-then-else function
def if_then_else(input, output1, output2):
    if input: return output1
    else: return output2

pset.addPrimitive(operator.lt, [float, float], bool)
pset.addPrimitive(operator.eq, [float, float], bool)
pset.addPrimitive(if_then_else, [bool, float, float], float)

# terminals
pset.addEphemeralConstant("rand100", lambda: random.random() * 100, float)
pset.addTerminal(False, bool)
pset.addTerminal(True, bool)

creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=1, max_=2)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("compile", gp.compile, pset=pset)

def evalSpambase(individual):
    # Transform the tree expression in a callable function
    func = toolbox.compile(expr=individual)
    # Randomly sample 400 mails in the spam database
    spam_samp = random.sample(spam, 400)
    # Evaluate the sum of correctly identified mail as spam
    result = sum(bool(func(*mail[:57])) is bool(mail[57]) for mail in spam_samp)
    return result,
    
toolbox.register("evaluate", evalSpambase)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

def main():
    random.seed(10)
    pop = toolbox.population(n=100)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean)
    stats.register("std", numpy.std)
    stats.register("min", numpy.min)
    stats.register("max", numpy.max)
    
    algorithms.eaSimple(pop, toolbox, 0.5, 0.2, 40, stats, halloffame=hof)

    return pop, stats, hof

if __name__ == "__main__":
    main()












