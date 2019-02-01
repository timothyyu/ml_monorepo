import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.finance import candlestick_ohlc
import matplotlib.dates as mdates
import pandas as pd
import quandl
from datetime import datetime, timedelta
import numpy as np

def pattern_generate(df):
    '''
        Example function of generating a pandas DataFrame with entries that
        satisify our given pattern
    '''

    df=df.reset_index()
    df=df.ix[:,['Date','Open','High','Low','Close']]


    dates = []

    for j in range(20,len(df)-1):
        previous = df.iloc[j-6:j-3].values
        trend = trend_identifier(previous)
        data = df.iloc[j-3:j]
        if triple_star_patterns(data.iloc[0].values,data.iloc[1].values,data.iloc[2].values,trend=trend):
            dates.append(data)
    return pd.concat(dates)


def candlestick_plot(df, Bollinger_Bands = False, Highlight = None):
    '''Uses matplotlib.finance candlestick_ohlc plot. This is compatable
    with Quandl's get() format.

    Args:
        pandas.dataframe: df
        Bollinger_Bands: bool

    '''
    fig = plt.figure()
    ax1 = fig.add_subplot(111) #.subplot2grid((1,1), (0,0))
    ax2 = fig.add_subplot(111)
    ax1.xaxis_date()
    plt.xlabel("Date")
    plt.ylabel("Price")
    for label in ax1.xaxis.get_ticklabels():
        label.set_rotation(45)

    bars = df
    bars=bars.reset_index()
    bars = bars.ix[:,['Date','Open','High','Low','Close']]
    bars['Date'] = pd.to_datetime(bars['Date'],unit='s')
    bars['Date'] = bars['Date'].map(mdates.date2num)

    candlestick_ohlc(ax1,bars.values,width=.5, colorup='g', colordown='k',alpha=0.75)

    if Bollinger_Bands:
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['20SD'] = df['Close'].rolling(window=20).std()
        df['Upper Band'] = df['20MA'] + 2 * df['20SD']
        df['Lower Band'] = df['20MA'] - 2 * df['20SD']
        df=df.reset_index()
        bands = df.ix[:,['20MA','Upper Band','Lower Band']]
        MA = [bands['20MA'].as_matrix(),bands['Upper Band'].as_matrix(), bands['Lower Band'].as_matrix()]
        colors = ['b','c','c']
        for color, band in zip(colors,MA):
             ax2.plot(bars['Date'], band,color = color)

    if Highlight is not None:
        dates = Highlight['Date'].map(mdates.date2num)
        for i in dates:
            plt.axvline(x=i,ymin=0,ymax=3000, color='red', alpha = 0.25)

    plt.show()

''' helper functions '''

def body_form(data):
    ''' Forms candlestick from data array.

    Args:
        data: [string: date, float: open, float: high, float: low, float: close]
    Returns:
        float: upper shadow, float: body, float: lower shadow, string: 'bearish' or'bullish'

     '''
    # get data features
    if data[1] > data[4]:
        body = data[1] - data[4]
        ushadow = data[2] - data[1]
        lshadow = data[4] -data[3]
        return ushadow, body, lshadow, 'bearish'
    elif data[1] < data[4]:
        body = data[4] - data[1]
        ushadow = data[2] - data[4]
        lshadow = data[1] - data[3]
        return ushadow, body, lshadow,'bullish'
    else:
        return data[2] - data[4], 0, data[1] - data[3], ''

def relative_dif(point1,point2):
    ''' Relative difference between two points
    Args:
        float: point1, float: point2
    Returns:
        float
    '''

    return 2 * abs(point1-point2) / (point1 + point2)

def trend_identifier(args):
    ''' Identifies if \* args are positive or negative slope based on their close

    Args:
        list of [string: date, float: open, float: high, float: low, float: close]

    Returns:
        string: 'uptrend', string: 'downtrend' or None

    '''
    body_array = []

    for entry in args:
        body_array.append(entry[4]) #close value

    upward = all(b >= a for a, b in zip(body_array, body_array[1:]))
    downward = all(b <= a for a, b in zip(body_array, body_array[1:]))

    if upward:
        return 'uptrend'
    elif downward:
        return 'downtrend'
    else:
        return None

