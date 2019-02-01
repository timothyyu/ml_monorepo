
# coding: utf-8

# In[2]:

### Preparing the workbook
import talib 

import numpy as np
import pandas as pd
import pyfolio as pf
import te


# In[3]:
### Load Data
### Reading 中证500 ETF（510500）
data = pd.read_csv('../../data/index_shanghai.csv', index_col='date', parse_dates=True)

### weekly resample
#ohlc_dict = {
#    'open':'first',
#    'high':'max',
#    'low':'min',
#    'close':'last',
#    'vol':'sum'
#    }
#data = data.resample('W-Fri', how=ohlc_dict)

data = data['20050901'::]
#data = data['20120315']
ret = pd.DataFrame()
ret['ret_cc'] = (data['close'] / data['close'].shift(1) - 1)
ret['ret_co'] = (data['close'] / data['open'] - 1)
ret['ret_oc'] = (data['open'] / data['close'].shift(1) - 1)


# In[4]:

(1+ret['ret_co']).cumprod().plot()


# In[64]:

### Load Data
### Reading 中证500 ETF（510500）
data = pd.read_excel('../../data/中证500_20151027.xlsx', index_col='date', parse_dates=True)
ret = pd.DataFrame()
ret['cc'] = (data['close'] / data['close'].shift(1) - 1)
ret['co'] = (data['close'] / data['open'] - 1)
ret['oc'] = (data['open'] / data['close'].shift(1) - 1)
(ret['co'] - ret['oc']).cumsum().plot()
pf.create_full_tear_sheet((ret['co']), benchmark_rets=ret['cc'])


# In[67]:

ret_strategy = pd.DataFrame()
ret_strategy['0'] = ret['cc']
#ret_strategy['1'] = ret['oc'] * (ret['co'] > 0).shift(1)
ret_strategy['2'] = ret['co'] * ((ret['oc'] > 0)*1).shift(1)
#ret_strategy['3'] = ret['oc'] * (ret['co'] < 0).shift(1)
#ret_strategy['4'] = ret['co'] * (ret['oc'] < 0).shift(1)
ret['5'] = ret['co'] * ((ret['co'] > 0)*1).shift(1)
#ret_strategy['6'] = ret['co'] * (ret['co'] < 0).shift(1)
#ret_strategy['7'] = ret['oc'] * (ret['oc'] > 0).shift(1)
#ret_strategy['8'] = ret['oc'] * (ret['oc'] < 0).shift(1)

#ret_strategy['9'] = ret['co'] * (ret['cc'] < 0).shift(1)
ret_strategy['10'] = ret['co'] * ((ret['cc'] > 0)*1).shift(1)
#ret_strategy['11'] = ret['oc'] * (ret['cc'] < 0).shift(1)
#ret_strategy['12'] = ret['oc'] * (ret['cc'] > 0).shift(1)


ret_strategy['13'] = ret['co'] * ((ret['oc'] < 0)*1)
ret_strategy['14'] = ret['co'] * ((ret['oc'] > 0)*1)

ret_strategy.cumsum().plot()


# In[71]:

pf.create_full_tear_sheet(ret['5'], benchmark_rets=ret['cc'])


# In[ ]:



