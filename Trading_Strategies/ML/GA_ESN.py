import pandas as pd
import numpy as np
from Features import *



def fitness(S, T, Close) :
    F = pd.Series(0.0, index=Close.index)

    if S.count() == 0:
       print "No signal to evaluate"
       return 1e10

    for i in range(len(T)) :
        if (i == 0) or (i == len(T)-1): continue

        Close_j = Close[T.index[i-1]:T.index[i+1]]
        S_j = S[Close_j.index[1:-1]].dropna()

        if T[i] == 1: # buying point
            score = 0
            if S_j.count() == 0 or sum(S_j) == 0: # case c: missing opportunities
                 score = max(Close_j[1:-1]) - Close[T.index[i]]
            else:
                for j in range(S_j.count()) :
                    if S_j[j] == 1: # case a: buying signal
                        score +=  Close[S_j.index[j]] - Close[T.index[i]]
                    if (S_j[j] == -1) : #and (abs(Close[S_j.index[j]] - Close[T.index[i]])/Close[T.index[i]] < 0.05) : # case b: selling signal
                        score += (max(Close_j) - Close[T.index[i]])
                score /= S_j.count()

        else : # selling point
            #S_j = S[T.index[i-1]:T.index[i+1]]
            if S_j.count() == 0 or sum(S_j) == 0: # case c: missing opportunities
                score = Close[T.index[i]] - min(Close_j[1:-1])
            else:
                for j in range(S_j.count()) :
                    if S_j[j] == -1: # case a: buying signal
                        score +=   Close[T.index[i]] - Close[S_j.index[j]]
                    if (S_j[j] == 1): #and (abs(Close[S_j.index[j]] - Close[T.index[i]])/Close[T.index[i]] < 0.05) : # case b: selling signal
                        score += (Close[T.index[i]] - min(Close_j))
                score /= S_j.count()

        F[T.index[i]] = score
    return F.sum()

def ConfirmEP(data, delta_t, delta_p):
    peak, valley, _ ,_ = CycleIndicator.ExtremePoints(data)
    peak_confirmed = np.zeros(peak.shape)
    valley_confirmed = np.zeros(valley.shape)

    T = len(peak)
    i = 0
    while(i <= T - 1) :
#         print "i={i}".format(i=i)
        confirmed= 0
        if peak[i] == 1:
#             print "peak={i}:price={p}:to confirm".format(i=i, p=data[i])
            for j in xrange(i+1,T) :
                if valley[j] == 1:
#                     print "valley={j}:price={p}".format(j=j, p=data[j])
                    if (j-i) > delta_t and (data[i] - data[j]) /data[i] > delta_p :
                        # print "peak={i}:price={p}:confirmed".format(i=i, p=data[i])
                        peak_confirmed[i] = 1
                        confirmed = 1
                        i=j
                        break
                if peak[j] == 1:
                    if data[j] > data[i] :
                        i=j
#                         print "peak={j}:price={p}:to reconfirm".format(j=j, p=data[j])
                        continue
            if confirmed == 0:
                # print "all peaks are confirmed:exit"
                break

        elif valley[i] == 1:
#             print "valley={i}:price={p}:to confirm".format(i=i, p=data[i])
            for j in xrange(i+1, len(valley) + 1):
                if peak[j] == 1:
#                     print "peak={j}:price={p}".format(j=j, p=data[j])
                    if (j-i) > delta_t and (data[j] - data[i])/data[i] > delta_p:
                        # print "valley={i}:price={p}:confirmed".format(i=i, p=data[i])
                        valley_confirmed[i] = 1
                        confirmed = 1
                        i = j
                        break
                if valley[j] == 1:
                    if data[j] < data[i]:
                        i = j
#                         print "valley={j}:price={p}:to reconfirm".format(j=j, p=data[j])
                        continue
            if confirmed == 0:
                # print "all peaks are confirmed:exit"
                break
        else:
            i += 1

        # print "--------------------------"
    return peak_confirmed, valley_confirmed, valley_confirmed - peak_confirmed


