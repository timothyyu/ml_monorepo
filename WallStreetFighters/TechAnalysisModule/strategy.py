import candles as candles
import trendAnalysis as trend
import oscilators as oscilators
from numpy import * 

class Strategy:
    positiveSignal = 50
    negativeSignal = -50
    trendVal = 100
    
    defPositiveSignal = 50
    defNegativeSignal = -50
    defTrendVal = 100

    """Formacje"""
    #Odwrocenie trendu wzrostowego
    headAndShouldersVal = -100
    tripleTopVal = -100
    risingWedgeVal = -80
    fallingTriangleVal = -80
    
    defHeadAndShouldersVal = -100
    defTripleTopVal = -100
    defRisingWedgeVal = -80
    defFallingTriangleVal = -80

    #Odwrocenie trendu spadkowego
    reversedHeadAndShouldersVal = 100
    tripleBottomVal = 100
    fallingWedgeVal = 80
    risingTriangleVal = 80
    
    defReversedHeadAndShouldersVal = 100
    defTripleBottomVal = 100
    defFallingWedgeVal = 80
    defRisingTriangleVal = 80

    #Kontynuacja trendu
    symetricTriangleVal = 50
    rectangleVal = 30
    
    flagPennantVal = 20

    defFlagPennantVal = 20
    defSymetricTriangleVal = 50
    defRectangleVal = 30
    """Wskazniki i oscylatory"""
    oscilatorsVal = 50
    newHighNewLowVal = 50
    bollignerVal = 50
    momentumVal = 50
    rocVal = 50
    cciVal = 50
    rsiVal = 50
    williamsVal = 50
    
    defOscilatorsVal = 50
    defNewHighNewLowVal = 50
    defBollignerVal = 50
    defMomentumVal = 50
    defRocVal = 50
    defCciVal = 50
    defRsiVal = 50
    defWilliamsVal = 50

    """Luki"""
    #Wzrostowe
    risingBreakawayGapVal = 50
    risingContinuationGapVal = 30
    fallingExhaustionGapVal = 10 
    
    defRisingBreakawayGapVal = 50
    defRisingContinuationGapVal = 30
    defFallingExhaustionGapVal = 10 

    #Spadkowe
    fallingBreakawayGapVal = -50
    risingExhaustionGapVal = -50
    fallingContinuationGapVal = -30
    
    defFallingBreakawayGapVal = -50
    defRisingExhaustionGapVal = -50
    defFallingContinuationGapVal = -30

    """Formacje swiecowe"""
    #sygnal kupna
    bull3Val = 15
    mornigStarVal = 10
    piercingVal = 5
    
    defBull3Val = 15
    defMornigStarVal = 10
    defPiercingVal = 5
    #sygnal sprzedazy
    bear3Val = -15
    eveningStarVal = -10
    darkCloudVal = -5
    
    defBear3Val = -15
    defEveningStarVal = -10
    defDarkCloudVal = -5
    data = None
    
    
    def __init__(self, data):
        self.setData(data)
    
    
    def setData(self, data):
        self.data = data
    
    #Potega wyrazen regularnych i textmate'a nie ma to jak wygenerowac 251 linii kodu
    
    def setPositiveSignal(self, positiveSignal):
        self.positiveSignal = positiveSignal
    def disablePositiveSignal(self):
        self.positiveSignal = 0
    def enablePositiveSignal(self):
        self.positiveSignal = self.defPositiveSignal

    def setNegativeSignal(self, negativeSignal):
        self.negativeSignal = negativeSignal
    def disableNegativeSignal(self):
        self.negativeSignal = 0
    def enableNegativeSignal(self):
        self.negativeSignal = self.defNegativeSignal

    def setTrendVal(self, trendVal):
        self.trendVal = trendVal
    def disableTrendVal(self):
        self.trendVal = 0
    def enableTrendVal(self):
        self.trendVal = self.defTrendVal

    """Formacje"""
    #Odwrocenie trendu wzrostowego

    def setHeadAndShouldersVal(self, headAndShouldersVal):
        self.headAndShouldersVal = headAndShouldersVal
    def disableHeadAndShouldersVal(self):
        self.headAndShouldersVal = 0
    def enableHeadAndShouldersVal(self):
        self.headAndShouldersVal = self.defHeadAndShouldersVal

    def setTripleTopVal(self, tripleTopVal):
        self.tripleTopVal = tripleTopVal
    def disableTripleTopVal(self):
        self.tripleTopVal = 0
    def enableTripleTopVal(self):
        self.tripleTopVal = self.defTripleTopVal

    def setRisingWedgeVal(self, risingWedgeVal):
        self.risingWedgeVal = risingWedgeVal
    def disableRisingWedgeVal(self):
        self.risingWedgeVal = 0
    def enableRisingWedgeVal(self):
        self.risingWedgeVal = self.defRisingWedgeVal

    def setFallingTriangleVal(self, fallingTriangleVal):
        self.fallingTriangleVal = fallingTriangleVal
    def disableFallingTriangleVal(self):
        self.fallingTriangleVal = 0
    def enableFallingTriangleVal(self):
        self.fallingTriangleVal = self.defFallingTriangleVal

    #Odwrocenie trendu spadkowego

    def setReversedHeadAndShouldersVal(self, reversedHeadAndShouldersVal):
        self.reversedHeadAndShouldersVal = reversedHeadAndShouldersVal
    def disableReversedHeadAndShouldersVal(self):
        self.reversedHeadAndShouldersVal = 0
    def enableReversedHeadAndShouldersVal(self):
        self.reversedHeadAndShouldersVal = self.defReversedHeadAndShouldersVal

    def setTripleBottomVal(self, tripleBottomVal):
        self.tripleBottomVal = tripleBottomVal
    def disableTripleBottomVal(self):
        self.tripleBottomVal = 0
    def enableTripleBottomVal(self):
        self.tripleBottomVal = self.defTripleBottomVal

    def setFallingWedgeVal(self, fallingWedgeVal):
        self.fallingWedgeVal = fallingWedgeVal
    def disableFallingWedgeVal(self):
        self.fallingWedgeVal = 0
    def enableFallingWedgeVal(self):
        self.fallingWedgeVal = self.defFallingWedgeVal

    def setRisingTriangleVal(self, risingTriangleVal):
        self.risingTriangleVal = risingTriangleVal
    def disableRisingTriangleVal(self):
        self.risingTriangleVal = 0
    def enableRisingTriangleVal(self):
        self.risingTriangleVal = self.defRisingTriangleVal

    #Kontynuacja trendu

    def setSymetricTriangleVal(self, symetricTriangleVal):
        self.symetricTriangleVal = symetricTriangleVal
    def disableSymetricTriangleVal(self):
        self.symetricTriangleVal = 0
    def enableSymetricTriangleVal(self):
        self.symetricTriangleVal = self.defSymetricTriangleVal

    def setRectangleVal(self, rectangleVal):
        self.rectangleVal = rectangleVal
    def disableRectangleVal(self):
        self.rectangleVal = 0
    def enableRectangleVal(self):
        self.rectangleVal = self.defRectangleVal

    def setFlagPennantVal(self, flagPennantVal):
        self.flagPennantVal = flagPennantVal
    def disableFlagPennantVal(self):
        self.flagPennantVal = 0
    def enableFlagPennantVal(self):
        self.flagPennantVal = self.defFlagPennantVal    
    """Wskazniki i oscylatory"""

    def setOscilatorsVal(self, oscilatorsVal):
        self.oscilatorsVal = oscilatorsVal
    def disableOscilatorsVal(self):
        self.oscilatorsVal = 0
    def enableOscilatorsVal(self):
        self.oscilatorsVal = self.defOscilatorsVal

    def setNewHighNewLowVal(self, newHighNewLowVal):
        self.newHighNewLowVal = newHighNewLowVal
    def disableNewHighNewLowVal(self):
        self.newHighNewLowVal = 0
    def enableNewHighNewLowVal(self):
        self.newHighNewLowVal = self.defNewHighNewLowVal

    def setBollignerVal(self, bollignerVal):
        self.bollignerVal = bollignerVal
    def disableBollignerVal(self):
        self.bollignerVal = 0
    def enableBollignerVal(self):
        self.bollignerVal = self.defBollignerVal

    def setMomentumVal(self, momentumVal):
        self.momentumVal = momentumVal
    def disableMomentumVal(self):
        self.momentumVal = 0
    def enableMomentumVal(self):
        self.momentumVal = self.defMomentumVal

    def setRocVal(self, rocVal):
        self.rocVal = rocVal
    def disableRocVal(self):
        self.rocVal = 0
    def enableRocVal(self):
        self.rocVal = self.defRocVal

    def setCciVal(self, cciVal):
        self.cciVal = cciVal
    def disableCciVal(self):
        self.cciVal = 0
    def enableCciVal(self):
        self.cciVal = self.defCciVal

    def setRsiVal(self, rsiVal):
        self.rsiVal = rsiVal
    def disableRsiVal(self):
        self.rsiVal = 0
    def enableRsiVal(self):
        self.rsiVal = self.defRsiVal

    def setWilliamsVal(self, williamsVal):
        self.williamsVal = williamsVal
    def disableWilliamsVal(self):
        self.williamsVal = 0
    def enableWilliamsVal(self):
        self.williamsVal = self.defWilliamsVal

    """Luki"""
    #Wzrostowe

    def setRisingBreakawayGapVal(self, risingBreakawayGapVal):
        self.risingBreakawayGapVal = risingBreakawayGapVal
    def disableRisingBreakawayGapVal(self):
        self.risingBreakawayGapVal = 0
    def enableRisingBreakawayGapVal(self):
        self.risingBreakawayGapVal = self.defRisingBreakawayGapVal

    def setRisingContinuationGapVal(self, risingContinuationGapVal):
        self.risingContinuationGapVal = risingContinuationGapVal
    def disableRisingContinuationGapVal(self):
        self.risingContinuationGapVal = 0
    def enableRisingContinuationGapVal(self):
        self.risingContinuationGapVal = self.defRisingContinuationGapVal

    def setFallingExhaustionGapVal(self, fallingExhaustionGapVal):
        self.fallingExhaustionGapVal = fallingExhaustionGapVal
    def disableFallingExhaustionGapVal(self):
        self.fallingExhaustionGapVal = 0
    def enableFallingExhaustionGapVal(self):
        self.fallingExhaustionGapVal = self.defFallingExhaustionGapVal

    #Spadkowe

    def setFallingBreakawayGapVal(self, fallingBreakawayGapVal):
        self.fallingBreakawayGapVal = fallingBreakawayGapVal
    def disableFallingBreakawayGapVal(self):
        self.fallingBreakawayGapVal = 0
    def enableFallingBreakawayGapVal(self):
        self.fallingBreakawayGapVal = self.defFallingBreakawayGapVal

    def setRisingExhaustionGapVal(self, risingExhaustionGapVal):
        self.risingExhaustionGapVal = risingExhaustionGapVal
    def disableRisingExhaustionGapVal(self):
        self.risingExhaustionGapVal = 0
    def enableRisingExhaustionGapVal(self):
        self.risingExhaustionGapVal = self.defRisingExhaustionGapVal

    def setFallingContinuationGapVal(self, fallingContinuationGapVal):
        self.fallingContinuationGapVal = fallingContinuationGapVal
    def disableFallingContinuationGapVal(self):
        self.fallingContinuationGapVal = 0
    def enableFallingContinuationGapVal(self):
        self.fallingContinuationGapVal = self.defFallingContinuationGapVal

    """Formacje swiecowe"""
    #sygnal kupna

    def setBull3Val(self, bull3Val):
        self.bull3Val = bull3Val
    def disableBull3Val(self):
        self.bull3Val = 0
    def enableBull3Val(self):
        self.bull3Val = self.defBull3Val

    def setMornigStarVal(self, mornigStarVal):
        self.mornigStarVal = mornigStarVal
    def disableMornigStarVal(self):
        self.mornigStarVal = 0
    def enableMornigStarVal(self):
        self.mornigStarVal = self.defMornigStarVal

    def setPiercingVal(self, piercingVal):
        self.piercingVal = piercingVal
    def disablePiercingVal(self):
        self.piercingVal = 0
    def enablePiercingVal(self):
        self.piercingVal = self.defPiercingVal


    #sygnal sprzedazy

    def setBear3Val(self, bear3Val):
        self.bear3Val = bear3Val
    def disableBear3Val(self):
        self.bear3Val = 0
    def enableBear3Val(self):
        self.bear3Val = self.defBear3Val

    def setEveningStarVal(self, eveningStarVal):
        self.eveningStarVal = eveningStarVal
    def disableEveningStarVal(self):
        self.eveningStarVal = 0
    def enableEveningStarVal(self):
        self.eveningStarVal = self.defEveningStarVal

    def setDarkCloudVal(self, darkCloudVal):
        self.darkCloudVal = darkCloudVal
    def disableDarkCloudVal(self):
        self.darkCloudVal = 0
    def enableDarkCloudVal(self):
        self.darkCloudVal = self.defDarkCloudVal

    
    def resetCoefficients(self):
        self.positiveSignal = self.defPositiveSignal  
        self.negativeSignal = self.defNegativeSignal
        self.trendVal = self.defTrendVal
        self.headAndShouldersVal = self.defHeadAndShouldersVal
        self.tripleTopVal = self.defTripleTopVal
        self.risingWedgeVal = self.defRisingWedgeVal
        self.fallingTriangleVal = self.defFallingTriangleVal
        self.reversedHeadAndShouldersVal = self.defReversedHeadAndShouldersVal
        self.tripleBottomVal = self.defTripleBottomVal
        self.fallingWedgeVal = self.defFallingWedgeVal
        self.risingTriangleVal = self.defRisingTriangleVal
        self.symetricTriangleVal = self.defSymetricTriangleVal
        self.rectangleVal = self.defRectangleVal
        self.oscilatorsVal = self.defOscilatorsVal
        self.newHighNewLowVal = self.defNewHighNewLowVal
        self.bollignerVal = self.defBollignerVal
        self.momentumVal = self.defMomentumVal
        self.rocVal = self.defRocVal
        self.cciVal = self.defCciVal
        self.rsiVal = self.defRsiVal
        self.williamsVal = self.defWilliamsVal
        self.risingBreakawayGapVal = self.defRisingBreakawayGapVal
        self.risingContinuationGapVal = self.defRisingContinuationGapVal
        self.fallingExhaustionGapVal = self.defFallingExhaustionGapVal 
        self.fallingBreakawayGapVal = self.defFallingBreakawayGapVal
        self.risingExhaustionGapVal = self.defRisingExhaustionGapVal
        self.fallingContinuationGapVal = self.defFallingContinuationGapVal
        self.bull3Val = self.defBull3Val
        self.mornigStarVal = self.defMornigStarVal
        self.piercingVal = self.defPiercingVal
        self.bear3Val = self.defBear3Val
        self.eveningStarVal = self.defEveningStarVal
        self.darkCloudVal = self.defDarkCloudVal
        self.flagPennantVal = self.defFlagPennantVal
            
    def analyze(self):
          resultText = ''
          overallScore = 0
          print "The program will now analyse trends, selected chart patterns, candle patterns, indicators, oscillators and gaps\n"
          resultText = resultText + "The program will now analyse trends, selected chart patterns, candle patterns, indicators, oscillators and gaps\n"
          print "   (+) -> positive\n\t(0) -> neutral\n\t(-) -> negative signal\n"
          resultText = resultText + "   (+) -> positive\n   (0) -> neutral\n   (-) -> negative signal\n"
          overallScore += self.trendVal * trend.optimizedTrend(self.data.close)
          resultText = resultText + "\nResults of trend analysis\n"
          
          if overallScore > 0:
              print "   (+) the long term trend is rising\n"
              resultText = resultText + "   (+) the long term trend is rising\n"
          elif overallScore < 0:
              print "   (-) the long term trend is falling\n"
              resultText = resultText + "   (-) the long term trend is falling\n"
          else:
              print "   (0) the long term trend is neutral\n"
              resultText = resultText + "   (0) the long-term trend is neutral\n"

          print "\nThe program has identified the following chart patterns:\n"
          resultText = resultText + "\nThe program has identified the following chart patterns:\n"
          form = trend.lookForHeadAndShoulders(self.data.close, self.data.volume, 1)
          overallScore += form[0] * self.headAndShouldersVal
          if form[0] * self.headAndShouldersVal != 0:
              print "   (-) head and shoulders\n" + self.data.date[int(form[1][0])].strftime("%Y-%m-%d")+self.data.date[int(form[1][2])].strftime("%Y-%m-%d")
              resultText = resultText + "   (-) head and shoulders                    " + self.data.date[int(form[1][0])].strftime("%Y-%m-%d") + " - " + self.data.date[int(form[1][2])].strftime("%Y-%m-%d") + "\n"

          form = trend.lookForReversedHeadAndShoulders(self.data.close, self.data.volume, 1)
          overallScore += form[0] * self.reversedHeadAndShouldersVal
          if form[0] * self.reversedHeadAndShouldersVal != 0:
              print "   (+) reversed head and shoulders\n"
              resultText = resultText + "   (+) reversed head and shoulders     " + self.data.date[int(form[1][0])].strftime("%Y-%m-%d") + " - " + self.data.date[int(form[1][2])].strftime("%Y-%m-%d") + "\n"

          form = trend.lookForTripleTop(self.data.close, self.data.volume, 1)
          overallScore += form[0] * self.tripleTopVal
          if form[0] * self.tripleTopVal != 0:
              print "   (-) triple top\n"
              resultText = resultText + "   (-) triple top                                   " + self.data.date[int(form[1][0])].strftime("%Y-%m-%d") + " - " + self.data.date[int(form[1][2])].strftime("%Y-%m-%d") + "\n"

          form = trend.lookForTripleBottom(self.data.close, self.data.volume, 1)
          overallScore += form[0] * self.tripleBottomVal
          if form[0] * self.tripleBottomVal != 0:
              print "   (+) triple bottom\n"
              resultText = resultText + "   (+) triple bottom                             " + self.data.date[int(form[1][0])].strftime("%Y-%m-%d") + " - " + self.data.date[int(form[1][2])].strftime("%Y-%m-%d") + "\n"
          
          
          geometricFormations = trend.findGeometricFormations(self.data.close)
          for formation in geometricFormations:
              hasFound = 0
              if formation != None:
                  if formation[0] == 'rect':
                      overallScore += self.rectangleVal * formation[3]
                      if self.rectangleVal * formation[3] > 0:
                          print "   (+)  rising rectangle\n"
                          resultText = resultText + "   (+)  rising rectangle                      "
                          hasFound = 1
                      elif self.rectangleVal * formation[3] < 0:
                          print "   (-) falling rectangle\n"
                          resultText = resultText + "   (-) falling rectangle                      "
                          hasFound = 1
                  elif formation[0] == 'symmetric_triangle':
                      overallScore += self.symetricTriangleVal * formation[3]
                      if self.symetricTriangleVal * formation[3] > 0:
                          print "   (+) symmetric triangle - continuation of rising trend\n"
                          resultText = resultText + "   (+) symmetric triangle - continuation of rising trend     "
                          hasFound = 1
                      elif self.symetricTriangleVal * formation[3] < 0:
                          print "   (-) symmetric triangle - continuation of falling trend\n"
                          resultText = resultText + "   (-) symmetric triangle - continuation of falling trend     "
                          hasFound = 1
                  elif formation[0] == 'falling_triangle':
                      overallScore += self.fallingTriangleVal * formation[3]
                      if self.fallingTriangleVal * formation[3] != 0:
                          print "   (-) falling triangle\n"
                          resultText = resultText + "   (-) falling triangle                           "
                          hasFound = 1
                  elif formation[0] == 'rising_triangle':
                      overallScore += self.risingTriangleVal * formation[3]
                      if self.risingTriangleVal * formation[3] != 0:
                          print "   (+) rising triangle\n"
                          hasFound = 1
                          resultText = resultText + "   (+) rising triangle                           "
                  elif formation[0] == 'rising_wedge':
                      overallScore += self.risingWedgeVal * formation[3]
                      if self.risingWedgeVal * formation[3] != 0:
                          print "   (-) rising wedge\n"
                          resultText = resultText + "   (-) rising wedge     "
                          hasFound = 1
                  elif formation[0] == 'falling_wedge':
                      overallScore += self.fallingWedgeVal * formation[3]
                      if self.fallingWedgeVal * formation[3] != 0:

                          print "   (+) falling wedge\n"
                          resultText = resultText + "   (+) falling wedge     "
                          hasFound = 1
                  if hasFound:
                      resultText = resultText + self.data.date[int(formation[1][0])].strftime("%Y-%m-%d") + " - " + self.data.date[int(formation[1][2])].strftime("%Y-%m-%d") + "\n"   
                      
           
	  flags = trend.findFlagsAndPennants(self.data.close,self.data.volume, self.data.high, self.data.low)
	  if flags != None:
		overallScore += defFlagPennantVal * flags[1]
		if flags[1] < 0:
			print "(-) falling-trend flag/pennant"
			resultText = resultText + "(-) falling-trend flag/pennant"
		else:
			print "(+) rising-trend flag/pennant"
			resultText = resultText + "(+) rising-trend flag/pennant"


          gaps = candles.findGaps(self.data.high,self.data.low,self.data.close)
          for formation in gaps:
              if formation != None:
                  if formation[0][0] == 'rising_breakaway_gap':
                      overallScore += self.risingBreakawayGapVal * formation[1]
                      if self.risingBreakawayGapVal * formation[1] != 0:
                          print "   (+) rising breakaway gap\n"
                  elif formation[0][0] == 'rising_continuation_gap':
                      overallScore += self.risingContinuationGapVal * formation[1]
                      if self.risingContinuationGapVal * formation[1] != 0:
                          print "   (+) rising continuation gap\n"
                  elif formation[0][0] == 'rising_exhaustion_gap':
                      overallScore += self.risingExhaustionGapVal * formation[1]
                      if self.risingExhaustionGapVal * formation[1] != 0:
                          print "   (-) rising exhaustion gap\n"
                  elif formation[0][0] == 'falling_breakaway_gap':
                      overallScore += self.fallingBreakawayGapVal * formation[1]
                      if self.fallingBreakawayGapVal * formation[1] != 0:
                          print "   (-) falling breakaway gap\n"
                  elif formation[0][0] == 'falling_continuation_gap':
                      overallScore += self.fallingContinuationGapVal * formation[1]
                      if self.fallingContinuationGapVal * formation[1] != 0:
                          print "   (-) falling continuation gap\n"
                  elif formation[0][0] == 'falling_exhaustion_gap':
                      overallScore += self.fallingExhaustionGapVal * formation[1]
                      if self.fallingExhaustionGapVal * formation[1] != 0:
                          print "   (+) falling exhaustion gap\n"

          candleFormations = candles.findCandleFormations(self.data.open, self.data.high, self.data.low, self.data.close)
          for formation in candleFormations:
              if formation != None:
                  if formation[0][0] == 'bull3':
                      overallScore +=  bull3Val * formation[3]
                      if bull3Val * formation[3] != 0:
                          print "   (+) triple bull candle pattern\n"
                          resultText = resultText + "   (+) triple bull candle pattern\n"
                  elif formation[0][0] == 'morning_star':
                      overallScore += self.morningStarVal * formation[3]
                      if self.morningStarVal * formation[3] != 0:
                          print "   (+) morning star candle pattern\n"
                          resultText = resultText + "   (+) morning star candle pattern\n"
                  elif formation[0][0] == 'piercing':
                      overallScore += self.piercingVal * formation[3]
                      if self.piercingVal * formation[3] != 0:
                          print "   (+) piercing candle pattern\n"
                          resultText = resultText + "   (+) piercing candle pattern\n"
                  elif formation[0][0] == 'bear3':
                      overallScore += self.bear3Val * formation[3]
                      if bear3Val * formation[3] != 0:
                          print "   (-) triple bear candle pattern\n"
                          resultText = resultText + "   (-) triple bear candle pattern\n"
                  elif formation[0][0] == 'evening_star':
                      overallScore += self.eveningStarVal * formation[3]
                      if self.eveningStarVal * formation[3] != 0:
                          print "   (-) evening star candle pattern\n"
                          resultText = resultText + "   (-) evening star candle pattern\n"
                  elif formation[0][0] == 'dark_cloud':
                      overallScore += self.darkCloudVal * formation[3]
                      if self.darkCloudVal * formation[3] != 0:
                          print "   (-) dark cloud candle pattern\n"
                          resultText = resultText + "   (-) dark cloud candle pattern\n"

                          
          # score, oscilatorsAndIndicators = oscilators.oscillatorStrategy(array(self.data.close), array(self.data.high), array(self.data.low), min(10, len(self.data.close)))
          #           overallScore += self.newHighNewLowVal * oscilatorsAndIndicators[0]
          #           if self.newHighNewLowVal * oscilatorsAndIndicators[0] > 0:
          #               print "   (+) new high - new low index\n"
          #           elif self.newHighNewLowVal * oscilatorsAndIndicators[0] < 0:
          #               print "   (-) new high - new low index\n"
          # 
          #           overallScore += self.bollignerVal * oscilatorsAndIndicators[1]
          #           if self.bollignerVal * oscilatorsAndIndicators > 0:
          #               print "   (+) bolligner bounds\n"
          #           elif self.bollignerVal * oscilatorsAndIndicators < 0:
          #               print "   (-) bolligner bounds\n"
          # 
          #           overallScore += self.momentumVal * oscilatorsAndIndicators[2]
          #           if self.momentumVal * oscilatorsAndIndicators > 0:
          #               print "   (+) momentum oscillator\n"
          #           elif self.momentumVal * oscilatorsAndIndicators < 0:
          #               print "   (-) momentum oscillator\n"
          # 
          #           overallScore += self.rocVal * oscilatorsAndIndicators[3]
          #           if self.rocVal * oscilatorsAndIndicators[3] > 0:
          #               print "   (+) roc oscillator\n"
          #           elif self.rocVal * oscilatorsAndIndicators[3] < 0:
          #               print "   (-) roc oscillator\n"
          # 
          #           overallScore += self.cciVal * oscilatorsAndIndicators[4]
          #           if self.cciVal * oscilatorsAndIndicators[4] > 0:
          #               print "   (+) cci oscillator\n"
          #           elif self.cciVal * oscilatorsAndIndicators[4] < 0:
          #               print "   (-) cci oscillator\n"
          # 
          #           overallScore += self.rsiVal * oscilatorsAndIndicators[5]
          #           if self.rsiVal * oscilatorsAndIndicators[5] > 0:
          #               print "   (+) rsi oscillator\n"
          #           elif self.rsiVal * oscilatorsAndIndicators[5] < 0:
          #               print "   (-) rsi oscillator\n"
          # 
          #           overallScore += self.williamsVal * oscilatorsAndIndicators[6]
          #           if self.williamsVal * oscilatorsAndIndicators[6] > 0:
          #               print "   (+) williams oscillator\n"
          #           elif self.williamsVal * oscilatorsAndIndicators[6] < 0:
          #               print "   (-) williams oscillator\n"
          
          print "\n Overall score: ",overallScore, "\n"
          resultText = resultText + "\n Overall score: "+str(overallScore)+ "\n\n"
          if  overallScore > self.positiveSignal:
              print "The technical analysis has generated a positive signal, however a fundamental analysis should also be considered\n"
              resultText = resultText + "The technical analysis has generated a positive signal, however a fundamental analysis should also be considered\n"
          elif overallScore < self.negativeSignal:
              print "The technical analysis has generated a negative signal. If you own actives, you should consider selling them. However, a fundamental analysis should also be taken into account\n"
              resultText = resultText + "The technical analysis has generated a negative signal. If you own actives, you should consider selling them. However, a fundamental analysis should also be taken into account\n"
          else:
              print "The technical analysis has generated a neutral signal\n"
              resultText = resultText + "The technical analysis has generated a neutral signal\n"
          print "\n\nNO RESPONSIBILITY is taken by the authors of this software, for the accuracy of any predictions or the loss of any finance by anyone using this program. You may use this software at your own risk.\n"
          resultText = resultText + "\n\nNO RESPONSIBILITY is taken by the authors of this software, for the accuracy of any predictions or the loss of any finance by anyone using this program. You may use this software at your own risk.\n"
          return resultText
