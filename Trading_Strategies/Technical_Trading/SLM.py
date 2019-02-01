

import numpy
from scipy import stats

from sklearn import linear_model

import matplotlib.pyplot as plt
import pandas as pd
import pyfolio as pf
from pyfolio.timeseries import sharpe_ratio
import math


def get_patterns(n, ret) :
    signals = pd.DataFrame()
    scores = [];
    for i in range(n) :
        signals[i] = (ret.shift(n-i-1) > 0) * 1
        if (i == 0) :
            scores = signals[i];
        else :
            scores = scores + signals[i] * pow(2, i);
    return scores;

def get_patterns1(n, ret) :
    signals = pd.DataFrame();
    scores = [];
    for i in range(0, n) :
        signals[i] = 2*(ret.shift(n - i-1) > 0.0075)
        signals[i] = signals[i] + 1*((ret.shift(n - i - 1) > -0.0075) & (signals[i] != 2))
        if (i == 0) :
            scores = signals[i];
        else :
            scores = scores + signals[i] * pow(3, i);
    return scores;

### function: get patterns, and calculate the historical insample returns, sharpe ratios and 
### other risk measures for each pattern. 
def pattern_characters(n, ret, annualized_factor=365) :
    pattern = get_patterns(n, ret)
    ret_pattern = pd.DataFrame(pattern.shift(1), columns=['pattern']).join(ret)
    ret_pattern_grouped = ret_pattern.groupby('pattern')

    nr_group = ret_pattern_grouped.count().shape[0]
    counts = {}
    probs = {}
    profit_factor = {}
    sharpes = {}
    for i in range(nr_group) :
        ret_test = ret_pattern_grouped.get_group(i).ix[:, 1]
        #print(ret_test.shape?)
        counts[i] = len(ret_test)
        probs[i] = float(numpy.sum(ret_test > 0)) / counts[i]
        profit_factor[i] = numpy.sum(ret_test[ret_test > 0]) / numpy.sum(-ret_test[ret_test < 0])
        sharpes[i] = numpy.mean(ret_test) / numpy.std(ret_test) * numpy.sqrt(annualized_factor)
    prob_list = pd.DataFrame(pd.Series(counts, name='count'), index = range(nr_group))
    prob_list = prob_list.join(pd.Series(probs, name='win_rate'))
    prob_list = prob_list.join(pd.Series(profit_factor, name='profit_factor'))
    prob_list = prob_list.join(pd.Series(sharpes, name='sharpes'))
    return prob_list
 

### function: 3 types of out-of-sample test for the pattern trading
def strategy_oos_test(n, ret, type = 1, n_lookback = 0, n_sliding = 0) :
    n_total = len(ret)
    ret_oos = pd.DataFrame();
    
    ## type = 1: single train set defined by n_lookback, single test set from n_lookback:n_total
    if type == 1 or type == 0:
        ret_train = ret[0:(n_lookback - 1)]
        ret_test = ret[n_lookback::]

        prob_list = pattern_characters(n, ret_train)
           
        ret_strategy1 = optimize_returns(n, ret_test, prob_list)
        ret_oos['t1'] = ret_strategy1
        #(1+ret_strategy).cumprod().plot()
    ## type 2: sliding insample window, defined by n_lookback and sliding forward. The test set window is defined as n_      
    if type == 2 or type == 0:
        k = n_lookback
        ret_strategy2 = pd.Series()
        while k < n_total-1 :
            ret_train = ret[0:(k - 1)]
            if (k+n_sliding) <= n_total :
                k2 = k + n_sliding - 1
            else :
                k2 = n_total - 1
            ret_test = ret[k:k2]

            ## trading
            prob_list = pattern_characters(n, ret_train)
            ret_strategy2 = ret_strategy2.append(optimize_returns(n, ret_test, prob_list))
            k = k2;
        ret_oos['t2'] = ret_strategy2
        #(1+ret_strategy).cumprod().plot()
    ## type 3: sliding insample window, defined by n_lookback and sliding forward. The test set window is defined as n_      
    if type == 3 or type == 0:
        k = n_lookback
        ret_strategy3 = pd.Series()
        while k < n_total-1 :
            ret_train = ret[(k-n_lookback):(k - 1)]
            if (k+n_sliding) <= n_total :
                k2 = k + n_sliding - 1
            else :
                k2 = n_total - 1
            ret_test = ret[k:k2]

            ## trading
            prob_list = pattern_characters(n, ret_train)
            ret_strategy3 = ret_strategy3.append(optimize_returns(n, ret_test, prob_list))
            k = k2;
        ret_oos['t3'] = ret_strategy3
        #(1+ret_strategy).cumprod().plot()
        
    return ret_oos;



        

### prepare the data
def get_data() :
    data = pd.read_csv('/Users/jianboxue/Documents/Research_Projects/data/index_shanghai.csv', index_col='date', parse_dates=True)
    data = data['19950101'::]
    #data = pd.read_excel('../../data/500ETF_510500_1d_20151028.xlsx', index_col='date', parse_dates=True)
    
    #### Return calculation
    ret_cc = data['close'] / data['close'].shift(1) - 1
    ret_co = data['close'] / data['open'] - 1
    ret_oc = data['open'] / data['close'].shift(1) - 1
    data['ret_cc'] = ret_cc;
    data['ret_co'] = ret_co;
    data['ret_oc'] = ret_oc;
    ret_all = data.ix[:, ('ret_cc', 'ret_co', 'ret_oc')]
    
    ### cleaning
    data = data.dropna()
    return data


### function: determine the best trading strategy, based on the pattern,and its historical risk measure
def optimize_returns(n, ret, prob_list) :
    n_total = len(ret)
    patterns = get_patterns(n, ret);
    ret_patterns = pd.DataFrame(patterns.shift(1), columns=['patterns']).join(ret)
    
    signal = pd.Series(0.0, index=ret_patterns.index)
    for i in range(n_total) :
        pattern = ret_patterns['patterns'].ix[i]
        if numpy.isnan(pattern):
            sharpe = 0;
            win_ratio = 0;
            profit_factor = 1;
        else :
            sharpe = prob_list['sharpes'].ix[pattern]
            win_ratio = prob_list['win_rate'].ix[pattern]
            profit_factor = prob_list['profit_factor'].ix[pattern]
            
        #### implementing Kelly Ratio
        #if (win_ratio > 0.5) :
        #    R = win_ratio - (1-win_ratio) / profit_factor
        #else :
        #    R = 0
            
#         #print(R)
#         if ( R > 0) :
#             signal[i] = R
#         #else :
#         #    signal[i] = R
        
        
        
        if ( sharpe > 0.5) :
             signal[i] = 1
        #elif (sharpe < -1 and win_ratio < 0.5) :
        #    signal[i] = -1
        else:
             signal[i] = 0
    #print(ret_patterns.ix[:, 1])      
    ret_strategy = ret_patterns.ix[:, 1] * pd.Series(signal, index=ret_patterns.index)
    
    return ret_strategy

def test(n = 4, n_lookback=1000, n_sliding = 500, type = 1):
    data = get_data()
    ret = data['ret_cc']
    
    ret_oos = strategy_oos_test(n, ret, type, n_lookback, n_sliding)
    sharpe = numpy.mean(ret_oos) / numpy.std(ret_oos) * math.sqrt(365)
    #sharpe = pf.timeseries.sharpe_ratio(ret_oos, 'compound', period='daily')
    
    
    return ret_oos, sharpe



ret_oos, sharpe = test(type=0)
print(sharpe)
fig = plt.plot((1+ret_oos).cumprod())
plt.show()
#(1+ret_oos).cumprod().plot()

winrate = {}
winrate[1] = float(numpy.sum(ret_oos.t1[ret_oos.t1 != 0] >0)) / len(ret_oos.t1[ret_oos.t1 != 0]) 
winrate[2] = float(numpy.sum(ret_oos.t2[ret_oos.t2 != 0] > 0)) / len(ret_oos.t2[ret_oos.t2 != 0])
winrate[3] = float(numpy.sum(ret_oos.t3[ret_oos.t3 != 0] > 0))  / len(ret_oos.t3[ret_oos.t3 != 0])
#print(winrate)
    

#pf.create_returns_tear_sheet(ret_oos)

