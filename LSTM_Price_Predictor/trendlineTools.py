"""
trendlineTools
Author: Nicholas Fentekes

Tools to calculate and plot support/resistance lines
"""
from __future__ import unicode_literals
import re, sys, requests, os, logging, time, json, argparse, math, io,itertools
from decimal import *
import matplotlib.dates as mdates
from datetime import datetime
import matplotlib.pyplot as plt
from requests.auth import HTTPBasicAuth
import matplotlib.ticker as mticker
import matplotlib.axes as ax
from matplotlib.finance import candlestick_ohlc
import numpy as np
import argparse

parser = argparse.ArgumentParser(description='Specify Binance candlestick data')
parser.add_argument('-symbol', metavar='S', type=str, nargs='+', default='XRPBTC',
                   help='symbol pairing to pull chart data for (Ex. XRPBTC)')
parser.add_argument('-interval', metavar='I', type=str, nargs='+', default='1d',
                   help="Candlestick interval. Choices are: 1w, 1d, 12h, 6h, 2h, 1h, 30m, 15m, 5m, 1m")
parser.add_argument('-period', metavar='P', type=int, nargs='+', default=200,
                   help='Chart period i.e. number of candlesticks to use')
args = parser.parse_args()
if args.interval!='1w' and args.interval!='1d' and args.interval!='12h' and args.interval!='6h' and args.interval!='2h' and args.interval!='1h' and args.interval!='30m' and args.interval!='15m' and args.interval!='5m' and args.interval!='1m':
    print("ERROR: Invalid interval! Possible values are: 1w, 1d, 12h, 6h, 2h, 1h, 30m, 15m, 5m, 1m")
    print("Exiting...")
    sys.exit(0)
if args.period%1 != 0 or args.period <= 0:
    print("ERROR: Invalid period! Must be interger value greater than 0")
    print("Exiting...")
    sys.exit(0)

def computePivotPoints(high,low,timestamp):
    """
        Compute Pivot Points:
        Input high:         Series of high prices over a period
        Input low:          Series of low prices over a period
        Input timestamp:    Series of timestamps corresponding to prices
    """
    maxs = []
    mins = []
    del high[high.index(max(high))]
    for i in range(2,len(high)):
        if(high[i-2]<=high[i-1] and high[i-1]>=high[i]):
            if(i>4 and i<len(timestamp)-2):
                maxs.append(([timestamp[j] for j in range(i-3,i+2)],[high[i-1]]*5))
            elif(i<len(timestamp)-1):
                maxs.append(([timestamp[j] for j in range(i-2,i+1)],[high[i-1]]*3))
            else:
                maxs.append(([timestamp[j] for j in range(i-3,i)],[high[i-1]]*3))
        elif(low[i-2] >= low[i-1] and low[i-1] <= low[i]):
            if(i>4 and i<len(timestamp)-2):
                mins.append(([timestamp[j] for j in range(i-3,i+2)],[low[i-1]]*5))
            elif(i<len(timestamp)-1):
                mins.append(([timestamp[j] for j in range(i-2,i+1)],[low[i-1]]*3))
            else:
                mins.append(([timestamp[j] for j in range(i-2,i+1)],[low[i-1]]*3))
    return (mins,maxs)


def computePivotRegression(high,low,timestamp):
    """
    regr = linear_model.LinearRegression()
    # Train the model using the training sets
    regr.fit(diabetes_X_train, diabetes_y_train)
    # Make predictions using the testing set
    min_y_pred = regr.predict(min_y_test)
    """

def computeResistanceLines(high,timestamp):
    """
        compute Resistance Lines
        Input high:   Series of high prices over a period
        Input timestamp:    Series of timestamps corresponding to high prices
        Output (resX,resY,resX2,resY2,resX3,resY3): 3 pairs of (x,y) coordinate arrays for plotting
            If the current price is at the first resistance line resX3=None and resY3=None
    """
    iMax,absMax         = high.index(max(high)),max(high)
    resSlope,resSlope3,resSlope4    = None,None,None     #Constant for log line equations
    lastRes1,lastRes2   = -1,-1
    resX,resY,resX2,resY2,resX3,resY3,resX4,resY4   = [],[],[],[],[],[],[],[]
    if iMax>=len(high)*0.8:
        for i in reversed(range(iMax)):
            h = high[i]

            if resSlope==None or (np.multiply(np.power(10,resSlope*(i-iMax)),absMax))<h:
                resSlope            = math.log10(absMax/h)/(i-iMax)
                lastRes1        = i
            elif np.multiply(np.power(10,resSlope*(i-iMax)),absMax*0.98)<h:
                lastRes1        = i
        resX    = [j-iMax for j in range(len(high))]   #x values for plotting resistance
        resY    = np.multiply(np.power(10,np.multiply(resX,(resSlope))),absMax)
    else:
        for i in range(iMax+1,len(high)):
            h = high[i]
            if resSlope==None or (np.multiply(np.power(10,-resSlope*(i-iMax)),absMax))<h:
                resSlope            = math.log10(absMax/h)/(i-iMax)
                lastRes1        = i
            elif np.multiply(np.power(10,-resSlope*(i-iMax)),absMax*0.98)<h:
                lastRes1        = i
        resX    = [j-iMax for j in range(len(high))]   #x values for plotting resistance
        resY    = np.multiply(np.power(10,np.multiply(resX,-(resSlope))),absMax)
    resX    = timestamp[-len(resX):]
    resX2   = resX
    resY2   = [y*0.95 for y in resY]
    if lastRes1+2<len(high):    #If current price is touching lon-term resistance
        #Then compute mid-term resistance line
        if iMax>=len(high)*0.8:
            for i in reversed(range(lastRes1-1)):
                h = high[i]
                if resSlope3==None or np.multiply(np.power(10,resSlope3*(i-lastRes1)),high[lastRes1])<h:
                    resSlope3       = math.log10(high[lastRes1]/h)/(i-lastRes1)
                    lastRes2    = i
                elif np.multiply(np.power(10,resSlope3*(i-lastRes1)),high[lastRes1]*0.98)<h:
                    lastRes2    = i
            resX3   = [j-lastRes1 for j in range(len(high))]
            resY3   = np.multiply(np.power(10,np.multiply(resX3,(resSlope3))),high[lastRes1])
            resX3   = timestamp[-len(resX3):]
        else:
            for i in range(lastRes1+1,len(high)):
                h = high[i]
                if resSlope3==None or np.multiply(np.power(10,-resSlope3*(i-lastRes1)),high[lastRes1])<h:
                    resSlope3       = math.log10(high[lastRes1]/h)/(i-lastRes1)
                    lastRes2    = i
                elif np.multiply(np.power(10,-resSlope3*(i-lastRes1)),high[lastRes1]*0.98)<h:
                    lastRes2    = i
            resX3   = [j-lastRes1 for j in range(len(high))]
            resY3   = np.multiply(np.power(10,np.multiply(resX3,-(resSlope3))),high[lastRes1])
            resX3   = timestamp[-len(resX3):]
        if lastRes2+2<len(high):    #If current price isnt touching mid-term resistance
            #Then compute short-term resistance
            if iMax>=len(high)*0.8:
                for h in high[lastRes2+1:]:
                    i = high.index(h)
                    if resSlope4==None or np.multiply(np.power(10,resSlope4*(i-lastRes2)),high[lastRes2])<h:
                        if i!=lastRes2:
                            resSlope4   = math.log10(high[lastRes2]/h)/(i-lastRes2)
                        else:
                            resSlope4   = 0
                resX4   = [j-lastRes2 for j in range(len(high))]   #xvals
                resY4   = np.multiply(np.power(10,np.multiply(resX4,(resSlope4))),high[lastRes2])
                resX4   = timestamp[-len(resX4):]   #xvals to timestamp for plotting
            else:
                for h in high[lastRes2+1:]:
                    i = high.index(h)
                    if resSlope4==None or np.multiply(np.power(10,-resSlope4*(i-lastRes2)),high[lastRes2])<h:
                        if i!=lastRes2:
                            resSlope4   = math.log10(high[lastRes2]/h)/(i-lastRes2)
                        else:
                            resSlope4   = 0
                resX4   = [j-lastRes2 for j in range(len(high))]   #xvals
                resY4   = np.multiply(np.power(10,np.multiply(resX4,-(resSlope4))),high[lastRes2])
                resX4   = timestamp[-len(resX4):]   #xvals to timestamp for plotting
        else:   #If current price is touching mid-term resistence
            #Then short-term resistance = mid-term resistance
            resX4,resY4,resSlope4 = resX3,resY3,resSlope3
    else:   #If current price is touching long-term resistance
        #Then short-term and mid-term resistance = long-term resistance
        resX3,resY3,resSlope3,resX4,resY4, resSlope4 = resX,resY,resSlope,resX,resY,resSlope
    return (resX,resY,resX2,resY2,resX3,resY3,resX4,resY4,[resSlope,resSlope3,resSlope4])


def computeSupportLines(low,timestamp):
    """
        compute Support Lines
        Input low:          Series of low prices over a period
        Input timestamp:    Series of timestamps corresponding to lowPrices
        Output (supX,supY,supX2,supY2,supX3,supY3):
            3 pairs of (x,y) coordinate arrays for plotting
            If the current price is at the first support line supX3=None and supY3=None
    """
    iMin, absMin        = low.index(min(low)), min(low) #index and val of absolute min
    supSlope,supSlope3,supSlope4    = None,None,None    #Slope constants for log lines
    lastSup1,lastSup2   = -1,-1 #Track last point that touched mid and long-term support
    supX,supY,supX2,supY2,supX3,supY3,supX4,supY4   = [],[],[],[],[],[],[],[]
    if len(low)>250:
        low         = low[250:]
        timestamp   = timestamp[250:]
    if iMin>len(low)*0.8:
        for i in reversed(range(iMin)):
            l = low[i]
            if supSlope == None or np.multiply(np.power(10,-supSlope*(i-iMin)),absMin)>l:
                supSlope            = math.log10(l/absMin)/(i-iMin)
                lastSup1        = i
            elif np.multiply(np.power(10,-supSlope*(i-iMin)),absMin*1.02)<l and i<len(low):
                lastSup1    = i

        supX    = [i-iMin for i in range(len(low))]  #x values for plotting support
        supY    = np.multiply(np.power(10,np.multiply(supX,-supSlope)),low[iMin])
        supX    = timestamp[-len(supX):]
    else:
        for i in range(iMin+1,len(low)):
            l = low[i]
            if supSlope == None or np.multiply(np.power(10,supSlope*(i-iMin)),absMin)>l:
                supSlope            = math.log10(l/absMin)/(i-iMin)
                lastSup1        = i
            elif np.multiply(np.power(10,supSlope*(i-iMin)),absMin*1.02)<l and i<len(low):
                lastSup1    = i
        supX    = [i-iMin for i in range(len(low))]  #x values for plotting support
        supY    = np.multiply(np.power(10,np.multiply(supX,supSlope)),low[iMin])
        if supY[-1]>1e60:
                    print('supX: ',supX)
                    print('supSlope')
        supX    = timestamp[-len(supX):]

    supX2,supY2 = supX,[y*1.05 for y in supY]   #5% support zone
    if lastSup1+2<len(low):     #If current price isn't at long-term support
        #Then compute mid-term support
        if iMin>len(low)*0.8:
            if lastSup1>5:
                for i in reversed(range(lastSup1)):  #compute log-line constants
                    l = low[i]
                    if supSlope3==None or np.multiply(np.power(10,-supSlope3*(i-lastSup1)),low[lastSup1])<l:
                        #print("supSlopeCOMPUTATION", math.log10(low[lastSup1]/l)/(i-lastSup1))
                        supSlope3       = math.log10(low[lastSup1]/l)/(i-lastSup1)
                        lastSup2    = i #Update last point that touched mid-term support
                    elif np.multiply(np.power(10,-supSlope3*(i-lastSup1)),low[lastSup1]*1.02)<l:
                        lastSup2    = i #Update last point that touched mid-term support
                supX3   = [i-lastSup1 for i in range(len(low))]   #x values
                #print("supX3   ",supX3)
                print("supSlope3    ",supSlope3)
                print("LASTSUP2",lastSup1)

                supY3   = np.multiply(np.power(10,np.multiply(supX3,-supSlope3)),low[lastSup1])
                supY3 = supY3.astype(np.float64)

                supX3   = timestamp[-len(supX3):]   #Convert xvals to timestamps
            else:
                supX3,supY3,supSlope3 = supX,supY,supSlope
                lastSup2 = 0
        else:
            for i in range(lastSup1+1,len(low)):  #compute log-line constants
                l = low[i]
                if supSlope3==None or np.multiply(np.power(10,supSlope3*(i-lastSup1)),low[lastSup1])<l:
                    supSlope3       = math.log10(low[lastSup1]/l)/(i-lastSup1)
                    lastSup2    = i #Update last point that touched mid-term support
                elif np.multiply(np.power(10,supSlope3*(i-lastSup1)),low[lastSup1]*1.02)<l:
                    lastSup2    = i #Update last point that touched mid-term support
            supX3   = [i-lastSup1 for i in range(lastSup1,len(low))]   #x values
            supY3   = np.multiply(np.power(10,np.multiply(supX3,supSlope3)),low[lastSup1])
            supX3   = timestamp[-len(supX3):]   #Convert xvals to timestamps
        if lastSup2+1<len(low): #If current price isn't touching mid-term support
            #Then compute short term support
            if iMin>len(low)*0.8:
                if lastSup2 > 5:
                    for l in reversed(low[:lastSup2]):  #compute log-line slope constant
                        i = low.index(l)
                        if supSlope4==None or np.multiply(np.power(10,-supSlope4*(i-lastSup2)),low[lastSup2])<l:
                            if i!=lastSup2:
                                supSlope4   = math.log10(low[lastSup2]/l)/(i-lastSup2)
                            else:
                                supSlope4 =0
                    supX4   = [i-lastSup2 for i in range(len(low))]   #xvals
                    supY4   = np.multiply(np.power(10,np.multiply(supX4,-supSlope4)),low[lastSup2])
                    supX4   = timestamp[-len(supX4):]   #timesamp conversion of xvals
                elif lastSup2 == 0:
                    supX4,supY4,supSlope4 = supX,supY,supSlope
                else:
                    supX4,supY4,supSlope4 = supX3,supY3,supSlope3
            else:
                for l in low[lastSup2+1:]:  #compute log-line slope constant
                    i = low.index(l)
                    if supSlope4==None or np.multiply(np.power(10,supSlope4*(i-lastSup2)),low[lastSup2])<l:
                        if i!=lastSup2:
                            supSlope4   = math.log10(low[lastSup2]/l)/(i-lastSup2)
                        else:
                            supSlope4 =0
                supX4   = [i-lastSup2 for i in range(lastSup2,len(low))]   #xvals
                supY4   = np.multiply(np.power(10,np.multiply(supX4,supSlope4)),low[lastSup2])
                supX4   = timestamp[-len(supX4):]   #timesamp conversion of xvals
        else:   #If current price at mid-term support
            supX4,supY4,supSlope4 = supX3,supY3,supSlope3   #short-term support = mid-term support
    else:   #If current price is at long term support
        #Then short-term and mid-term support are equal to long term support
        supX3,supY3,supSlope3,supX4,supY4,supSlope4 = supX,supY,supSlope,supX,supY,supSlope
    return (supX,supY,supX2,supY2,supX3,supY3,supX4,supY4,[supSlope,supSlope3,supSlope4])  #Return all lines


def detectTriangle(supYs,resYs,high,low):
    """
        Detect Triangle and Wedge Patterns
        Inputs:
            (supXs,supYs):  List of support lines as pairs of x,y lists
            supSlope:           List of slopes of support lines
            (resXs,resYs):  List of resistance lines as pairs of x,y lists
            resSlope:           List of slopes of resistance lines
        Outputs:
            symVal:         Strength of symmetric triangle pattern (0,1)
            ascdescVal:     Strength of ascending triangle pattern (-1,1)
                            1 = strong ascending triangle, -1 = strong descending triangle
            riseFallVal:    Strength of rising or falling wedge pattern (-1,1)
                            1 = strong rising wedge, -1 = strong falling wedge
    """
    symVal,ascDescVal,riseFallVal,avgTouches = [],[],[],[]
    for i in range(len(supYs)): #for each supprt and resistance line
        if supYs[i][0]!=0:  #If first support val is not 0
            if (supYs[i][1]>=supYs[i][0]):  #If slope of support line is posotive
                supSlope    = math.log10(supYs[i][1]/supYs[i][0])/1  #slope of support line
            else:
                supSlope    = -math.log10(supYs[i][0]/supYs[i][1])/1  #slope of support line
            if resYs[i][1]>=resYs[i][0]:
                resSlope    = math.log10(resYs[i][1]/resYs[i][0])/1  #slope of resistance line
            else:
                resSlope    = -math.log10(resYs[i][0]/resYs[i][1])/1  #slope of resistance line
        else:   #If first support val is 0, use second 2 vals so compute slope
            print('supYs[i]',supYs[i])
            print('i',i)
            print('len',len(supYs[i]))
            if (supYs[i][2]>=supYs[i][1]):
                supSlope    = math.log10(supYs[i][2]/supYs[i][1])/1  #slope of support line
            else:
                supSlope    = -math.log10(supYs[i][1]/supYs[i][2])/1  #slope of support line
            if resYs[i][2]>=resYs[i][1]:
                resSlope    = math.log10(resYs[i][2]/resYs[i][1])/1  #slope of resistance line
            else:
                resSlope    = -math.log10(resYs[i][1]/resYs[i][2])/1  #slope of resistance line
        supTouches = 0  #Number of touches to support line
        resTouches = 0  #Number of touches to resistance line
        for j in range(len(supYs[i])):  #Calcula Number of touches to support line
            if low[j]<supYs[i][j]*1.02:
                supTouches+=1
        for j in range(len(resYs[i])):  #compute number of touches to resistance line
            if high[j]>resYs[i][j]*0.98:
                resTouches+=1
        #Store average touches as an indicator of pattern strength
        avgTouches.append((supTouches+resTouches)/2)
        if ((supSlope >0 and resSlope<0) or (supSlope<0 and resSlope>0)) and ((abs(supSlope)>=abs(resSlope)*0.5 and abs(supSlope)<=abs(resSlope)*1.5)or(abs(resSlope)>=abs(supSlope)*0.5 and abs(resSlope)<=abs(supSlope)*1.5)): #Equal and negated slopes
            symVal.append(1)
        else:
            symVal.append(0)
        if supSlope>0 and resSlope>0 and supSlope>resSlope:             #Rising wedge
            riseFallVal.append(1)
        elif supSlope<0 and resSlope<0 and supSlope>resSlope:           #Falling wedge
            riseFallVal.append(-1)
        elif abs(supSlope) < abs(resSlope)*0.4 and resSlope<0:     #Ascending wedge
            ascDescVal.append(1)
        elif abs(resSlope)<abs(supSlope)*0.4 and supSlope>0:       #Descending wedge
            ascDescVal.append(-1)
    return symVal,ascDescVal,riseFallVal,avgTouches


