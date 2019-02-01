# -*- coding: utf-8 -*-
"""
Created on Fri Nov 06 11:57:40 2015

@author: zhangchenhan
@contributor: xuejianbo 
"""

import numpy as np 
import pandas as pd
import talib as ta


#%%
### Backtest function
def Backtest_old(data, signal):
    data_bt = data.ix[:,:5]
    data_bt['pred'] = signal
    #data_bt.index = data_bt.index.tz_localize('UTC')
    positions = np.zeros(len(data_bt))
    returns = np.zeros(len(data_bt))
    trading_cost = 0
    for i in range(len(data_bt)-1):
        if data_bt['pred'][i] == 1:
            positions[i] = 1
            returns[i] = (data_bt['close'][i+1]*(1-trading_cost)-data_bt['close'][i]*(1+trading_cost))/data_bt['close'][i]
        elif data_bt['pred'][i] == -1:
            positions[i] = -1
            returns[i] = (data_bt['close'][i]*(1-trading_cost)-data_bt['close'][i+1]*(1+trading_cost))/data_bt['close'][i]   
       
    returns = pd.Series(returns,index = data_bt.index)  
    
    return returns

### Backtest function
### It generates intra-day High/Low/Open/Close NAVs for a given trading strategy
def Backtest(data, signal) :
    data_bt = data.ix[:,:5]
    #data_bt['pred'] = signal
    #data_bt.index = data_bt.index.tz_localize('UTC')
    positions = np.zeros(len(data_bt))
    returns = np.zeros(len(data_bt))
    returns_open = np.zeros(len(data_bt))
    returns_high = np.zeros(len(data_bt))
    returns_low = np.zeros(len(data_bt))
    trading_cost = 0
    for i in range(len(data_bt)-1):
        if signal[i] == 1:
            positions[i] = 1
            returns[i] = (data_bt['close'][i+1]*(1-trading_cost)-data_bt['close'][i]*(1+trading_cost))/data_bt['close'][i]
            returns_open[i] = (data_bt['open'][i+1]*(1-trading_cost)-data_bt['close'][i]*(1+trading_cost))/data_bt['close'][i]
            returns_high[i] = (data_bt['high'][i+1]*(1-trading_cost)-data_bt['close'][i]*(1+trading_cost))/data_bt['close'][i]
            returns_low[i] = (data_bt['low'][i+1]*(1-trading_cost)-data_bt['close'][i]*(1+trading_cost))/data_bt['close'][i]
        elif signal[i] == -1:
            positions[i] = -1
            returns[i] = (data_bt['close'][i]*(1-trading_cost)-data_bt['close'][i+1]*(1+trading_cost))/data_bt['close'][i] 
            returns_open[i] = (data_bt['close'][i]*(1-trading_cost)-data_bt['open'][i+1]*(1+trading_cost))/data_bt['close'][i] 
            returns_high[i] = (data_bt['close'][i]*(1-trading_cost)-data_bt['high'][i+1]*(1+trading_cost))/data_bt['close'][i] 
            returns_low[i] = (data_bt['close'][i]*(1-trading_cost)-data_bt['low'][i+1]*(1+trading_cost))/data_bt['close'][i] 
       
    returns = pd.Series(returns,index = data_bt.index)  
    
    ### calculate high, low
    navs = pd.DataFrame();
    navs['close'] = (1+returns).cumprod()
    navs['open'] = navs['close'].shift(1) * (1+returns_open)
    navs['high'] = navs['close'].shift(1) * (1+returns_high)
    navs['low'] = navs['close'].shift(1) * (1+returns_low)
    
    return returns, navs
    
    
# In[2]
### Technical Indicator KDJ
def KDJ(data, n = 14, m = 3, l = 3, s = 3): 
    """
    data: original data with open,high,low,close,vol，amount
    
    """
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
    
    
    data['k'],data['d'],data['j'] = kdj(data,n,m,l,s)
    signal = pd.DataFrame(index=data.index) 
    
    #strategy 1
    """
    当K上穿30时或者上穿70，买入，信号为1
    当K下穿70时或者下穿30，卖空，信号为-1
    """
    signal['1'] = (((data['k'] >30) & (data['k'].shift(1) <30)) | ((data['k'] >70) & (data['k'].shift(1) <70)))*1 + (((data['k'] <30) & (data['k'].shift(1) >30)) | ((data['k'] <70) & (data['k'].shift(1) >70)))*(-1)
    signal['1'] = signal['1'][signal['1'].isin([1,-1])].reindex(data.index, method='ffill')    
    #strategy 2
    """
    当K上穿30时，买入，信号为1
    当K下穿70时，卖空，信号为-1
    当信号为1且K在70以下，K，D产生死叉，反向做空，信号改为-1
    当信号为-1且K在30以上，K，D产生金叉，反向做多，信号改为1
    当K大于70时，信号恒为1
    """
    signal['2'] = ((data['k'] >30) & (data['k'].shift(1) <30)) *1+((data['k'] <70) & (data['k'].shift(1) >70))*(-1)
    signal['2'] = signal['2'][signal['2'].isin([1,-1])].reindex(data.index, method='ffill')    
    
    #K,D金叉死叉
    kd = (data.k>data.d)*1
    uc_kd = ((kd == 1) & (kd.shift(1) == 0))*1
    dc_kd = ((kd == 0) & (kd.shift(1) == 1))*1
    
    signal['2'] = ((signal['2'] == 1) & (data['k'] < 70) & (dc_kd == 1))*(-2) +                   ((signal['2'] == -1) & (data['k'] > 30) & (uc_kd == 1))*(2) +                   ((data['k'] >30) & (data['k'].shift(1) <30)) *1+((data['k'] <70) & (data['k'].shift(1) >70))*(-1)
    signal['2'][signal['2'] > 0] = 1
    signal['2'][signal['2'] < 0] = -1
    #
    signal['2'] = signal['2'][signal['2'].isin([1,-1])].reindex(data.index, method='ffill')   
    signal['2'][data['k'] > 70] = 1
        
    signal = signal.fillna(0)
    return signal
    

# In[3]
### Technical Indicator ADX
def ADX(data, n = 14):
    """
    data: original data with open,high,low,close,vol
    n: timeperiod
    """
    data['adx'] = ta.ADX(np.array(data.high),np.array(data.low),np.array(data.close),n)#Average Directional Movement Index (Momentum Indicators)
    data['mdi'] = ta.MINUS_DI(np.array(data.high),np.array(data.low),np.array(data.close),n)
    data['pdi'] = ta.PLUS_DI(np.array(data.high),np.array(data.low),np.array(data.close),n)
    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    当+DI上穿-DI，买入，信号为1
    当+DI下穿-DI，卖空，信号为-1
    """
    signal['1'] = ((data['pdi']>data['mdi'])&(data['pdi'].shift(1)<data['mdi'].shift(1)))*1 + ((data['pdi']<=data['mdi'])&(data['pdi'].shift(1)<data['mdi'].shift(1)))*(-1)
    signal['1'] = signal['1'][signal['1'].isin([1,-1])].reindex(data.index, method='ffill') 
    signal = signal.fillna(0)
    return signal
    

# In[4]
### Technical Indicator Aroon
def AROON(data, d=15, up = 50, down = -50, up_up = 70, down_down = 50):
    """
    data: original data with open,high,low,close,vol
    d: days for calculation
    up and down: threshold for aroon
    up_up and down_down: threshold for aroon_up and aroon_down
    """
    
    data['aroon_dn'],data['aroon_up'] = ta.AROON(np.array(data.high),np.array(data.low),d)
    data['aroon'] = data['aroon_up']-data['aroon_dn']
    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    当 AROON_UP 上穿70，并且AROON>0，买入，信号为1
    当AROON_DN 上穿70，并且AROON<0，卖空，信号为-1
    当AROON_UP 下穿50，并且AROON<0，卖空，信号为-1
    当AROON_DN 下穿50，并且AROON>0，买入，信号为1
    参数为20 
    """   
    signal['1'] = ((data['aroon']>0)&\
                  (((data['aroon_up']>70)&(data['aroon_up'].shift(1)<70))|\
                  ((data['aroon_dn']<50)&(data['aroon_dn'].shift(1)>50))))*1+ \
                  ((data['aroon']<0)&(((data['aroon_dn']>70)&(data['aroon_dn'].shift(1)<70))|\
                  ((data['aroon_up']<50)&(data['aroon_up'].shift(1)>50))))*(-1)
    signal['1'] = signal['1'][signal['1'].isin([1,-1])].reindex(data.index, method='ffill') 
    #strategy 2
    """
    AROON 上穿50，买入，信号为1
    AROON 下穿-50，卖空，信号为-1
    测得的最优参数为15
    """      
    signal['2'] = ((data['aroon']> up)&(data['aroon'].shift(1)< up))*1+ \
                  ((data['aroon']< down)&(data['aroon'].shift(1)> down))*(-1)
    signal['2'] = signal['2'][signal['2'].isin([1,-1])].reindex(data.index, method='ffill') 
    signal = signal.fillna(0)
    return signal


# In[5]
### Technical Inidcator Bollinger Band
def BBANDS(data, n = 20, m = 2):
    data['bbands_mid'] = ta.SMA(np.array(data[['high', 'low', 'close']].mean(axis=1)),n)
    data['bbands_up'] =  data['bbands_mid'] + m* pd.rolling_apply(data.close, n, np.std)
    data['bbands_dn'] =  data['bbands_mid'] - m* pd.rolling_apply(data.close, n, np.std)
    signal = pd.DataFrame(index = data.index)
    """
    当收盘价上穿上轨线，买入，信号为1
    当收盘价下穿下轨线，卖空，信号为-1
    参数为20
    """
    signal['1'] = ((data['close'] > data['bbands_up'])&(data['close'].shift(1) < data['bbands_up'].shift(1)))*1 +                  ((data['close'] < data['bbands_dn'])&(data['close'].shift(1) > data['bbands_dn'].shift(1)))*(-1)
    signal['1'] = signal['1'][signal['1'].isin([1,-1])].reindex(data.index, method='ffill') 
    signal = signal.fillna(0)
    return signal

def CCI(data,n=20,m=7):  
    data['cci'] = ta.CCI(np.array(data.high),np.array(data.low),np.array(data.close),n)
    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    当 CCI 上穿100，买入，信号为1
    当CCI 下穿-100，卖空，信号为-1
    参数为20
    """
    signal['1'] = ((data['cci'] > 100)&(data['cci'].shift(1) < 100))*1 +                  ((data['cci'] < -100)&(data['cci'].shift(1) > -100))*(-1)
    signal['1'] = signal['1'][signal['1'].isin([1,-1])].reindex(data.index, method='ffill') 
    
    #strategy 2
    """
    CCI 指标上穿100 买入，信号为1
    当CCI 指标回到100，并距离前次上穿100 在m 天之内，我们卖出，信号为-1
    否则信号不变，直到下穿-100 才卖出
    下穿-100 情况同上。
    测得最优参数为n=20,m=8
    """
    signal['2'] = ((data['cci'] > 100)&(data['cci'].shift(1) < 100))*1 +                  ((data['cci'] < -100)&(data['cci'].shift(1) > -100))*(-1)
    signal['2'] = signal['2']+                  (((data['cci'] < 100)&(data['cci'].shift(1) > 100))&(pd.rolling_sum(signal['2'], m)>0))*(-1) +                  (((data['cci'] > -100)&(data['cci'].shift(1) < -100))&(pd.rolling_sum(signal['2'], m)<0))*1
    signal['2'] = signal['2'][signal['2'].isin([1,-1])].reindex(data.index, method='ffill')
    signal = signal.fillna(0)
    return signal

# In[6]
### Technical Indicator Chaikind AD
def CHAIKINAD(data, m = 14, n = 16):
    """
    s: 1-strategy 1;2-strategy 2;3-strategy 3
    [(Close  -  Low) - (High - Close)] /(High - Low) 
    """    
    data['ad'] = ta.AD(np.array(data.high),np.array(data.low),np.array(data.close),np.array(data.vol))
    data['adosc'] = ta.ADOSC(np.array(data.high),np.array(data.low),np.array(data.close),np.array(data.vol),m,n)
    data['adosc_ma'] = ta.SMA(np.array(data.ad),m)-ta.SMA(np.array(data.ad),n)#(14,16)   
    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    AD上升，买入，信号为1
    AD下降，卖出，信号为-1
    """
    signal['1'] = (data['ad']>data['ad'].shift(1))*2 - 1
    
    #strategy 2
    """
    当CHAIKIN上穿0轴，买入，信号为1
    当CHAIKIN下穿0轴，卖空，信号为-1
    日最优参数：9，13，周最优参数：5，6
    """
    signal['2'] = ((data['adosc'] > 0)&(data['adosc'].shift(1) < 0))*1 +                  ((data['adosc'] < 0)&(data['adosc'].shift(1) > 0))*(-1)
    signal['2'] = signal['2'][signal['2'].isin([1,-1])].reindex(data.index, method='ffill')
    
    #strategy 3
    """
    用简单移动平均线来替代指数移动平均线
    """
    signal['3'] = ((data['adosc_ma'] > 0)&(data['adosc_ma'].shift(1) < 0))*1 +                  ((data['adosc_ma'] < 0)&(data['adosc_ma'].shift(1) > 0))*(-1)
    signal['3'] = signal['3'][signal['3'].isin([1,-1])].reindex(data.index, method='ffill')
    
    signal = signal.fillna(0)
    return signal

