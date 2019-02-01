import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GMM
import pandas as pd
from Technical_Trading.util import is_oos_data
import pyfolio as pf
from matplotlib import pyplot as plt

def get_data() :
    data = pd.read_csv('/Users/jianboxue/Documents/Research_Projects/data/index_shanghai.csv', index_col='date', parse_dates=True)
    data = data['20000101'::]
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



#####
def get_pattern(data, n):
    ret = data['ret_co']
    price = data['close']
    meta = pd.DataFrame()
    meta['ret'] = ret
    meta['price'] = price
    meta['price_n'] = price.shift(-n)
    
    meta['max'] = pd.rolling_max(ret, n).shift(1)
    meta['min'] = pd.rolling_min(ret, n).shift(1)
    meta['signal_max'] = (ret > meta['max']) * 1
    meta['signal_min'] = (ret < meta['min']) * 1
    
    meta['up_n'] = (price < meta['price_n']) * 1
    meta['down_n'] = (price > meta['price_n']) * 1
    
    return meta
    
    
    
 


#####
def risk_measure(data, n):
    meta = get_pattern(data, n)
    max_break = meta.ix[meta['signal_max'] == 1]
    min_break = meta.ix[meta['signal_min'] == 1]
    
    total_max_break = sum(max_break['signal_max'])
    total_min_break = sum(min_break['signal_min'])
    
    
    total_ups = sum(max_break.ix[max_break['up_n'] ==1, 'up_n'])
    total_downs = sum(min_break.ix[min_break['down_n'] == 1, 'down_n'])
    
    win_rate_maxbreak = float(total_ups) / float(total_max_break)
    win_rate_minbreak = float(total_downs) / float(total_min_break)
    return win_rate_maxbreak, win_rate_minbreak
      
    
data = get_data()
data = data['20000101':]

win_rate1 = []
win_rate2 = []
for i in range(400) :
    
    w1, w2 = risk_measure(data, i+1)
    print(i+1, w1, w2)
    win_rate1.append(w1)
    win_rate2.append(w2)
    
plt.plot(win_rate1)
plt.plot(win_rate2)
win_rate1
    