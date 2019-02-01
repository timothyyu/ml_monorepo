
import pandas as pd
import numpy as np
import talib as ta
from ML.Tools import *
import scipy.stats as stats
from numpy import *



def next_day_log_ratio(df) :
    v = 25000 * np.log(df['open'].shift(-2) / df['open'].shift(-1))
    ndlr = pd.DataFrame(data=np.array(v), index=df.index, columns=['ndlr'])
    return ndlr

def next_day_atr_return_distance(df, win=250):
    delta_o = np.array(df['open'].shift(-2) - df['open'].shift(-1))
    atr = ta.ATR(df['high'].values, df['low'].values, df['close'].values, 250)
    v = delta_o / atr

    ndard = pd.DataFrame(data=v, index=df.index, columns=['ndard'])
    return ndard


# 1-day log return
def log_return(df) :
    df_price = np.log(df[['close']])
    l_ret = df_price - df_price.shift(1)
    return pd.DataFrame(data=l_ret.values, index=df.index, columns=['logret'])

'''
Direction of the past returns of the timeseries. If ret(0) > 0, direction = 1.
else direction = 0.
histLen specified the days back to compare
'''
def direction(df, histLen=1) :
    df_price = df[['close']]
    df_dir = (df_price > df_price.shift(histLen)) * 1
    df_dir[:(histLen-1)] = np.nan
    return pd.DataFrame(data=df_dir.values, index=df.index, columns=['direction_{n}'.format(n=histLen)])


# n-day close to close (log return)
def close_to_close(df, histLen=5) :
    df_price = df['close']
    return np.log(df_price / df_price.shift(histLen))



'''
Bollinger_Bandwidth: the ratio between rolling standard deviation of the Close price, and rolling mean of
the close price. The ratio will then take logarithmic function.
'''
def bollinger_bandwidth(df, histLen=10) :
    df_std = pd.rolling_std(df['close'], histLen)
    df_mean = pd.rolling_mean(df['close'], histLen)
    v_bb = np.log(df_std.values / df_mean.values)
    return pd.DataFrame(data=v_bb, index=df.index, columns=['bollinger_bw_{m}'.format(m=histLen)])



'''
Delta of a timeseries
'''
def delta(df_v, shiftLen=10) :
    name = df_v.columns[0]
    df_1 = df_v[name]
    df_delta = df_v - df_v.shift(shiftLen)
    return pd.DataFrame(data=df_delta.values, index=df.index,
                        columns=['delta_{m}_{s}'.format(m=shiftLen, s=name)])


# Moving Average
def sma(df, maLen=10) :
    if maLen == 1:
        l_sma = df[['close']].values
    else:
        l_sma = ta.SMA(df['close'].values, maLen)
    return pd.DataFrame(data=l_sma, index=df.index, columns=['ma_{n}'.format(n=maLen)])


def close_ma_ATR_log(df, histLen = 5, atrLen = 30) :
    # Close - MovingAverage
    # Normlaized by Log ATR
    df_price = df[['close']]
    df_ma = sma(df, histLen)
    df_atr = ATR(df, atrLen)

    v1 = np.log(df_price.values / df_ma.values) #/ np.sqrt(histLen)
    v2 =  np.log(df_atr.values)
    v = v1/v2

    return pd.DataFrame(data=v, index=df.index, columns=['cmatr_{n}_{m}'.format(n=histLen, m=atrLen)])


def ma_diff_ATR_log(df, shortLen = 5, longLen = 51, lag = 5) :
    # MA different, normalized by ATR
    # Params: ShortLen, LongLen, Lag
    # ShortLen - the lenght for the short MA
    # longLen - the length for the long MA
    # lag - the long MA will apply with a lag. If the lag >= shortLen, the long and the short MA
    # will by apply for the 2 separated windows
    # The delta of the 2 MAs will be normalized with the ATR with len = Lag + LongLength
    df_short_ma = sma(df, shortLen)
    df_long_ma = sma(df, longLen).shift(lag)
    df_atr = ATR(df, longLen + lag)

    delta = np.log(df_short_ma.values) - np.log(df_long_ma.values)

    o = delta / np.log(df_atr.values)
    return pd.DataFrame(data=o, index=df.index, columns=['mdatr'])

def ma_diff_ATR(df, shortLen = 5, longLen = 51, lag = 5) :
    df_short_ma = sma(df, shortLen)
    df_long_ma = sma(df, longLen).shift(lag)
    df_atr = ATR(df, longLen + lag)

    delta = df_short_ma.values - df_long_ma.values
    o = delta / df_atr.values
    return pd.DataFrame(data=o, index=df.index, columns=['mdatr'])


