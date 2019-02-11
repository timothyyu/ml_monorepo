"""
datasetBuild
Author: Nicholas Fentekes

Build dataset indicators for LSTM model
"""
import pandas as pd
import trendlineTools as tT
import math
from multiprocessing import Pool
import indicators

def extractFeatures(data):
    rsiPeriod=14

    """ SMA Calculation """
    sMA10,sMA20,sMA50,sMA100,sMA150,sMA200 = indicators.computeSMAsOverPeriod(data)

    """ RSI Calculation """
    rsiList = indicators.computeRSIOverPeriod(data,rsiPeriod)

    """ stochRSI calculation """
    stochRsiList = indicators.computeStochRSIOverPeriod(rsiList,rsiPeriod)

    """ Ichimoku Cloud Calculation """
    ichiConversion,ichiBase,ichiLeadingSpanA,ichiLeadingSpanB,ichiLagging = indicators.computeIchimokuCloudOverPeriod(data)

    """ Average True Range Calculation """
    avgTrueRangeList = indicators.computeAverageTrueRangeOverPeriod(data)

    """ Candle Color and Englufing Calculation """
    candleColor = indicators.checkGreenCandleOverPeriod(data)

    """ Engulfing Candle Flag Setting """
    engulfing = indicators.checkEngulfingCandleOverPeriod(data)

    """ SMA of Volume """
    volumeNorm = []
    for i in range(len(data["VolumeBTC"])):
        if i>20:
            data.iloc[i]["VolumeBTC"]= data.iloc[i]["VolumeBTC"]/sum(data.iloc[:i]["VolumeBTC"].tolist())/20

    """ Compute Trendline Values and slopes """
    supVal1,supVal2,supVal3,supSlope1,supSlope2,supSlope3,resVal1,resVal2,resVal3,resSlope1,resSlope2,resSlope3 = indicators.computeTrendlines(data["High"],data["Low"],data["Close"].tolist())

    """ Compute if price increases next period """
    tolerance = 0.01 #Change this parameter as needed
    increased = indicators.checkIncreaseTomorrow(data["Close"].tolist(),tolerance)

    """ Add extracted features to the dataset """
    data["candlecolor"]                 = candleColor
    data["engulfing"]                   = engulfing
    data["stochRSI"]                    = stochRsiList
    data["SMA10Close"]                  = sMA10
    data["SMA20Close"]                  = sMA20
    data["SMA50Close"]                  = sMA50
    data["SMA100Close"]                 = sMA100
    data["SMA200Close"]                 = sMA200
    data["IchimokuconversionLine"]      = ichiConversion
    data["IchimokuBaseline"]            = ichiBase
    data["IchimokuLeadingSpanA"]        = ichiLeadingSpanA
    data["IchimokuLeadingSpanB"]        = ichiLeadingSpanB
    data["IchimokuLaggingSpan"]         = ichiLagging
    data["IchimokuCloudSpan"]           = [((a-b) if not(a==None or b==None) else None) for a,b in zip(ichiLeadingSpanA,ichiLeadingSpanB)]
    data["DistanceLeadingSpanA"]        = [((b-a) if not(a==None or b==None) else None) for a,b in zip(ichiLeadingSpanA,data["Close"].tolist())]
    data["DistanceLeadingSpanB"]        = [((b-a) if not(a==None or b==None) else None) for a,b in zip(ichiLeadingSpanB,data["Close"].tolist())]
    data["ConversionLineBaseLine"]      = [((a-b) if not(a==None or b==None) else None) for a,b in zip(ichiConversion,ichiBase)]
    data["AverageTrueRange"]            = avgTrueRangeList
    data["SupportLine1"]                = supVal1
    data["SupportLine2"]                = supVal2
    data["SupportLine3"]                = supVal3
    data["SupportSlope1"]               = supSlope1
    data["SupportSlope2"]               = supSlope2
    data["SupportSlope3"]               = supSlope3
    data["ResistantLine1"]              = resVal1
    data["ResistantLine2"]              = resVal2
    data["ResistantLine3"]              = resVal3
    data["ResistanceSlope1"]            = resSlope1
    data["ResistanceSlope2"]            = resSlope2
    data["ResistanceSlope3"]            = resSlope3
    data["CategoricalIncrease"]         = increased    #Put extracted feature at the end

    return data

if __name__ == '__main__':
    train_dataset_url ='btcpricetrainingdataweekly.csv'
    dataWeekly = pd.read_csv(train_dataset_url,encoding="ISO-8859-1")
    train_dataset_url ='btcpricetrainingdatadaily.csv'
    dataDaily = pd.read_csv(train_dataset_url,encoding="ISO-8859-1")
    train_dataset_url ='btcpricetrainingdata12hr.csv'
    data12hr = pd.read_csv(train_dataset_url,encoding="ISO-8859-1")
    data12hr = data12hr.astype('float32')
    data =[]
    with Pool() as p:
        data = p.map(extractFeatures,[dataWeekly,dataDaily,data12hr])
    dataWeekly = data[0]
    dataDaily = data[1]
    data12hr = data[2]
    #dataWeekly = extractFeatures(dataWeekly,14)
    #dataDaily = extractFeatures(dataDaily,14)
    cleanData = dataWeekly.dropna()
    cleanData = cleanData.astype('float32')
    cleanData.CategoricalIncrease=cleanData.CategoricalIncrease.astype('int32')
    print("Clean Data Weekly: ")
    print(cleanData)
    trainData   = cleanData.iloc[:(math.floor(len(cleanData["Open"])*0.75))]
    testData    = cleanData.iloc[(math.floor(len(cleanData["Open"])*0.75)):]
    trainData.to_csv("data/btcpricetrainingdataweekly2.csv")
    testData.to_csv("data/btcpricetestingdataweekly2.csv")

    cleanData = dataDaily.dropna()
    cleanData = cleanData.astype('float32')
    cleanData.CategoricalIncrease=cleanData.CategoricalIncrease.astype('int32')
    print("Clean Data: ")
    print(cleanData)
    trainData   = cleanData.iloc[:(math.floor(len(cleanData["Open"])*0.75))]
    testData    = cleanData.iloc[(math.floor(len(cleanData["Open"])*0.75)):]
    trainData.to_csv("data/btcpricetrainingdatadaily2.csv")
    testData.to_csv("data/btcpricetestingdatadaily2.csv")

    #data = extractFeatures(data,14)
    cleanData = data12hr.dropna()
    cleanData = cleanData.astype('float32')
    cleanData.CategoricalIncrease=cleanData.CategoricalIncrease.astype('int32')
    print("Clean Data: ")
    print(cleanData)
    trainData   = cleanData.iloc[:(math.floor(len(cleanData["Open"])*0.75))]
    testData    = cleanData.iloc[(math.floor(len(cleanData["Open"])*0.75)):]
    trainData.to_csv("data/btcpricetrainingdata12hr2.csv")
    testData.to_csv("data/btcpricetestingdata12hr2.csv")
