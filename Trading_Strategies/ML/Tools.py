import numpy as np
import scipy as sc
import pandas as pd
from scipy.stats import norm
import talib as ta



def iqr(data) :
    q25 = np.percentile(data, q=25)
    q75 = np.percentile(data, q=75)
    return abs(q75 - q25)


def scaling(data, win):
    return data / pd.rolling_apply(data, window=win, func=iqr)


def centering(data, win):
    return data - pd.rolling_median(data, win)


def Normalization(data, length = 100):
    v = np.zeros(data.shape)

    for i in range(len(data)) :
        if i < length:
            continue

        data_in = data[(i-length+1):i]
        i_start = i - length + 1
        delta =  data[i] - np.median(data_in)
        iqr = iqr(data_in)
        v[i] = 100 * norm.cdf(0.5 * delta / iqr) - 50
    return v

def RegularNormalization(data, length = 100):
    max = ta.MAX(data, length)
    min = ta.MIN(data, length)
    return (data - min) / (max - min) * 100 - 50

def ZScore(data, length = 100) :
    me = ta.SMA(data, length)
    st = ta.STDDEV(data, length)
    return (data - me) / st

def adf(x):
    """
    adf(x) - Calculate adf stat, p-value and half-life of the given list. This test will tell us if a
             time series is mean reverted.
             e.g. adf(prices)
    :param x: A pandas.Series of data.
    :return: (stat, p_value, half_life)
    Reference
        http://statsmodels.sourceforge.net/devel/generated/statsmodels.tsa.stattools.adfuller.html
        http://en.wikipedia.org/wiki/Augmented_Dickey%E2%80%93Fuller_test
    """
    # Calculate ADF to get ADF stats and p-value
    result = ts.adfuller(x)

    # Calculate the half-life of reversion
    price = pd.Series(x)
    lagged_price = price.shift(1).fillna(method="bfill")
    delta = price - lagged_price
    beta = np.polyfit(lagged_price, delta, 1)[0] #Use price(t-1) to predicate delta.
    half_life = (-1*np.log(2)/beta)
    return result[0], result[1], half_life

from Data.StockDataManager import *
from Data.TimeSeries import *

if __name__  == "__main__" :
    tickers = ['GOOG/NYSE_SPY']

    settings = Settings()
    dp = TimeSeries(settings).get_agg_ETF_data(tickers)
    df = dp[:, :,'price']

    #df.plot(figsize=[20,12])
    n = df.copy()
    # n['scaling'] = scaling(df, 50)
    # n['centering'] = centering(df, 50)
    n['normalization'] = Normalization(df.values, 50)
    n['regnormal'] = RegularNormalization(df.values, 50)
    n.plot()
    print 'done!'