'''
Line Per ATR
calcuate the least-square deviation line of the data - using the
mean(sum(high+low+open+close)) with the window. the slope of the line divided
by the ATR.
parameters
- histLen - window for the slope estimation
- atrLen - ATR window
output:
DataFrame containing two columns
- 'lpatr' line slope adjusted by ATR
- 'slope_predict' the next day predict using the line slope
- 'delta_predict' the different betweeen the predict and the close price
'''
def line_per_atr(df, histLen = 50, atrLen = 200) :
    l_mean = df[['open', 'high','low', 'close']].mean(axis=1)
    nr = len(l_mean)

    l_slope = []
    l_predict = []
    l_delta = []

    # sklearn linear model
    from sklearn import linear_model
    regr = linear_model.LinearRegression()

    for i in range(nr) :
        if i < histLen:
            l_slope.append(np.nan)
            l_predict.append(np.nan)
            l_delta.append(np.nan)
        else :
            y = np.reshape(l_mean[(i-histLen):i].values, [histLen, 1])
            x = np.reshape(np.arange(histLen), [histLen, 1])
            regr.fit(x,y)
            slope = regr.coef_[0,0]
            l_slope.append(slope)
            l_predict.append(l_mean[i] + slope)

    df_atr = ATR(df, atrLen)

    df_slope = pd.DataFrame(data=l_slope, index=df.index, columns=['slope'])
    df_slope['lpatr'] = l_slope / df_atr.values.ravel()
    #df_slope['close'] = df['Close']
    df_slope['slope_predict'] = l_predict
    df_slope['delta_predict'] = df_slope['slope_predict'].shift(1) - df['close']

    df_slope.columns = ['slope_{m}'.format(m=histLen),
                        'lpatr_{m}_{n}'.format(m=histLen, n=atrLen),
                       'predict_{m}'.format(m=histLen),
                       'delta_predict_{m}'.format(m=histLen)]
    return df_slope


# ATR
def ATR(df, atrLen = 10):
    import talib as ta
    l_atr = ta.ATR(df['high'].values, df['low'].values, df['close'].values, atrLen)
    return pd.DataFrame(data=l_atr, index=df.index, columns=['atr_{n}'.format(n=atrLen)])

def atr_per_close(df, atrLen = 10) :
    a = ATR(df, atrLen)
    l = a / df[['close']].values
    return pd.DataFrame(data=l.values, index=df.index, columns=['atr_per_close_{n}'.format(n=atrLen)])



def ATRRatio(df, shortLen=10, longLen=20) :
    '''
    ATR Ratio - the ratio between the short ATR and the long ATR
    '''
    df_atr_short = ATR(df, shortLen)
    df_atr_long = ATR(df, longLen)
    v_atr_ratio = df_atr_short.values / df_atr_long.values

    return pd.DataFrame(data=v_atr_ratio, index=df.index, columns=['ATR_Ratio_{n}/{m}'.format(n=shortLen, m=longLen)])

def DeltaATRRatio(df, shortLen=10, longLen=20, n=5):
    '''
    DeltaATRRatio: The delta between ATRRatio now and the ATRRatio n bars ago
    :param df:
    :param shortLen:
    :param longLen:
    :param n: n bars between now and the past
    :return:
    '''
    atr_0 = ATRRatio(df, shortLen, longLen)
    atr_n = atr_0.shift(n)
    delta = atr_0 - atr_n
    return pd.DataFrame(data=delta.values, index=df.index,
                        columns=['Delta_ATR_Ratio_{n}/{m}_{t}'.format(n=shortLen, m=longLen, t=n)])


def RSI(df, field='open', histLen=3) :
    df_price = df[field]
    lst_rsi = ta.RSI(df_price.values, histLen)
    return pd.DataFrame(data=lst_rsi, index=df.index, columns=['rsi_{n}'.format(n=histLen)])



def Trend(df, histLen=50) :
    sma = ta.SMA(df['open'], histLen)
    delta =  df['open'].values - sma
    return pd.DataFrame(data=delta, index=df.index, columns=['trend_open_sma_{n}'.format(n=histLen)] )

def Trend(data, length = 10) :
    sma = ta.SMA(data, length)
    delta = data - sma


def Momentum(data, length = 10) :
    '''
    Momentum - The price difference in n days, standardized by the volatility
    (close_0 - close_n)/stdev(close, n)
    :param df:
    :param length:
    :return:
    '''
    delta = ta.MOM(data, length)
    stdev = ta.STDDEV(data, length)

    return delta / stdev

