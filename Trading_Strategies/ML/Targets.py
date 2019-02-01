import numpy as np
import pandas as pd
import talib as ta
import math
from Features import *
from sklearn.metrics import fbeta_score

'''
calcualte the open-to-open log return ,
set as target
'''
def target_log_return(df) :
    df_logret = log_return(df)

    # at the end of the day, we need to know the log ret between open at day 1 and day 2
    # we now have the logret(0) as log ret of open at day -1 and day 0.
    # therefore we need to shift the timeseries 2 days into the fture.
    df_logret = df_logret.shift(-2) # shift the logret 2 days into the future.

    return pd.DataFrame(data=df_logret.values, index=df.index, columns=['t_logret'])

def target_direction(df, len=1) :
    df_dir = direction(df, len)
    df_dir = df_dir.shift(-1)
    return pd.DataFrame(data=df_dir.values, index=df.index, columns=['t_direction_{n}'.format(n=len)])

def target_valley_top(df, len=100) :
    vall


'''
Open-to-open log return , standardized by ATR
'''
def log_return_std_by_atr(df, atrLen = 30) :
    df_logret = log_return(df)

    df_atr = ATR

def next_day_atr_return_distance(df, win=250):
    delta_o = np.array(df['open'].shift(-2) - df['open'].shift(-1))
    atr = ta.ATR(df['high'].values, df['low'].values, df['close'].values, win)
    if win == 1:
        v = delta_o
    else :
        v = delta_o / atr

    ndard = pd.DataFrame(data=v, index=df.index, columns=['ndard'])
    return ndard

def subsequent_day_atr_return_distance(df, seq, win=250) :
    n = next_day_atr_return_distance(df, win)
    n_s = n.shift(-1*seq)
    col_new = 'ndard_{s}'.format(s=seq)
    n_s.columns = [col_new]
    return n_s

def next_month_atr_return_distance(df, win = 250):
    df_o = df.copy()

    ## get the first trading day of the month
    b = df_o.index[0:(len(df_o)- 1)]
    b = b.insert(0, df_o.index[0])
    a = df_o.index

    ## get the delta of opening price, between month(1) and month(2)
    df_f_month = df_o.loc[a[a.month <> b.month]]
    df_f_month['delta_o'] = np.array(df_f_month['open'].shift(-1) - df_f_month['open'])

    df_o['delta_o'] = df_f_month['delta_o']
    df_o = df_o.fillna(method='bfill')
    df_o['delta_o'] = df_o['delta_o'].shift(-1)

    ## get ATR in the window
    df_o['atr'] = ta.ATR(df_o['high'].values, df_o['low'].values, df_o['close'].values, win)
    if win == 1:
        v = df_o['delta_o']
    else :
        v = df_o['delta_o'] / df_o['atr']

    nmatd = pd.DataFrame(data=v, index=df_o.index, columns=['nmatd'])
    return nmatd

def hit_or_miss_up_down_cutoff_atr(df, up=2, down=5, cutoff = 40, atrdist=250):
    list_up_down = []

    price = df['open']
    for i in range(len(price)) :
        if i > len(price) - cutoff - 1:
            list_up_down.append(0)
        else :
            price_co = price[(i+1):(i+1+cutoff)]
            v_max = max(price_co)
            v_min = min(price_co)

            i_max = price_co.argmax()
            i_min = price_co.argmin()

            # check the upper bound
            atr = df_o['atr'][i]
            max_reach = 0
            min_reach = 0

            if (v_max - price_co[0]) > up * atr:
                max_reach = 1
            if (price_co[0] - v_min) > down * atr:
                min_reach = 1

            # normalize the returns with ATR
            if math.isnan(atr) :
                up_down = np.NAN
            else:

                if atr <> 0:
                    up_down = (price_co[-1] - price_co[0]) / atr
                else :
                    up_down = price_co[-1] - price_co[0]


                if max_reach == 1 and min_reach == 0:
                    up_down = up
                elif min_reach == 1 and max_reach == 0:
                    up_down = -1 * down
                elif max_reach == 1 and min_reach == 1:
                    if i_max > i_min:
                        up_down = up
                    if i_max < i_min:
                        up_down = -1*down
    #             else :
    #                 print "max/min no reaches"
    #                 print "max_reach={a}:min_reach={b}".format(a=max_reach, b=min_reach)
    #                 print "price_0={a}:price_1={b}".format(a=price_co[0], b=price_co[-1])
    #                 print "up_ratio = {a}".format(a = (v_max - price_co[0])/atr)
    #                 print "down_ratio = {a}".format(a = (price_co[0] - v_min)/atr)


            list_up_down.append(up_down)
    #         print "max={max}:min={min}:price={price}:atr={atr}:hit={hit}".format(
    #                 max=v_max, min=v_min, price=price[i], atr=atr, hit=up_down
    #             )
    #         print "---------------------------------------------------------------"

    hmatr = pd.DataFrame(data=list_up_down, index=df.index, columns=['hmatr'])
    return hmatr