def MovingAverageSystem(params, *args) :
    '''
    based on Baba2004 paper, the Moving average system will generate
    Golden-cross and dea-cross trade signals based on the system below.
    '''

    a = params[0] / 10.0
    b = params[1] / 10.0
    c = params[2] #/ 10.0
    a_ = params[3] / 10.0
    b_ = params[4] / 10.0
    c_ = params[5] #/ 10.0
    M = int(params[6]  + 2)
    N = int(params[7] /100.0 *  (300 - M - 1) + M + 1)


    C = args[0]

    sma1 = pd.rolling_mean(C, M)
    sma2 = pd.rolling_mean(C, N)
    Z = sma1 - sma2
    crossover = pd.Series(0, index=Z.index)
    for i in range(len(Z)) :
        if i == 0: continue
        if (Z[i-1] < 0) and (Z[i] > 0): crossover[i] = 1
        if (Z[i-1] > 0) and (Z[i] < 0): crossover[i] = -1
    crossover = crossover.where(crossover <>0).dropna().copy()


    trade = pd.Series(0, index=Z.index)
    for i in range(len(Z)):
        if i == 0: continue
        cr_j = crossover[:Z.index[i]]
        if cr_j.count() == 0: continue

        index_s = cr_j.index[-1]
        index_e = Z.index[i]
        z_j = Z[index_s:index_e]

        if Z[i] >= 0 :
            MZt = max(z_j)
            if (MZt >  b*c) and (Z[i] < min(MZt/a, c)) :
                trade[i] = 1

        if Z[i] < 0:
            MWt = max(-1*z_j)
            if (MWt >  b_*c_) and (-1*Z[i] < min(MWt/a_, c_)) :
                trade[i] = -1

    return trade

def SimpleMASystem(params, C) :
    '''
    based on Baba2004 paper, the Moving average system will generate
    Golden-cross and dea-cross trade signals based on the system below.
    '''


    M = int(params[0]  + 2)
    N = int(params[1] /100.0 *  (300 - M - 1) + M + 1)
    l_up = params[2] / 100.0
    l_down = params[3] / 100.0
    w_up = int(params[4] + 5)
    w_down = int(params[5] + 5)

    sma1 = pd.rolling_mean(C, M)
    sma2 = pd.rolling_mean(C, N)
    Z = sma1 - sma2
    crossover = pd.Series(0, index=Z.index)
    for i in range(len(Z)) :
        if i == 0: continue
        if (Z[i-1] < 0) and (Z[i] > 0):
            if Z[i] > l_up * np.max(Z[i-w_up:i]) : crossover[i] = 1
        if (Z[i-1] > 0) and (Z[i] < 0):
            if Z[i] < l_down * np.min(Z[i-w_down:i]): crossover[i] = -1
    crossover = crossover.where(crossover <>0).dropna().copy()

    return crossover

def RSI_system(params, C) :
    '''
    based on Baba2004 paper, the Moving average system will generate
    Golden-cross and dea-cross trade signals based on the system below.
    '''


    thres_ob = int(params[0]/2) + 50
    thres_os = int(params[1]/2)
    p = (100-thres_ob) * params[2] / 100
    q = thres_os * params[3] / 100
    period = int(params[4]) + 5


    rsi = ta.RSI(C.values, period)
    trade = pd.Series(0.0, index=C.index)

    last_ob = 0
    last_os = 0

    for i in range(len(rsi)) :
        if i < period - 1:
            continue


        if rsi[i] > thres_ob and rsi[i-1] < thres_ob:
            last_ob = i
        if last_ob <> 0:
            thres_sell = thres_ob + p * (i-last_ob)
            if rsi[i] < thres_sell :
                trade[i] = -1
                last_ob = 0

        if rsi[i] < thres_os and rsi[i-1] > thres_os :
            last_os = i
        if last_os <> 0:
            thres_buy = thres_os - q * (i-last_ob)
            if rsi[i] > thres_buy:
                trade[i] = 1
                last_os = 0

    trade = trade.where(trade<>0).dropna().copy()
    return trade