def smart_return(cond1, cond2):
    ''' Helper function to determine return type of pattern functions

    Args:
        string: cond1, string: cond2

    Returns:
        bool

        if cond1 == 'auto_return'
        bool, string
    '''

    if cond1 == 'auto' and cond2 != None:
        return True
    elif cond1 == 'auto_return' and cond2 != None:
        return True, cond2
    elif cond1 == cond2:
        return True
    else:
        if cond1 == 'auto_return':
            return False, ''
        else:
            return False

''' Single candlestick patterns '''

def spinning_top(data, percent_classifier = 3.0):
    ''' Spinning top single point pattern match.

    Args:
        data: [string: date, float: open, float: high, float: low, float: close]
        float: percent_classifier, default = 3.0

    Returns:
        bool
    '''
    high = data[2]
    low = data[3]
    open_ = data[1]
    close = data[4]

    if open_ > close:
        ushadow = high-open_
        lshadow = close-low
        diff = relative_dif(ushadow,lshadow) * 100
    else:
        ushadow = high-close
        lshadow = open_-low
        diff = relative_dif(ushadow,lshadow) * 100

    if diff > 5.0:
        return False
    else:
        shadow_center = 0.5 * (high+low)
        body_center = 0.5 * (open_+close)
        diff = relative_dif(shadow_center,body_center) * 100

    if diff > 5.0:
      return False

    shadow_size = high-low
    body_size = abs(open_-close)
    ratio = body_size/shadow_size

    if ratio < percent_classifier and body_size != 0:
      return True

    return False

def marubozo(data):
    ''' Marubozo pattern matching for single point

    Args:
        data: [string: date, float: open, float: high, float: low, float: close]

    Returns:
        bool

    '''
    high = data[2]
    low = data[3]
    open_ = data[1]
    close = data[4]

    if open_ >= high and close <= low:
        return True
    else:
        return False

def doji(data, specifier = 'auto'):
    ''' Doji pattern matching for single point.

    Args:
        data: [string: date, float: open, float: high, float: low, float: close]

        string: specifier, default = 'auto', acceptable options:
            'long-legged'
            'dragonfly'
            'gravesetone'
            'four_price'
            'auto_return'
    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''
    high = data[2]
    low = data[3]
    open_ = data[1]
    close = data[4]

    specifier_name = None

    if close == open_ and open_ != high and close != low:
        specifier_name =  "long-legged"
    elif close == open_ and open_ == high and close != low:
        specifier_name =  "dragonfly"
    elif close == open_ and open_ != high and close == low:
        specifier_name = 'gravestone'
    elif close == open_ and open_ == high and close == low:
        specifier_name = 'four_price'

    return smart_return(specifier, specifier_name)

def single_patterns(data, specifier = 'auto', ratio_classifier = 2.5):
    ''' Classify single patterns. Ratio classifier is defined as ratio between shadows and body

    Args:
        data: [string: date, float: open, float: high, float: low, float: close]

        string: specifier, default = 'auto', acceptable options:
            'hammer',
            'hanging_man'
            'inverted_hammer'
            'shooting_star'
            'auto_return'

        float: ratio_classifier

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''
    specifier_name = None

    # get data features
    ushadow, body, lshadow, animal = body_form(data)

    # classify pattern
    if ushadow < lshadow and lshadow >= ratio_classifier * body and animal == 'bullish':
        specifier_name = 'hammer'
    elif ushadow < lshadow and lshadow >= ratio_classifier * body and animal == 'bearish':
        specifier_name = 'hanging_man'
    elif ushadow > lshadow and ushadow >= ratio_classifier * body and animal == 'bullish':
        specifier_name = "inverted_hammer"
    elif ushadow > lshadow and ushadow >= ratio_classifier * body and animal == 'bearish':
        specifier_name = 'shooting_star'

    # return based on specifier
    return smart_return(specifier, specifier_name)

''' Two candlestick patterns '''

