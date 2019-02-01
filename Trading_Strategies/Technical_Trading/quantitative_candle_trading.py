import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GMM
import pandas as pd
from Technical_Trading.util import is_oos_data

import pyfolio as pf

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

def get_feature7(data):
    delta = pd.DataFrame()
    

def get_feature6(data): 
    delta = pd.DataFrame()
    hl = data['high'] - data['low']
    cl = data['close'] - data['low']
    delta['ibs'] = cl / hl * 100
    delta['ibs_1'] = delta['ibs'].shift(1)
    #delta['ibs_2'] = delta['ibs'].shift(2)
    #delta['ibs_3'] = delta['ibs'].shift(3)
    delta  = delta.dropna()
    return delta

def get_feature5(data) :
    delta = pd.DataFrame()
    delta['ho'] = data['high'] - data['open']
    delta['co'] = data['close'] - data['open']
    delta['lo'] = data['low'] - data['open'] 
    hl = data['high'] - data['low']
    cl = data['close'] - data['low']
    #delta['hc'] = data['high'] = data['close']
      
    delta['ho1'] = delta['ho'].shift(1)
    delta['co1'] = delta['co'].shift(1)
    delta['lo1'] = delta['lo'].shift(1)
#     
    delta['ho2'] = delta['ho'].shift(2)
    delta['co2'] = delta['co'].shift(2)
    delta['lo2'] = delta['lo'].shift(2)

    
    #delta['ibs'] = cl / hl * 100
    #delta['ibs_1'] = delta['ibs'].shift(1)
    #delta['ibs_2'] = delta['ibs'].shift(2)
    #delta['ibs_3'] = delta['ibs'].shift(3)
    #delta['ibs_4'] = delta['ibs'].shift(4)
    delta  = delta.dropna()
    
    return delta

def get_feature4(data):
    delta = pd.DataFrame()
    delta['high'] = data['high']
    delta['low'] = data['low']
    delta['open'] = data['open']
    delta['close'] = data['close']
    
    delta['h1'] = delta['high'].shift(1)
    delta['h2'] = delta['high'].shift(2)
    delta['l1'] = delta['low'].shift(1)
    delta['l2'] = delta['low'].shift(2)
    delta['o1'] = delta['open'].shift(1)
    delta['o2'] = delta['open'].shift(2)
    delta['c1'] = delta['close'].shift(1)
    delta['c2'] = delta['close'].shift(2)
    
    delta = delta.dropna()
    #data = data.join(delta)
    
    return delta

def get_feature1(data):
    delta = pd.DataFrame()
    hi = data['high']
    lo = data['low']
    op = data['open']
    cl = data['close']
    
    delta['hilo'] = (hi/lo).shift(2) 
    delta['oplo'] = (op/lo).shift(2)
    delta['cllo'] = (cl/lo).shift(2)
    
    delta['hi1lo'] = (hi/lo.shift(1)).shift(1)
    delta['lo1lo'] = (lo/lo.shift(1)).shift(1)
    delta['op1lo'] = (op/lo.shift(1)).shift(1)
    delta['cl1lo'] = (cl/lo.shift(1)).shift(1)
    
    delta['hi2lo'] = (hi/lo.shift(2))
    delta['lo2lo'] = (lo/lo.shift(2))
    delta['op2lo'] = (op/lo.shift(2))
    delta['cl2lo'] = (cl/lo.shift(2))
    
    
    delta = delta.dropna()
    #data = data.join(delta)
    
    return delta

def get_feature2(data):
    delta = pd.DataFrame()
    hi = data['high']
    lo = data['low']
    op = data['open']
    cl = data['close']
    
    delta['hilo'] = (hi-lo).shift(2) 
    delta['oplo'] = (op-lo).shift(2)
    delta['cllo'] = (cl-lo).shift(2)
    
    delta['hi1lo'] = (hi-lo.shift(1)).shift(1)
    delta['lo1lo'] = (lo-lo.shift(1)).shift(1)
    delta['op1lo'] = (op-lo.shift(1)).shift(1)
    delta['cl1lo'] = (cl-lo.shift(1)).shift(1)
    
    delta['hi2lo'] = (hi-lo.shift(2))
    delta['lo2lo'] = (lo-lo.shift(2))
    delta['op2lo'] = (op-lo.shift(2))
    delta['cl2lo'] = (cl-lo.shift(2))
    
    
    delta = delta.dropna()    
    return delta

def get_feature3(data):
    delta = pd.DataFrame()
    hi = data['high']
    lo = data['low']
    op = data['open']
    cl = data['close']
    
    delta['hilo'] = (hi-lo) 
    delta['oplo'] = (op-lo)
    delta['cllo'] = (cl-lo)
    
    delta['hilo1'] = delta['hilo'].shift(1)
    delta['oplo1'] = delta['oplo'].shift(1)
    delta['cllo1'] = delta['cllo'].shift(1)
    
    delta['hilo2'] = delta['hilo'].shift(2)
    delta['oplo2'] = delta['oplo'].shift(2)
    delta['cllo2'] = delta['cllo'].shift(2)
    
    
    delta = delta.dropna()    
    return delta

def get_feature(data, feature_type):
    if feature_type == 1:
        return get_feature1(data)
    if feature_type == 2:
        return get_feature2(data)
    if feature_type == 3:
        return get_feature3(data)
    if feature_type == 4:
        return get_feature4(data)
    if feature_type == 5:
        return get_feature5(data)
    if feature_type == 6:
        return get_feature6(data)
    else :
        return []
        

 
### function to get trading strategy report
def risk_measure(ret, group, nr_group):
    nr_trade = []
    nr_winning = []
    nr_losing = []
    pct_winning = []
    
    total_trade = []
    total_winning = []
    total_losing = []
    avg_trade = []
    avg_winning = []
    avg_losing = []
    
    max_dd = []
    sharpe = []
    sortino = []
    
    for i in range(nr_group) :
        ret_group = ret * ((group == i)*1).shift(1)
        ### numbers of trading 
        nr_trade.append(sum((group == i)*1))
        nr_winning.append(sum((ret_group > 0) * 1))
        nr_losing.append(nr_trade[i] - nr_winning[i])
        pct_winning.append(float(nr_winning[i]) / nr_trade[i])
        
        ### avg trading profit
        total_winning.append(sum(ret_group[ret_group > 0]))
        avg_winning.append(total_winning[i] / nr_winning[i])
        total_losing.append(sum(ret_group[ret_group < 0]))
        avg_losing.append(total_losing[i] / nr_losing[i])
        total_trade.append(sum(ret_group.dropna()))
        avg_trade.append(total_trade[i] / nr_trade[i])
         
        ### risk measure
        max_dd.append(pf.timeseries.max_drawdown(ret_group))
        sharpe.append(pf.timeseries.sharpe_ratio(ret_group))
        sortino.append(pf.timeseries.sortino_ratio(ret_group))

    stats = {}
    stats['nr_trade'] = nr_trade
    stats['nr_winning'] = nr_winning
    stats['nr_losing'] = nr_losing
    stats['pct_winning'] = pct_winning
    
    stats['total_winning'] = total_winning
    stats['total_losing'] = total_losing
    stats['total_trade'] = total_trade
    
    stats['avg_winning'] = avg_winning
    stats['avg_losing'] = avg_losing
    stats['avg_trade'] = avg_trade
    
    stats['max_dd'] = max_dd
    stats['sharpe'] = sharpe
    stats['sortino'] = sortino
    return stats


    
def trading(nr_groups, is_data, oos_data, grouping_type='kmeans', feature_type = 1):
    is_delta = get_feature(is_data, feature_type)
    oos_delta = get_feature(oos_data, feature_type)
    
    ### using machine learning algorithm to group the data
    if grouping_type == 'kmeans':
        #### using k-mean to categorize
        model = KMeans(nr_groups)
        fitted = model.fit(np.array(is_delta))
        is_delta['group'] = fitted.labels_
        oos_delta['group'] = fitted.predict(np.array(oos_delta))
    if grouping_type == 'gmm':
        ### Using GMM to calibrate
        model = GMM(nr_groups)
        is_delta['group'] = model.fit_predict(np.array(is_delta))
        oos_delta['group'] = model.predict(np.array(oos_delta))
    
    is_stats = risk_measure(is_data['ret_cc'], is_delta['group'], nr_groups)
    ### calculate the returns
    oos_ret = pd.DataFrame()
    is_ret = pd.DataFrame()
    
    strategy_is_ret = is_data['ret_cc'] * 0
    strategy_oos_ret = oos_data['ret_cc'] * 0
    
    for i in range(nr_groups) :
        oos_ret[str(i)] = oos_data['ret_cc'] * ((oos_delta['group'] == i)*1).shift(1)
        is_ret[str(i)] = is_data['ret_cc'] * ((is_delta['group'] == i)*1).shift(1)
     
        if is_stats['sharpe'][i] > 0.5:
            strategy_is_ret = strategy_is_ret + is_ret[str(i)]
            strategy_oos_ret = strategy_oos_ret + oos_ret[str(i)]
        #if is_stats['sharpe'][i] < -0.5:
        #    strategy_is_ret = strategy_is_ret - is_ret[str(i)]
        #    strategy_oos_ret = strategy_oos_ret - oos_ret[str(i)]        
            
    return  is_ret, oos_ret, is_stats, strategy_is_ret, strategy_oos_ret
    

### Strategy_full_test conducts in-sample and out-of-sample trading optimization
def strategy_full_test(data, grouping_nr, grouping_type, grouping_feature_type, n_lookback, n_sliding, oos_type = 'sliding'):
    data_is, data_oos = is_oos_data(data, oos_type, n_lookback, n_sliding)
    nr_chunck = len(data_is)
    
    str_all_oos_ret = pd.Series()
    for i in range(nr_chunck) :
        chunck_is = data_is[i]
        chunck_oos = data_oos[i]
        
        is_ret, oos_ret, stats, str_is_ret, str_oos_ret = trading(grouping_nr, chunck_is, chunck_oos, grouping_type, grouping_feature_type)
        if i == 0:
            str_all_oos_ret = str_oos_ret
        else :
            str_all_oos_ret = pd.concat([str_all_oos_ret, str_oos_ret])
        
    return str_all_oos_ret;
    

data = get_data()

#is_ret, oos_ret, stats, str_is_ret, str_oos_ret =  trading(10, data[3000:3500], data[3500:3700], 2)

str_oos_ret = pd.DataFrame()
for i in range(5):
    print(i)
    ret0 = strategy_full_test(data, grouping_nr=10, grouping_type='kmeans', grouping_feature_type=i+2, 
                                  n_lookback=1000, n_sliding=250,  oos_type = 'rolling')
    ret = pd.DataFrame(ret0, index=ret0.index, columns=['feature '+str(i)])
    if i == 0:
        str_oos_ret = ret
    else :
        str_oos_ret = str_oos_ret.join(ret)
        
import matplotlib.pyplot as plt
#plt.plot((1+str_is_ret).cumprod())
plt.plot((1+str_oos_ret).cumprod())

#data_is, data_oos = is_oos_data(data, 2, 1000, 500)

print('hello')
#print(delta.head()))