def cleanSpikes(highPrice,lowPrice,closePrice):
    """ Remove high and low prices significantly out of the normal range
        Remove highest price if greater than 2x the second highest price
        Remove lowest price if less than 1/2 the second lowest price
        Input highPrice:                List of high prices over the period
        Input lowPrice:                 List of low prices over the period
        Input closePrice:               List of close prices over the period
        Output (highPrice,lowPrice):    Cleaned high and low price lists
    """
    tempHigh,tempLow = highPrice, lowPrice
    #tempHigh.pop(tempHigh.index(max(tempHigh)))
    #tempLow.pop(tempLow.index(min(tempLow)))
    maxIndex = highPrice.index(max(highPrice))
    minIndex = lowPrice.index(min(lowPrice))
    max2,min2= 0,max(lowPrice)
    for i in range(len(highPrice)):
        if i!=maxIndex:
            if highPrice[i] > max2:
                max2    = highPrice[i]
        if i!=minIndex:
            if lowPrice[i] < min2:
                min2    = lowPrice[i]
    if max(highPrice) > max2*3:
        highPrice[maxIndex] = closePrice[maxIndex]
    if min(lowPrice) < min2*0.4:
        lowPrice[minIndex]  = closePrice[minIndex]
    return highPrice,lowPrice

if __name__ == '__main__':
    pr      = {"symbol": args.symbol, "interval": args.interval, "limit": args.period}
    lst     = requests.get("https://www.binance.com/api/v1/klines",params = pr).json()
    smaTimestamp    = [float(candle[0])/1000 for candle in lst]
    lst             = lst[-(args.period):]
    date = [datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d %H:%M:%S') for candle in lst]
    timestamp   = [float(candle[0])/1000 for candle in lst]
    open        = [float(candle[1]) for candle in lst]
    high        = [float(candle[2]) for candle in lst]
    low         = [float(candle[3]) for candle in lst]
    close       = [float(candle[4]) for candle in lst]
    volume      = [float(candle[5]) for candle in lst]
    high,low    = cleanSpikes(high,low,close)

    ohlc = []   #Open,High,Low,Close Price dataset for candlesticks
    for x in range(len(date)):
        append_me = float(timestamp[x]), float(open[x]), float(high[x]), float(low[x]), float(close[x]), float(volume[x])
        ohlc.append(append_me)
    fig = plt.Figure()
    ax = plt.subplot2grid((1,1), (0,0))
    candlestick_ohlc(ax, ohlc)  #Plot candlestick chart
    (resx1,resY1,resx2,resY2,resx3,resY3,resx4,resY4,resSlope) = computeResistanceLines(high,timestamp)
    plt.plot(resx1,resY1)
    plt.plot(resx2,resY2)
    if len(resY3):
        plt.plot(resx3,resY3)
    if len(resY4):
        plt.plot(resx4,resY4)
    (supX1,supY1,supX2,supY2,supX3,supY3,supX4,supY4,supSlope) = computeSupportLines(low,timestamp)
    plt.plot(supX1,supY1)
    plt.plot(supX2,supY2)
    if len(supY3):
        plt.plot(supX3,supY3)
    if len(supY4):
        plt.plot(supX4,supY4)
    sys,resYs=[supY1,supY3,supY4],[resY1,resY3,resY4]
    (supYmVal,ascDescVal,riseFallVal,avgTouches)  = detectTriangle([supY1,supY3,supY4],[resY1,resY3,resY4],high,low)

    mins,maxs = computePivotPoints(high,low,timestamp)
    for x,y in maxs:
        ax.plot(x,y)
    for x,y in mins:
        ax.plot(x,y)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(10))
    plt.ylim(ymin=min(low),ymax=max(high)+max(high)*0.05)
    ax.grid(True)
    plt.yscale('log')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.title(args.symbol)
    plt.show()