def TrendDeviation(data, length = 10) :
    '''
    TrendDeviation - the logarithm of ( closeing price / the lowpass filtered price)
    :param data:
    :param length:
    :return:
    '''
    lp = TrendIndicators.LowPass(data, length)
    return log(data/ lp)


class CycleIndicator():

    @staticmethod
    def ExtremePoints(data):
        '''
        ExtremePoints - determine the peak and the valleys of a timeseries
        Peak is defined as a data point data[t] > data[t-1], and data[t] > data[t+1]
        Valley is defined as a data point data[t] < data[t-1], and data[t] < data[t-1]

        In the function, we calculate peaks and valleys at time t, with data[t-1], data[t]
        and data[t+1]. CAUTION: the peaks and valleys at time t, can only be calculated
        by time t+1, as we use the data[t+1]. Therefore, when we use the peaks and valleys
        generated by this function, we should shift the time series one time lag forward, so
        that no forward-looking bias should be included.

        Normally, to use ExtremePoints on the price will generate lots of peaks and valleys, due
        to the noisy nature of the price. One good practice is to first use trend-smoothing functions
        such as SMA/EMA and various other trend indicators to smooth the price data, and then use
        the functions to determine the peak/valleys on the trend.
        '''
        valley = np.zeros(data.shape)
        peak = np.zeros(data.shape)
        pos_reversal = np.zeros(data.shape)
        pos_trend = np.zeros(data.shape)

        for i in range(len(data)) :
            if i < 1:
                continue
            if i >= (len(data) - 1):
                continue

            if (data[i] > data[i-1]) and (data[i] > data[i+1]) :
                peak[i] = 1
                pos_reversal[i] = 0
                pos_trend[i] = 1
            elif (data[i] < data[i-1]) and (data[i] < data[i+1]) :
                valley[i] = 1
                pos_reversal[i] = 1
                pos_trend[i] = 0
            else :
                pos_reversal[i] = pos_reversal[i-1]
                pos_trend[i] = pos_trend[i-1]


        return peak, valley, pos_reversal, pos_trend

    @staticmethod
    def DochianChannel(data, period = 100):
        high = ta.MAX(data, period)
        low = ta.MIN(data, period)
        return high, low

    @staticmethod
    def MMI(data, period = 100) :
        '''
        MMM - Market Meanness Index
        :param data:
        :param period: nsarray
        :return:
        '''


        mmi = np.zeros(data.shape)
        for i in range(len(data)) :
            if i < period - 1:
                continue

            m = np.median(data[(i-period + 1):i])
            nl = 0
            nh = 0
            for j in range(period-1):
                if j < 1:
                    continue
                if (data[i-j] > m) and (data[i-j] > data[i-j-1]) :
                    nl += 1
                if (data[i-j] < m) and (data[i-j] < data[i-j-1]) :
                    nh += 1
            mmi[i] = 100.0 * (nl+nh)/(period -1 )

        return mmi

    @staticmethod
    def MMIDeviation(data, period = 100, n = 10):
        '''
        MMMDeviation = MMI_now - MMI_ndays_ago
        :param data:
        :param period:
        :param n: days ago to compare
        :return:
        '''
        mmi_0 = CycleIndicator.MMI(data, period)
        mmi_de = np.zeros(mmi_0.shape)
        from scipy.ndimage.interpolation import shift
        mmi_n = shift(mmi_0, n, cval=np.NAN)
        for i in range(len(mmi_de)):
            if i < n - 1:
                continue
            mmi_de[i] = mmi_0[i] - mmi_0[i - n]
        return mmi_de

    @staticmethod
    def Hurst(data, period = 100) :
        from numpy import cumsum, log, polyfit, sqrt, std, subtract
        def hurst(ts):
            """Returns the Hurst Exponent of the time series vector ts"""
            # Create the range of lag values
            if 50 <= len(ts)  :
                n = 50
            else:
                n = len(ts)
            lags = range(2, 100)

            # Calculate the array of the variances of the lagged differences
            tau = [sqrt(std(subtract(ts[lag:], ts[:-lag]))) for lag in lags]

            # Use a linear fit to estimate the Hurst Exponent
            poly = polyfit(log(lags), log(tau), 1)

            # Return the Hurst exponent from the polyfit output
            return poly[0]*2.0



        h = np.ones(data.shape) * 0.5
        for i in range(len(data)) :
            if i < period - 1:
                continue

            h[i] = hurst(data[(i-period+1):i])
        return h

