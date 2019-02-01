import odo
import pandas as pd
import matplotlib


def GetOneSideVolatility(data, n_vol = 20, n_ma = 60) :
    """ calculate the positive and negative volatility. For example, when calculating
        positive volatility, the function replaces negative data as 0.
    :param data: Pandas Serie containing the data to be process
    :param n_vol: The size of the rolling window for volatility calculation. By default 20
    :return: A dict
         - positive/negatie vol
         - delta_vol = (positive - negative)
         - MA_delta_vol
         - signal_cross (when delta_vol upcross MA, signal_cross = 1, else = -1)
         - signal_ma (when MA_delta_vol > 0, signal_ma = 1, else = -1)
    """

    df = data.to_frame('data')
    df['po_data'] = (df['data'] > 0) * df['data']
    df['ne_data'] = (df['data'] < 0) * df['data']

    df['po_std'] = pd.rolling_std(df['po_data'], n_vol)
    df['ne_std'] = pd.rolling_std(df['ne_data'], n_vol)

    df['delta_std'] = df['po_std'] - df['ne_std']
    df['ma_delta_std'] = pd.rolling_mean(df['delta_std'], n_ma)

    df = df.dropna()
    return df

def AbsoluteVol(data, n_ma=60) :
    df = data
    df['po_std'] = df['High'] - df['Open']
    df['ne_std'] = df['Open'] - df['Low']
    df['delta_std'] = df['po_std'] - df['ne_std']
    df['ma_delta_std'] = pd.rolling_mean(df['delta_std'], n_ma)

    df = df.dropna()
    return df


def RPS(price, n_days = 250, n_ma = 10) :
    """
    :param price: the value to calculate RPS
    :param n_days: number of days for 1 year
    :param n_ma: number of days for moving average
    :return:
        value: RPS
        ma: moving average of RPS
    """
    spread = price - price.shift(n_days)
    max_price = pd.rolling_max(price, n_days)
    min_price = pd.rolling_min(price, n_days)

    rps = pd.DataFrame()
    rps['value'] = (price - min_price) / (max_price - min_price)
    rps['ma'] = pd.rolling_mean(rps['value'], n_ma)
    return rps


def PosNegVolatilityStrategy(df_price, n_vol=20, n_ma=60) :
    df_spread = df_price['Close'] - df_price['Open']

    # calculate the returns
    df_ret_co = df_price['Close'] / df_price['Open'] -1
    df_ret_cc = df_price['Close'] / df_price['Close'].shift(1) -1
    df_ret_oo = df_price['Open'] / df_price['Open'].shift(1) - 1
    df_ret_oc = df_price['Open'] / df_price['Close'].shift(1) - 1

    # calculate the vol
    df_spread_vol = AbsoluteVol(df_price, n_ma)
    #df_ret_co_vol = GetOneSideVol(df_ret_co, n_ma)

    # strategy 1: using the daily Close-Open spread
    signal = pd.DataFrame()
    signal['ma'] = (df_spread_vol['ma_delta_std'] > 0) * 1 \
    #    + (df_spread_vol['ma_delta_std'] < 0) * -1
    signal['cross'] = (df_spread_vol['delta_std'] > df_spread_vol['ma_delta_std']) * 1 \
    #    +  (df_spread_vol['delta_std'] < df_spread_vol['ma_delta_std']) * -1

    ret = pd.DataFrame()
    ret.index.tz = None
    ret['cc'] = df_ret_cc
    ret['oo'] = df_ret_oo
    ret['co'] = df_ret_co
    ret['oc'] = df_ret_oc
    ret['cross_cc'] = signal['cross'].shift(1) * df_ret_cc
    ret['cross_co'] = signal['cross'].shift(1) * df_ret_co
    ret['cross_oo'] = signal['cross'].shift(1) * df_ret_oo
    ret['ma_cc'] = signal['ma'].shift(1) * df_ret_cc
    ret['ma_co'] = signal['ma'].shift(1) * df_ret_co
    ret['ma_oo'] = signal['ma'].shift(2) * df_ret_oo
    ret = ret.dropna()
    return ret

def RPSStrategy(df_price, n_days = 250, n_ma=1) :
    # calculate the returns
    df_ret_co = df_price['Close'] / df_price['Open'] -1
    df_ret_cc = df_price['Close'] / df_price['Close'].shift(1) -1
    df_ret_oo = df_price['Open'] / df_price['Open'].shift(1) - 1
    df_ret_oc = df_price['Open'] / df_price['Close'].shift(1) - 1

    # calculate the RPS
    df_rps = RPS(df_price['Close'], n_days, n_ma)

    # strategy 1: using the daily Close-Open spread
    signal = pd.DataFrame()
    signal['rps'] = (df_rps['ma'] > 0.8) * 1 \
       # + (df_rps['ma'] < 0.2) * -1


    ret = pd.DataFrame()
    ret.index.tz = None
    ret['cc'] = df_ret_cc
    #ret['oo'] = df_ret_oo
    #ret['co'] = df_ret_co
    #ret['oc'] = df_ret_oc
    ret['rps_cc'] = signal['rps'].shift(1) * df_ret_cc
    #ret['rps_co'] = signal['rps'].shift(1) * df_ret_co
    ret = ret.dropna()
    return ret


def CombinedStrategy(df_price) :
    df_spread = df_price['Close'] - df_price['Open']

    # calculate the returns
    df_ret_co = df_price['Close'] / df_price['Open'] -1
    df_ret_cc = df_price['Close'] / df_price['Close'].shift(1) -1
    df_ret_oo = df_price['Open'] / df_price['Open'].shift(1) - 1
    df_ret_oc = df_price['Open'] / df_price['Close'].shift(1) - 1

    # calculate the RPS
    df_rps = RPS(df_price['Close'])

    # calculate the one side vol
    n_ma = int((1-df_rps['ma'].tail(1)) * 60) + 1
    print (n_ma)
    df_vol = AbsoluteVol(df_price, n_ma)

    # strategy 1: using the daily Close-Open spread
    signal = pd.DataFrame()
    signal['ma'] = (df_vol['ma_delta_std'] > 0) * 1
    signal['cross'] = (df_vol['delta_std'] > df_vol['ma_delta_std']) * 1

    ret = pd.DataFrame()
    ret.index.tz = None
    ret['cc'] = df_ret_cc
    ret['ma_cc'] = signal['ma'].shift(1) * df_ret_cc
    #ret['ma_co'] = signal['ma'].shift(1) * df_ret_co
    ret['cross_cc'] = signal['cross'].shift(1) * df_ret_cc
    #ret['cross_co'] = signal['cross'].shift(1) * df_ret_co
    ret = ret.dropna()
    return ret


import Quandl
df_price = Quandl.get("YAHOO/INDEX_SSEC", trim_start="1970-01-01")
df_price = df_price.loc['2004-04-20'::]

ret = CombinedStrategy(df_price)
(1+ret).cumprod().plot(figsize=[15,7])
print ret