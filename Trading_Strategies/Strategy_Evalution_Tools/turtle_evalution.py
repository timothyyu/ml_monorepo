
from scipy import stats

from sklearn import linear_model

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ### 海龟交易法则－稳健投资策略评估方法
# 海龟交易法则书中提到几种评估稳健投资策略的方法：
# 
# 1. RAR － Regressed Annual Return
# 
# RAR 比CAGR对于一个波动的净值曲线而言， 更能够稳定的测量该曲线的上涨幅度和回报率。 
# In[223]:
def RAR(ret) :
    n = ret.count()
    nav = (1+ret).cumprod()
    cagr = (nav[-1]/nav[0] -1) / n 

    reg = linear_model.LinearRegression()
    X = np.array(range(n), ndmin=2).transpose();
    y = np.array(nav.data, ndmin=2).transpose()
    reg.fit(X, y)

    rar = (reg.predict(X[-1]) / reg.predict(X[0]) -1) / n
    rar = np.float64(rar)
    
    
    return cagr, rar, reg

def Sharpe(ret, annualized_factor = 365) :
    cagr, rar, reg = RAR(ret)
    cagr = cagr * annualized_factor
    rar = rar * annualized_factor
    vol = np.std(ret) * np.sqrt(annualized_factor)
    
    r_sharpe = rar / vol
    sharpe = cagr / vol
    return sharpe, r_sharpe




# 2 稳健风险回报比例（robust risk/reward ratio)

# In[181]:

def MDD(ret, N) :
    nav = (1+ret).cumprod();
    high_wm = nav * 0 #high water mark


    for i in range(len(ret)) :
        if i == 0:
            high_wm[i] = nav[i]
        else:
            high_wm[i] = nav[i] if nav[i] > high_wm[i-1] else high_wm[i-1]

    dd = nav - high_wm ## drawdown curves

    ### determine the numbers of the drawdown periods, and their start/end index
    start = []
    end = []
    for j in range(len(dd)) :
        if j > 0:
            if dd[j] < 0 and dd[j - 1] == 0: 
                start.append(j);
            if dd[j] == 0 and dd[j -1] < 0:
                end.append(j);
            if dd[j] <0 and j == len(dd) - 1:
                end.append(j);

    ### drawdown percentage
    dd_pct = dd * 0
    n_dd = len(start)
    for k in range(n_dd):
        dd_pct[start[k]:end[k]] = nav[start[k]:end[k]] / nav[start[k]-1] - 1

    ###
    dd_size = []
    dd_duration = []
    n_dd = len(start)
    for k in range(n_dd):
        dd_size.append(min(dd_pct[start[k]:end[k]]))
        dd_duration.append(end[k] - start[k])

    ### top N largest drawdown
    max_dd_size = []
    max_dd_duration = []
    for l in range(N) :
        max_dd = min(dd_size)
        index = dd_size.index(max_dd)

        max_dd_size.append(dd_size.pop(index))
        max_dd_duration.append(dd_duration.pop(index))
        
    ### output
    return max_dd_size, max_dd_duration

 
### length_adjusted_MDD annualize MDD with their average length.
### the formula is : Average_Max_DD / Average_DD_Duration * Annulized_factor (365 by default, if days are using)
def length_adjusted_MDD(ret, N = 5, annualized_factor = 365) :
    max_dd_size, max_dd_duration = MDD(ret, N);
    avg_mdd = np.mean(max_dd_size)
    avg_mdd_duration = np.mean(max_dd_duration)
    
    la_MDD = avg_mdd / avg_mdd_duration * annualized_factor
    return la_MDD
    


# In[204]:

def RRR(ret, N = 5, annualized_factor = 365):
    cagr, rar, reg= RAR(ret)
    rar = rar * annualized_factor

    la_mdd = length_adjusted_MDD(ret, N, annualized_factor)
    rrr = rar / abs(la_mdd)
    return rrr


