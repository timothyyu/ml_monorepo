
# coding: utf-8

# In[15]:

### Prepare the workbook
import numpy
from scipy import stats

from sklearn import linear_model

import matplotlib.pyplot as plt
import pandas as pd
import pyfolio as pf
import tushare as ts


# In[41]:
#### function: get Patterns with specified nr of days lookingback
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


# ### Case1: 上证指数

# In[50]:

data = pd.read_csv('../../data/index_shanghai.csv', index_col='date', parse_dates=True)
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


### capture the pattern
pattern = get_patterns(3, data['ret_cc'])
ret_pattern = pd.DataFrame(pattern.shift(1), columns=['pattern']).join(ret_all)
#ret_pattern = ret_pattern[~numpy.isnan(ret_pattern['pattern'])]
ret_pattern_grouped = ret_pattern.groupby('pattern')

### data to test
nr_group = ret_pattern_grouped.count().shape[0]
plt.figure(figsize=(12,10),dpi=98)
for i in range(nr_group) :
    plt.subplot(3,3,i+1)
    ret_test = ret_pattern_grouped.get_group(i)
    plt.plot(ret_test.cumsum())

#ret_pattern_grouped.get_group(1).cumsum().plot()
pattern


# In[31]:

pattern = get_patterns(1, data['ret_co'])
ret_pattern = pd.DataFrame(pattern.shift(1), columns=['pattern']).join(ret_all)
ret_pattern_grouped = ret_pattern.groupby('pattern')
ret_pattern_grouped.get_group(0)


# In[32]:

ret_strategy = data['ret_cc'] * 0;
ret_strategy = pd.DataFrame.merge(ret_strategy, ret_pattern_grouped.get_group(6).ix[:,1])
ret_strategy[numpy.isnan(ret_strategy) ]  = 0
ret_strategy = ret_strategy + ret_pattern_grouped.get_group(4).ix[:,1]
ret_strategy[numpy.isnan(ret_strategy)] = 0

#ret_strategy = pd.DataFrame.merge((data['ret_cc']*0), ret_pattern_grouped.get_group(6).ix[:,1], how='outer')
#ret_pattern_grouped.get_group(4).ix[:,1]
#pf.create_returns_tear_sheet(ret_strategy, benchmark_rets=data['ret_cc'])


# In[765]:

get_ipython().magic('pinfo pd.DataFrame.merge')


# 

# In[718]:




# In[719]:

pd.


# ### 测试中证500 IC期货和指数投资

# In[730]:

### loading data
data = pd.read_excel('../../data/IC500_CurrentMonth_20151027.xlsx', index_col='date', parse_dates=True)
data_future = data.ix[:,0:7]
data_index = data.ix[:, 8:]

### calculate returns of the indicies
ret_index_cc = data['bm_close'] / data['bm_close'].shift(1) - 1
ret_index_co = data['bm_close'] / data['bm_open'] - 1
ret_index_oc = data['bm_open'] / data['bm_close'].shift(1) - 1
ret_index_all = pd.DataFrame()
ret_index_all['cc'] = ret_index_cc
ret_index_all['co'] = ret_index_co
ret_index_all['oc'] = ret_index_oc
ret_index_all = ret_index_all.dropna()

### calculate returns of the future
ret_future_cc = data['fu_close'] / data['fu_close'].shift(1) - 1
ret_future_co = data['fu_close'] / data['fu_open'] - 1
ret_future_oc = data['fu_open'] / data['fu_close'].shift(1) - 1
ret_future_all = pd.DataFrame()
ret_future_all['cc'] = ret_future_cc
ret_future_all['co'] = ret_future_co 
ret_future_all['oc'] = ret_future_oc
ret_future_all = ret_future_all.dropna()


# In[14]:

### capture the pattern
pattern = get_patterns(1, ret_index_all['co'])
ret_pattern = pd.DataFrame(pattern.shift(1), columns=['pattern']).join(ret_future_all)
ret_pattern = ret_pattern[~numpy.isnan(ret_pattern['pattern'])]
ret_pattern_grouped = ret_pattern.groupby('pattern')

### data to test
nr_group = ret_pattern_grouped.count().shape[0]
plt.figure(figsize=(12,10),dpi=98)
for i in range(0, nr_group) :
    plt.subplot(3,3,i+1)
    ret_test = ret_pattern_grouped.get_group(i)
    plt.plot(ret_test.cumsum())

ret_pattern_grouped


# In[738]:

pf.create_full_tear_sheet(ret_pattern_grouped.get_group(1).ix[:, 2], benchmark_rets=ret_future_all['cc'])


# In[ ]:



