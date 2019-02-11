"""
Functions for common indicators to be extracted from an OHLC candleSetset
Author: Nicholas Fentekes
"""
import math
import pandas as pd
import trendlineTools as tT
def checkGreenCandle(candle):
    if candle["Open"] < candle["Close"]:
        return True
    else:
        return False
def checkGreenCandleOverPeriod(candleSet):
    candleColor = []
    for i in range(len(candleSet["Open"])):
        if(checkGreenCandle(candleSet.iloc[i-1])):
            #If the candle increased in price
            candleColor.append(1)
        if(not checkGreenCandle(candleSet.iloc[i-1])):
            candleColor.append(-1)
    return candleColor

def checkEngulfingCandleOverPeriod(candleSet):
    engulfing = []
    engulfing.append(0)
    for i in range(1,len(candleSet["Open"])):
        if(checkGreenCandle(candleSet.iloc[i-1])):
            engulfing.append(-1 if candleSet["Open"][i] > candleSet["Close"][i-1] and candleSet["Close"][i] < candleSet["Open"][i-1] else 0)
        if(not checkGreenCandle(candleSet.iloc[i-1])):
            if candleSet["Open"][i] < candleSet["Close"][i-1] and candleSet["Close"][i] > candleSet["Open"][i-1]:
                engulfing.append(1)
            else:
                engulfing.append(0)
    return engulfing

def sumGainsAndLossesOverPeriod(candleSet):
    gainsTotal, lossesTotal = 0,0
    for index,candle in candleSet.iterrows():   #Sum total gains and losses over candleSet
        if(checkGreenCandle(candle)):
            gainsTotal+=(candle["Close"]-candle["Open"])
        else:
            lossesTotal+=(candle["Open"]-candle["Close"])
    return gainsTotal, lossesTotal

def computeRSI(candleSet, previousGains = None, previousLosses = None, firstRSICalculation=False):
    """ Compute the RSI for a given set of candles """
    period = len(candleSet["Open"])
    gainsTotal, lossesTotal = sumGainsAndLossesOverPeriod(candleSet)
    gainsAveragePerCandle = gainsTotal / period
    lossesAveragePerCandle = lossesTotal / period
    if firstRSICalculation:
        rsi = (100-100/(1+(gainsAveragePerCandle/lossesAveragePerCandle)))
        return (rsi,(gainsAveragePerCandle,lossesAveragePerCandle))
    else:
        rs = ((previousGains*(period-1)+gainsAveragePerCandle)/period) / ((previousLosses*(period-1)+lossesAveragePerCandle)/period)
        return((100-100/(1+rs)),(gainsAveragePerCandle,lossesAveragePerCandle))
def computeRSIOverPeriod(candleSet,rsiPeriod):
    rsiList = []
    for i in range(len(candleSet["Open"])):
        if(i<rsiPeriod):
            #Need 14 previous candles to compute RSI
            rsiList.append(None)
        elif(i==rsiPeriod):
            #First RSI Calculation
            (rsi,(gains,losses)) = computeRSI(candleSet=candleSet.iloc[0:i],firstRSICalculation=True)
            rsiList.append(rsi)
        elif(i>rsiPeriod):
            #compute smoothed RSI with previous avg gains and avg losses
            (rsi,(gains,losses)) = computeRSI(candleSet=candleSet.iloc[i-rsiPeriod:i],previousGains=gains,previousLosses=losses,firstRSICalculation=False)
            rsiList.append(rsi)
    return rsiList

def computeStochRSIOverPeriod(rsiList,rsiPeriod):
    stochRSIList = []
    for i in range(len(rsiList)):
        if(i<=rsiPeriod*2):
            stochRSIList.append(None)
        if(i>rsiPeriod*2):
            maxRSI = max(rsiList[i-rsiPeriod:i])
            minRSI = min(rsiList[i-rsiPeriod:i])
            stochRSIList.append((rsiList[i-1]-minRSI)/(maxRSI-minRSI))
    return stochRSIList

def computeSMAsOverPeriod(candleSet):
    sMA10,sMA20,sMA50,sMA100,sMA150,sMA200 = [],[],[],[],[],[]
    for i in range(len(candleSet["Open"])):
        currentPrice = float(candleSet.iloc[i]["Close"])
        if(i>10):
            sMA10.append((abs(candleSet.iloc[i-10:i]["Close"].sum()/10-currentPrice))/currentPrice)
        else:
            sMA10.append(None)
        if(i>20):
            sMA20.append((abs(candleSet.iloc[i-20:i]["Close"].sum()/20-currentPrice))/currentPrice)
        else:
            sMA20.append(None)
        if(i>50):
            sMA50.append((abs(candleSet.iloc[i-50:i]["Close"].sum()/50-currentPrice))/currentPrice)
        else:
            sMA50.append(None)
        if(i>100):
            sMA100.append((abs(candleSet.iloc[i-100:i]["Close"].sum()/100-currentPrice))/currentPrice)
        else:
            sMA100.append(None)
        if(i>150):
            sMA150.append((abs(candleSet.iloc[i-150:i]["Close"].sum()/150-currentPrice))/currentPrice)
        else:
            sMA150.append(None)
        if(i>200):
            sMA200.append((abs(candleSet.iloc[i-200:i]["Close"].sum()/200-currentPrice))/currentPrice)
        else:
            sMA200.append(None)
    return sMA10,sMA20,sMA50,sMA100,sMA150,sMA200

def computeIchimokuCloud(candleSet):
    """ compute current values of Ichimoku Cloud lines """
    conversionLine  = (max([x["High"] for i,x in candleSet.iloc[-9:].iterrows()]) + min([y["Low"] for i,y in candleSet.iloc[-9:].iterrows()]))/2
    baseLine        = (max([x["High"] for i,x in candleSet.iloc[-26:].iterrows()])+ min([y["Low"] for i,y in candleSet.iloc[-26:].iterrows()]))/2
    leadingSpanA    = (conversionLine + baseLine)/2
    leadingSpanB    = (max([x["High"] for i,x in candleSet.iloc[:].iterrows()]) + min([y["Low"] for i,y in candleSet.iloc[:].iterrows()]))/2
    laggingSpan     = candleSet.iloc[-26]["Close"]
    return conversionLine,baseLine,leadingSpanA,leadingSpanB,laggingSpan
def computeIchimokuCloudOverPeriod(candleSet):
    ichiConversion,ichiBase,ichiLeadingSpanA,ichiLeadingSpanB,ichiLagging = [],[],[],[],[]
    for i in range(len(candleSet["Open"])):
        if i>52:
            (conversionLine,baseLine,leadingSpanA,leadingSpanB,laggingSpan) = computeIchimokuCloud(candleSet.iloc[i-52:i])
            ichiConversion.append(conversionLine/(candleSet["Close"].iloc[i]))
            ichiBase.append(baseLine/(candleSet["Close"].iloc[i]))
            ichiLeadingSpanA.append(leadingSpanA/(candleSet["Close"].iloc[i]))
            ichiLeadingSpanB.append(leadingSpanB/(candleSet["Close"].iloc[i]))
            ichiLagging.append(laggingSpan/(candleSet["Close"].iloc[i]))
        else:
            ichiConversion.append(None)
            ichiBase.append(None)
            ichiLeadingSpanA.append(None)
            ichiLeadingSpanB.append(None)
            ichiLagging.append(None)
    return ichiConversion,ichiBase,ichiLeadingSpanA,ichiLeadingSpanB,ichiLagging

def computeAverageTrueRange(candleSet):
    """ compute the average volitility over a given period """
    rangeList = []
    count = 0
    for index,candle in candleSet.iterrows():
        if count>0 and index>0:
            maxRange = max([candle["High"]-candle["Low"],candle["High"]-candleSet.iloc[count-1]["Close"],candleSet.iloc[count-1]["Close"]-candle["Low"]])
            rangeList.append(maxRange)
        count +=1
    return sum(rangeList)/len(rangeList)
def computeAverageTrueRangeOverPeriod(candleSet):
    avgTrueRangeList = []
    for i in range(len(candleSet["Open"])):
        if i>14:
            avgTrueRangeList.append(computeAverageTrueRange(candleSet.iloc[i-15:i]))
        else:
            avgTrueRangeList.append(None)
    return avgTrueRangeList

def checkIncreaseTomorrow(close,tol):
    """ Determine if price will increase, decrease, or stay the same within specified tolerance
        Input tol =         Tolerance for price movement as a percent
                            ex. 0.02 = 2% tolerance
        Output increased:   Array of output values
                            0   = increase next period > tolerance
                            2   = decrease next period > tolerance
                            1  = price stays within range of tolerance
    """
    tol = tol + 1
    increased = []
    for i in range(len(close)-1):
        if close[i]*tol<close[i+1]:
            increased.append(1)
        else:
            increased.append(0)
    increased.append(0)
    return increased

def computeTrendlines(high,low,close):
    """ Trendline Calculation """
    resList,supList,triangleList=[],[],[]
    supVal1,supVal2,supVal3,supSlope1,supSlope2,supSlope3 = [],[],[],[],[],[]
    resVal1,resVal2,resVal3,resSlope1,resSlope2,resSlope3 = [],[],[],[],[],[]
    for i in range(len(high)):
        if(i>100):
            resList.append(tT.computeResistanceLines(high.iloc[i-100:i].tolist(),range(i-100,i)))
            supList.append(tT.computeSupportLines(low.iloc[i-100:i].tolist(),range(i-100,i)))
            resx1,resy1,resx2,resy2,resx3,resy3,resx4,resy4,resSlope=resList[-1]
            sx1,sy1,sx2,sy2,sx3,sy3,sx4,sy4,supSlope=supList[-1]
            supys=sy1.tolist(),sy2,sy3.tolist(),sy4.tolist()
            resys=resy1.tolist(),resy2,resy3.tolist(),resy4.tolist()
            #triangleList.append(tT.detectTriangle(supys,resys,high.tolist(),low))
        else:
            resList.append(None)
            supList.append(None)
            triangleList.append(None)
        """ Format trendlines for datatable """
        if(supList[i]==None):
            supVal1.append(None)
            supVal2.append(None)
            supVal3.append(None)
            supSlope1.append(None)
            supSlope2.append(None)
            supSlope3.append(None)
        else:
            (sx1,sy1,sx2,sy2,sx3,sy3,sx4,sy4,(supM1,supM2,supM3)) = supList[i]
            supVal1.append(float(sy1[-1]/close[i]))
            supVal2.append(float(sy3[-1]/close[i]))
            supVal3.append(float(sy4[-1]/close[i]))
            supSlope1.append(float(supM1/close[i]))
            supSlope2.append(float(supM2/close[i]))
            supSlope3.append(float(supM3/close[i]))
        if(resList[i]==None):
            resVal1.append(None)
            resVal2.append(None)
            resVal3.append(None)
            resSlope1.append(None)
            resSlope2.append(None)
            resSlope3.append(None)
        else:
            (resx1,resy1,resx2,resy2,resx3,resy3,resx4,resy4,(resM1,resM2,resM3)) = resList[i]
            resVal1.append(float(resy1[-1]/close[i]))
            resVal2.append(float(resy3[-1]/close[i]))
            resVal3.append(float(resy4[-1]/close[i]))
            resSlope1.append(float(resM1/close[i]))
            resSlope2.append(float(resM2/close[i]))
            resSlope3.append(float(resM3/close[i]))
    return supVal1,supVal2,supVal3,supSlope2,supSlope2,supSlope3,resVal1,resVal2,resVal3,resSlope1,resSlope2,resSlope3