class TrendIndicators():
    import numpy as np

    @staticmethod
    def get_indicators(df, names=[], periods=[]):
        data = df.iloc[:, 0].values.ravel()

        df_output = pd.DataFrame(data=data, index=df.index, columns=['data'])

        for n in names:
            for p in periods:
                try :
                    method = getattr(TrendIndicators, n)
                    df_output['{a}_{b}'.format(a=n, b=p)] = method(data, p)
                except:
                    print "cannot find method[{n}]".format(n=n)
                    continue
        return df_output


    @staticmethod
    def DecyclerOsc(data, HPPeriod1=30, HPPeriod2 = 60) :
        nr = len(data)
        # Close = df[['close']].values

        alpha1 = (np.cos(0.707*2*np.pi / HPPeriod1) + np.sin(0.707*2*np.pi/ HPPeriod1) - 1) / np.cos(0.707*2*np.pi/HPPeriod1)
        alpha2 = (np.cos(0.707*2*np.pi / HPPeriod2) + np.sin(0.707*2*np.pi/ HPPeriod2) - 1) / np.cos(0.707*2*np.pi/HPPeriod2)

        HP1 = np.zeros(data.shape)
        HP2 = np.zeros(data.shape)

        for i in range(nr):
            if i < 2:
                continue
            else :
                HP1[i] = (1 - alpha1/2) * (1-alpha1/2)* (data[i] - 2 * data[i - 1] + data[i - 2]) + \
                        2*(1 - alpha1) * HP1[i-1] - (1 - alpha1) * (1 - alpha1) * HP1[i-2]
                HP2[i] = (1 - alpha2/2) * (1-alpha2/2)* (data[i] - 2 * data[i - 1] + data[i - 2]) + \
                        2*(1 - alpha2) * HP2[i-1] - (1 - alpha2) * (1 - alpha2) * HP2[i-2]
        Decycle = HP2 - HP1
        # df_decycle = pd.DataFrame(data = Decycle, index=df.index, columns=['decycle_osc'])
        # df_decycle['decycle_hp1'] = HP1
        # df_decycle['decycle_hp2'] = HP2
        # df_decycle['close'] = close
        return Decycle

    @staticmethod
    def Decycler(data, cutoff = 60) :
        '''
        Based on John Ehler's Decycler Algorithm.
        This indicator is a high-pass filter, filtering out the cycle periods < cutoff
        '''
        alpha1 = (np.cos(2*np.pi/cutoff) + np.sin(2*np.pi/cutoff) - 1) / np.cos(2*np.pi/cutoff)
        # Close = df[['close']].values
        decycle = np.zeros(data.shape)

        for i in range(len(decycle)) :
            if i < 1:
                continue
            else :
                decycle[i] = (alpha1 / 2) * (data[i] + data[i - 1]) + (1 - alpha1) * decycle[i - 1]

        # df_decycler = pd.DataFrame(data=decycle, index=df.index, columns=['decycler'])
        #df_decycler['close'] = df[['close']]
        return decycle

    @staticmethod
    def ZMA(data, period = 100):
        '''
        ZMA - Ehler's Zero-lag Moving Average, an EMA with a correction term for removing lag.
        http://www.financial-hacker.com/trend-delusion-or-reality/
        '''
        # close = df[['close']].values.ravel()
        a = 2.0 / (1 + period)
        ema = ta.EMA(data, period)
        error = 10000000
        gain = 5
        gain_limit = 5
        best_gain = 0

        zma = np.zeros(data.shape)
        for i in range(len(zma)):
            if i < period - 1:
                continue
            else:

                gain = -gain_limit
                while gain < gain_limit:
                    gain += 0.1
                    zma[i] = a * (ema[i] + gain * (data[i] - zma[i - 1])) + (1 - a) * zma[i - 1]
                    new_error = data[i] - zma[i]
                    if np.abs(error) < new_error:
                        error = np.abs(new_error)
                        best_gain = gain

                zma[i] = a * (ema[i] + best_gain * (data[i] - zma[i - 1])) + (1 - a) * zma[i - 1]

        # df_zma = pd.DataFrame(data=zma, index=df.index, columns=['zma_{i}'.format(i=period)])
        return zma

    @staticmethod
    def ALMA(data, period=100) :
        '''
        ALMA - Arnaud Legoux Moving Average,
        http://www.financial-hacker.com/trend-delusion-or-reality/
        '''
        # data = df[['close']].values.ravel()
        m = np.floor(0.85 * (period - 1))
        s = period  / 6.0
        alma = np.zeros(data.shape)
        w_sum = np.zeros(data.shape)

        for i in range(len(data)):
            if i < period - 1:
                continue
            else:
                for j in range(period):
                    w = np.exp(-(j-m)*(j-m)/(2*s*s))
                    alma[i] += data[i - period + j] * w
                    w_sum[i] += w
                alma[i] = alma[i] / w_sum[i]

        # df_alma = pd.DataFrame(data=alma, index=df.index, columns=['alma_{i}'.format(i=period)])
        return alma

    @staticmethod
    def LowPass(data, period = 100):
        '''
        LowPass filter - John Elher's smoothing filter to get the trend of the time series
        '''
        # close = df[['close']].values.ravel()
        a = 2.0 / (1+period)
        lp = data.copy()

        for i in range(len(data)) :
            if i < 2:
                continue
            else :
                lp[i] = (a - 0.25*a*a) * data[i] \
                    + 0.5*a*a * data[i - 1] \
                    - (a-0.75*a*a) * data[i - 2] \
                    + 2*(1.0-a)*lp[i-1] \
                    - (1.0 -a)*(1.0 -a)*lp[i-2]
        # df_lp = pd.DataFrame(data=lp, index=df.index, columns=['lp_{i}'.format(i=period)])
        return lp

    @staticmethod
    def SuperSmooth(data, period=50) :
        '''
        SuperSmooth - proposed by John Ehler to get rid of undersample noise.
        '''
        # close = df[['close']].values.ravel()
        f = (1.414*np.pi)/period
        a = np.exp(-f)
        c2 = 2 * a * np.cos(f)
        c3 = - a*a
        c1 = 1 - c2 - c3

        ss = np.zeros(data.shape)
        for i in range(len(data)) :
            if i < 2:
                continue
            else :
                ss[i] = c1 * (data[i] + data[i - 1]) * 0.5 + c2 * ss[i - 1] + c3 * ss[i - 2]
        # df_ss = pd.DataFrame(data=ss, index=df.index, columns=['ss_{i}'.format(i=period)])
        return ss

    @staticmethod
    def ImpluseTest(period = 50):

        impluse = np.concatenate((np.zeros([200,1]), np.ones([100,1]), np.zeros([20,1]), np.ones([5,1]), np.zeros([200,1])), axis=0)
        df_im = pd.DataFrame(data=impluse, columns=['close'])
        df_lp = TrendIndicators.LowPass(df_im, period)
        df_lp['close'] = df_im['close']
        df_lp = df_lp.join(TrendIndicators.ALMA(df_im, period))
        # df_lp = df_lp.join(ZMA(df_im, period))
        #df_lp['EMA'] = ta.EMA(df_im['close'].values.ravel(), period)
        df_lp = df_lp.join(TrendIndicators.SuperSmooth(df_im, period))
        df_lp = df_lp.join(TrendIndicators.Decycler(df_im, period))
        df_lp.plot(figsize=[20,10])