def Hybrid_System(params, C) :
    params1 = params[:5]
    params2 = params[5:]

    trade1 = RSI_system(params1, C)
    trade2 = SimpleMASystem(params2, C)\

    trade = pd.DataFrame(0.0, index=C.index)

    + trade1 + trade2
    trade[trade >= 1] = 1
    trade[trade <= -1] = -1
    trade = trade.where(trade<>0).dropna().copy()
    return trade

# def evaluate(individual, Close=Close, delta_t=5, delta_p=0.05) :
#     (Close, delta_t, delta_p) = args[0]
#
#     _, _, Trade = ConfirmEP(Close, delta_t, delta_p)
#     Trade = pd.Series(Trade, index=Close.index )
#     T = Trade.where(Trade<>0).dropna().copy()
#     Signal = MovingAverageSystem(individual, Close)
#     S = Signal.where(Signal<>0).dropna().copy()
#
#     fit = fitness(S, T, Close)
#     print "fitness={f}".format(f=fit)
#
#     return fit


import Quandl

if __name__  == "__main__" :

    df_tlt = Quandl.get('GOOG/NYSE_SPY', authtoken='AuFngLLqDpLf672K9W85')

    Close = df_tlt['Close']

    import array
    import random

    import numpy as np
    import pandas as pd

    from deap import algorithms
    from deap import base
    from deap import creator
    from deap import tools

    import matplotlib


    from ML.Features import *

    # df_funds = pd.read_csv('data/NAV_5ETFs.csv')
    #
    # Close = pd.Series(df_funds['zz 500'].values, index=df_funds['Date'])
    # Close  = Close[-3000:-1000]

    df_funds = pd.read_csv('data/NAV_5ETFs.csv')
    Close = pd.Series(df_funds['zz 500'].values, index=df_funds['Date']).dropna() * 100


    delta_t = 5
    delta_p = 0.15




    _, _, Trade = ConfirmEP(Close, delta_t, delta_p)
    # peak, valley, _, _ = CycleIndicator.ExtremePoints(Close)
    # Trade = valley - peak
    Trade = pd.Series(Trade, index=Close.index )

    individual = [24.80688574431058, 13.308847279590141, 64, 96, 76.48226618166598, 57, 33.565571859346065, 84.09699171247095,
                  24.80688574431058, 13.308847279590141, 64, 96, 76.48226618166598, 57, 33.565571859346065, 84.09699171247095]
    Signal =  MovingAverageSystem(individual, Close)


    T = Trade.where(Trade<>0).dropna().copy()
    T1 = Trade.where(Trade==1).dropna().copy()
    print fitness(T*0, T, Close)

    def evaluate(individual, Close=Close, T=T) :
        # Signal = MovingAverageSystem(individual, Close)
        Signal = Hybrid_System(individual, Close)
        S = Signal.where(Signal<>0)[:T.index[-1]].dropna().copy()

        fit = fitness(S, T, Close)
        print "fitness={f}:individual={i}".format(f=fit, i=individual)
        print "------------------------------------"
        return fit,
    evaluate(individual)



    toolbox = base.Toolbox()

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    toolbox.register("attr_uni", random.uniform, 0, 100)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_uni, 11)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register('evaluate', evaluate)
    toolbox.register("mate", tools.cxTwoPoint)

    toolbox.register("mutate", tools.mutUniformInt, low=0, up=100, indpb=0.5)
    toolbox.register("select", tools.selTournament, tournsize=50)

    import multiprocessing
    pool = multiprocessing.Pool()
    toolbox.register("map", pool.map)

    pop = toolbox.population(n=10000)


    pop, log = algorithms.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=100)