def engulfing_patterns(data1, data2, specifier = 'auto', ratio_classifier = 1.5):
    ''' Classify engulfing double patterns. Ratio classifier is defined as ratio between shadows and body

    Args:
        data1: [string: date, float: open, float: high, float: low, float: close]
        data2: [string: date, float: open, float: high, float: low, float: close]

        string: specifier, default = 'auto', acceptable options:
            'bearish_engulfing'
            'bullish_engulfing'
            'auto_return'

        float: ratio_classifier, default = 1.5

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''

    open_1 = data1[1]
    close1 = data1[4]
    open_2 = data2[1]
    close2 = data2[4]
    ushadow1, body1, lshadow1, animal1 = body_form(data1)
    ushadow2, body2, lshadow2, animal2 = body_form(data2)
    specifier_name = None

    if body2 >= body1 * ratio_classifier and open_2 >= open_1 and close2 <= close1:
        if animal1 == 'bearish' and animal2 == 'bullish':
            specifier_name = animal2 + '_' + 'engulfing'
        elif animal2 == 'bearish' and animal1 == 'bullish':
            specifier_name = animal2 + '_' + 'engulfing'

    return smart_return(specifier, specifier_name)

def tweezer_patterns(data1, data2, specifier = 'auto', dif_classifier = 3.0):
    ''' Classify tweezer double patterns. Difference classifier is percent difference
    between upper and lower shadows.

    Args:
        data1: [string: date, float: open, float: high, float: low, float: close]
        data2: [string: date, float: open, float: high, float: low, float: close]

        string: specifier, default = 'auto', acceptable options:
            'tweezer_bottoms'
            'tweezer_tops'
            'auto_return'

        float: dif_classifier, default = 3.0

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''

    high1 = data1[2]
    low1 = data1[3]
    high2 = data2[2]
    low2 = data2[3]
    ushadow1, body1, lshadow1, animal1 = body_form(data1)
    ushadow2, body2, lshadow2, animal2 = body_form(data2)

    specifier_name = None

    dif_body = relative_dif(body1,body2)
    dif_ushadow = relative_dif(ushadow1,ushadow2)
    dif_lshadow = relative_dif(lshadow1,lshadow2)

    if dif_body <= dif_classifier and dif_lshadow <= dif_classifier and dif_ushadow <= dif_classifier:
        if animal1 == 'bearish' and animal2 == 'bullish' and relative_dif(high1,high2) <= dif_classifier:
            if relative_dif(ushadow1, 0.0) <= relative_dif:
                specifier_name = 'tweezer_bottoms'
        elif animal1 == 'bullish' and animal2 =='bearish' and relative_dif(low1,low2) <=dif_classifier:
            if relative_dif(lshadow1,0.0)<=dif_classifier:
                specifier_name = 'tweezer_tops'

    return smart_return(specifier, specifier_name)

''' three candlestick patterns '''

def triple_star_patterns(data1, data2, data3, trend, specifier = 'auto'):
    ''' Classify star triple patterns. Trend refers to uptrend or downtrend of the previous points of data.
    See trend_identifier()

    Args:
        data1: [string: date, float: open, float: high, float: low, float: close]
        data2: [string: date, float: open, float: high, float: low, float: close]
        data3: [string: date, float: open, float: high, float: low, float: close]

        string: trend, must be either:
            'downtrend'
            'uptrend'
            None

        string: specifier, default = 'auto', acceptable options:
            'evening_star'
            'morning_star'
            'auto_return'

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''
    if trend == None:
        return smart_return(specifier, None)

    ushadow1, body1, lshadow1, animal1 = body_form(data1)
    ushadow2, body2, lshadow2, animal2 = body_form(data2)
    ushadow3, body3, lshadow3, animal3 = body_form(data3)

    midpoint1 = data1[3] + lshadow1 + 0.5 * body1
    close3 = data3[4]

    specifier_name = None

    if trend == 'uptrend' and animal1 == 'bullish' and animal3 == 'bearish':
        if body1 > body2 and body3 > body2 and midpoint1 > close3:
            specifier_name = 'evening_star'
    elif trend == 'downtrend' and animal3 == 'bullish' and animal1 == 'bearish':
        if body1 > body2 and body3 > body2 and midpoint1 < close3:
            specifier_name = 'morning_star'


    return smart_return(specifier, specifier_name)

def soldier_crow_patterns(data1, data2, data3, trend, specifier = 'auto', wick_size_ratio = 10.0):
    ''' Classify soldier/crow triple patterns. Trend refers to uptrend or downtrend of the previous points of data.
    See trend_identifier(). Wick size ratio is ratio between shadows and the body.

    Args:
        data1: [string: date, float: open, float: high, float: low, float: close]
        data2: [string: date, float: open, float: high, float: low, float: close]
        data3: [string: date, float: open, float: high, float: low, float: close]

        string: trend, must be either:
            'downtrend'
            'uptrend'
            None

        string: specifier, default = 'auto', acceptable options:
            'three_white_soldiers'
            'three_black_crows'
            'auto_return'

        float: wick_size_ratio, default = 10.0

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''
    if trend == None:
        return smart_return(specifier, None)

    _, body1, _, animal1 = body_form(data1)
    ushadow2, body2, lshadow2, animal2 = body_form(data2)
    ushadow3, body3, lshadow3, animal3 = body_form(data3)

    close1 = data1[4]
    open_2 = data2[1]
    close2 = data2[4]
    open_3 = data3[1]
    close3 = data3[4]

    specifier_name = None

    this_trend = trend_identifier(data1,data2,data3)

    if trend == 'downtrend' and this_trend == 'uptrend' and \
        animal1 == 'bullish' and animal2 == 'bullish' and \
        animal3 == 'bullish' and body1 < body2 and body2 < body3 and \
        close1<= open_2 and close2 <= open_3 and ushadow2/body2 <= wick_size_ratio and \
        lshadow2/body2 <= wick_size_ratio and lshadow3/body3 <= wick_size_ratio and \
        ushadow3/body3 <= wick_size_ratio:
        specifier_name = 'three_white_soldiers'
    elif trend == 'uptrend' and this_trend == 'downtrend' and \
        animal1 == 'bearish' and animal2 == 'bearish' and \
        animal3 == 'bearish' and body1 < body2 and body2 <= body3 and \
        close1>= open_2 and close2 >= open_3 and ushadow2/body2 <= wick_size_ratio and \
        lshadow2/body2 <= wick_size_ratio and lshadow3/body3 <= wick_size_ratio and \
        ushadow3/body3 <= wick_size_ratio:
        specifier_name = 'three_black_crows'

    return smart_return(specifier, specifier_name)

def three_inside(data1, data2, data3, trend, specifier = 'auto'):
    ''' Classify inside up/down triple patterns. Trend refers to uptrend or downtrend of the previous points of data.
    See trend_identifier().

    Args:
        data1: [string: date, float: open, float: high, float: low, float: close]
        data2: [string: date, float: open, float: high, float: low, float: close]
        data3: [string: date, float: open, float: high, float: low, float: close]

        string: trend, must be either:
            'downtrend'
            'uptrend'
            None

        string: specifier, default = 'auto', acceptable options:
            'three_inside_up'
            'three_inside_down'
            'auto_return'

    Returns:
        bool

        if cond1 == 'auto_return'
            bool, string of matched pattern

    '''
    ushadow1, body1, lshadow1, animal1 = body_form(data1)
    ushadow2, body2, lshadow2, animal2 = body_form(data2)
    ushadow3, body3, lshadow3, animal3 = body_form(data3)

    open_2 = data2[2]

    high1 = data1[2]
    low1 = data1[3]

    close3 = data3[4]

    midpoint1 = data1[3] + lshadow1 + 0.5 * body1

    specifier_name = None

    if trend == ' downtrend' and animal1 == 'bearish' and animal2 == 'bullish'and \
        animal3 == 'bullish' and body1 > body2 and open_2 >= midpoint1 and \
        close3 > high1:
        specifier_name = 'three_inside_up'
    elif trend == ' uptrend' and animal1 == 'bullish' and animal2 == 'bearish'and \
        animal3 == 'bearish' and body1 > body2 and close_2 <= midpoint1 and \
        close3 < low1:
        specifier_name = 'three_inside_down'

    return smart_return(specifier, specifier_name)