class NormalityTest():

    @staticmethod
    def KStest(data, period=100, side='two-sided') :
        '''
        KStest - Kolmogrov Smirnov Tests
        :parameter side - "two-sided", "less", "greater"

        '''
        k = np.zeros(len(data))
        p = np.zeros(len(data))

        for i in range(len(data)) :
            if i < period - 1:
                continue
            data_in = data[(i-period+1):i]
            k[i], p[i] = stats.kstest(data_in, cdf='norm', alternative=side)

        return k, p

    @staticmethod
    def ShapiroTest(data, period =100) :
        '''
        ShapiroTest - Testing  distribution normality
        '''
        s = np.zeros(len(data))
        p = np.zeros(len(data))

        for i in range(len(data)):
            if i < period - 1:
                continue

            data_in = data[(i-period+1):i]
            s[i], p[i] = stats.shapiro(data_in)
        return s, p

    @staticmethod
    def ADFTest(data, period = 100) :
        stats = np.zeros(data.shape)
        pvalue = stats.copy()
        half_life = stats.copy()

        for i in range(len(data)) :
            if i < period - 1:
                continue
            data_in = data[(i-period+1):i]

            stats[i], pvalue[i], half_life[i] = adf(data_in)
        return stats, pvalue, half_life




from Data.TimeSeries import *
from Data.StockDataManager import  *

if __name__  == "__main__" :
    tickers = ['GOOG/NYSE_SPY']

    settings = Settings()
    dp = TimeSeries(settings).get_ETF_data(tickers)

    df = dp[tickers[0]][['Open', 'High', 'Low', 'Close', 'volume']].dropna()

    df.columns = ['open', 'high', 'low', 'close', 'volume']

    #TrendIndicators.ImpluseTest(50)
    names_ind = ['SuperSmooth', 'ZMA', 'ALMA', 'LowPass' ]
    periods = [20, 50]
    a = TrendIndicators.get_indicators(df[['close']], names_ind,  periods)

    print 'done!'