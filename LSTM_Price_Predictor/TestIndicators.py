"""
Test indicators.py functions for common indicators to be extracted from an OHLC dataset
Author: Nicholas Fentekes
"""
import unittest
import indicators
import pandas as pd
class TestIndicators(unittest.TestCase):

    def test_checkGreenCandle(self):
        candleGreen = {"Open": 1.2, "Close": 1.5}
        candleRed = {"Open": 3.4, "Close": 2}
        self.assertEqual(indicators.checkGreenCandle(candleGreen),True)
        self.assertEqual(indicators.checkGreenCandle(candleRed),False)

    def test_checkEngulfingCandleOverPeriod(self):
        candleSet = []
        candleSet.append({"Open": 1, "Close": 2})
        candleSet.append({"Open": 3, "Close": 0.5})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkEngulfingCandleOverPeriod(candleSet), [0,-1])
        candleSet = []
        candleSet.append({"Open": 5, "Close": 4})
        candleSet.append({"Open": 3, "Close": 6})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkEngulfingCandleOverPeriod(candleSet), [0,1])

    def test_sumGainsAndLossesOverPeriod(self):
        candleSet = []
        candleSet.append({"Open": 1, "Close": 2})
        candleSet.append({"Open": 2, "Close": 1})
        candleSet = pd.DataFrame(candleSet)
        gainsTotal,lossesTotal = indicators.sumGainsAndLossesOverPeriod(candleSet)
        self.assertEqual(gainsTotal,1)
        self.assertEqual(lossesTotal,1)

        candleSet = []
        candleSet.append({"Open": 1, "Close": 2})
        candleSet.append({"Open": 2, "Close": 3})
        candleSet = pd.DataFrame(candleSet)
        gainsTotal,lossesTotal = indicators.sumGainsAndLossesOverPeriod(candleSet)
        self.assertEqual(gainsTotal,2)
        self.assertEqual(lossesTotal,0)

        candleSet = []
        candleSet.append({"Open": 3, "Close": 2})
        candleSet.append({"Open": 2, "Close": 1})
        candleSet = pd.DataFrame(candleSet)
        gainsTotal,lossesTotal = indicators.sumGainsAndLossesOverPeriod(candleSet)
        self.assertEqual(gainsTotal,0)
        self.assertEqual(lossesTotal,2)

    """
    def test_computeRSI(self):
        candleSet = []
        for i in range (1,29):
            candleSet.append({"Open": i, "Close": i+1})
        candleSet = pd.DataFrame(candleSet)
        """

    def test_computeSMAsOverPeriod(self):
        candleSet = []
        for i in range(250):
            candleSet.append({"Open": 5, "Close": 5})
        candleSet = pd.DataFrame(candleSet)
        solution10,solution20,solution50,solution100,solution150,solution200 = [],[],[],[],[],[]
        for i in range(250):
            if i>10:
                solution10.append(0)
            else:
                solution10.append(None)
            if i>20:
                solution20.append(0)
            else:
                solution20.append(None)
            if i>50:
                solution50.append(0)
            else:
                solution50.append(None)
            if i>100:
                solution100.append(0)
            else:
                solution100.append(None)
            if i>150:
                solution150.append(0)
            else:
                solution150.append(None)
            if i>200:
                solution200.append(0)
            else:
                solution200.append(None)
        sMA10,sMA20,sMA50,sMA100,sMA150,sMA200 = indicators.computeSMAsOverPeriod(candleSet)
        self.assertEqual(sMA10,solution10)
        self.assertEqual(sMA20,solution20)
        self.assertEqual(sMA50,solution50)
        self.assertEqual(sMA100,solution100)
        self.assertEqual(sMA150,solution150)
        self.assertEqual(sMA200,solution200)

        candleSet = []
        for i in range(125):
            candleSet.append({"Open": 5, "Close": 5})
            candleSet.append({"Open": 10, "Close": 10})
        candleSet = pd.DataFrame(candleSet)
        solution10,solution20,solution50,solution100,solution150,solution200 = [],[],[],[],[],[]
        for i in range(125):
            if i==0:
                solution10.append(None)
            elif i*2-1>10:
                solution10.append(0.25)
                solution10.append(0.5)
            else:
                solution10.append(None)
                solution10.append(None)
            if i==0:
                solution20.append(None)
            elif i*2-1>20:
                solution20.append(0.25)
                solution20.append(0.5)
            else:
                solution20.append(None)
                solution20.append(None)
            if i==0:
                solution50.append(None)
            elif i*2-1>50:
                solution50.append(0.25)
                solution50.append(0.5)
            else:
                solution50.append(None)
                solution50.append(None)
            if i==0:
                solution100.append(None)
            elif i*2-1>100:
                solution100.append(0.25)
                solution100.append(0.5)
            else:
                solution100.append(None)
                solution100.append(None)
            if i==0:
                solution150.append(None)
            elif i*2-1>150:
                solution150.append(0.25)
                solution150.append(0.5)
            else:
                solution150.append(None)
                solution150.append(None)
            if i==0:
                solution200.append(None)
            elif i*2-1>200:
                solution200.append(0.25)
                solution200.append(0.5)
            else:
                solution200.append(None)
                solution200.append(None)
        solution10.append(0.25)
        solution20.append(0.25)
        solution50.append(0.25)
        solution100.append(0.25)
        solution150.append(0.25)
        solution200.append(0.25)
        sMA10,sMA20,sMA50,sMA100,sMA150,sMA200 = indicators.computeSMAsOverPeriod(candleSet)
        self.assertEqual(sMA10,solution10)
        self.assertEqual(sMA20,solution20)
        self.assertEqual(sMA50,solution50)
        self.assertEqual(sMA100,solution100)
        self.assertEqual(sMA150,solution150)
        self.assertEqual(sMA200,solution200)


    def test_computeAverageTrueRange(self):
        candleSet = []
        for i in range (1,29):
            candleSet.append({"Low": i, "High": i+1,"Close": i+1})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.computeAverageTrueRange(candleSet),1)
        candleSet = []
        for i in range (1,29):
            candleSet.append({"Low": i, "High": i+5,"Close": i+5})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.computeAverageTrueRange(candleSet),5)
        candleSet = []
        for i in range (1,29):
            candleSet.append({"Low": 1, "High": 1,"Close": 1})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.computeAverageTrueRange(candleSet),0)

    def test_checkIncreaseTomorrow(self):
        candleSet = []
        candleSet.append({"Open": 1, "Close": 1})
        candleSet.append({"Open": 1, "Close": 2})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkIncreaseTomorrow(candleSet["Close"],0.02),[1,0])
        candleSet = []
        candleSet.append({"Open": 1, "Close": 1})
        candleSet.append({"Open": 1, "Close": 1})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkIncreaseTomorrow(candleSet["Close"],0.02),[0,0])
        candleSet = []
        candleSet.append({"Open": 1, "Close": 1})
        candleSet.append({"Open": 1, "Close": 0.5})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkIncreaseTomorrow(candleSet["Close"],0.02),[0,0])
        candleSet = []
        candleSet.append({"Open": 1, "Close": 1})
        candleSet.append({"Open": 1, "Close": 1.0001})
        candleSet = pd.DataFrame(candleSet)
        self.assertEqual(indicators.checkIncreaseTomorrow(candleSet["Close"],0.02),[0,0])

if __name__ == '__main__':
    unittest.main()