#%%
# Technical Indicator CMO
def CMO(data,n = 14,m = 0):
    data['cmo'] = ta.CMO(np.array(data.close),n)
    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    CMO 大于0, 买入，信号为1
    CMO 小于0，卖出，信号为-1
    常用参数14
    最优参数12
    """
    signal['1'] = (data['cmo']>0)*1+(data['cmo']<0)*(-1)
    
    #strategy 2
    """
    CMO 大于m, 买入，信号为1
    CMO 小于-m，卖出，信号为-1
    """
    signal['2'] = (data['cmo']> m)*1+(data['cmo']< -m)*(-1)
    signal = signal.fillna(0)
    return signal

#%%
### 
def EMV(data,n=20,m=23):
    """
    """
    def emv(high,low,vol,n=14):
        MID = np.zeros(len(high))  
        MID[1:] = (np.array(high[1:])+np.array(low[1:])-np.array(high[:-1])-np.array(low[:-1]))/2.
        BRO = np.array(vol)/(100000000.*(np.array(high)-np.array(low)))
        EM = MID/BRO
        return ta.SMA(EM,n)
    data['emv'] = emv(np.array(data.high),np.array(data.low),np.array(data.vol),n)
    data['maemv'] = ta.SMA(np.array(data['emv']),m)

    signal = pd.DataFrame(index=data.index)
    
    #strategy 1
    """
    EMV 大于0，买入，信号为1
    EMV 小于0，卖出，信号为-1
    常用参数：n=14
    """
    signal['1'] = (data['emv']>0)*2 - 1
    
    
    #strategy 2
    """
    EMV 大于MAEMV，买入，信号为1
    EMV 小于MAEMV，卖出，信号为-1
    参数设为n=20，m=23
    """
    signal['2'] = (data['emv'] > data['maemv'])*2 - 1
    signal = signal.fillna(0)
    return signal
    

