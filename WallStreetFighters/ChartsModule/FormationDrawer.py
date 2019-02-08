# -*- coding: utf-8 -*-
import TechAnalysisModule.candles as candles
import TechAnalysisModule.trendAnalysis as trend


class FormationDrawer:
    """Klasa odpowiedzialna za rysowanie wybranych przez użytkownika formacji
    (przekazywanych w tablicy configuration) na wykresie."""
   
    defTrendColor = 'r'
    trendColor = defTrendColor
    defTrendLwidth = 2.0
    trendLwidth = defTrendLwidth
    defTrendLstyle = '-'
    trendLstyle = defTrendLstyle
    
    defHeadAndShouldersColor = 'm'
    headAndShouldersColor = 'm'
    defHeadAndShouldersLwidth = 2.0
    headAndShouldersLwidth = 2.0
    defHeadAndShouldersLstyle = '-'
    headAndShouldersLstyle = '-'
    
    defReversedHeadAndShouldersColor = 'c'
    reversedHeadAndShouldersColor = 'c'
    defReversedHeadAndShouldersLwidth = 2.0
    reversedHeadAndShouldersLwidth = 2.0
    defReversedHeadAndShouldersLstyle = '-'
    reversedHeadAndShouldersLstyle = '-'
    
    defTripleTopColor = 'y'
    tripleTopColor = 'y'
    defTripleTopLwidth = 2.0
    tripleTopLwidth = 2.0
    defTripleTopLstyle = '-'
    tripleTopLstyle = '-'
    
    defTripleBottomColor = 'b'
    tripleBottomColor = 'b'
    defTripleBottomLwidth = 2.0
    tripleBottomLwidth = 2.0
    defTripleBottomLstyle = '-'
    tripleBottomLstyle = '-'
    
    
    defRisingWedgeColor = 'r'
    risingWedgeColor = 'r'
    defRisingWedgeLwidth = 2.0
    risingWedgeLwidth = 2.0
    defRisingWedgeLstyle = '-'
    risingWedgeLstyle = '-'

    defFallingTriangleColor = 'r'
    fallingTriangleColor = 'r'
    defFallingTriangleLwidth = 2.0
    fallingTriangleLwidth = 2.0
    defFallingTriangleLstyle = '-'
    fallingTriangleLstyle = '-'

    defReversedHeadAndShouldersColor = 'm'
    reversedHeadAndShouldersColor = 'm'
    defReversedHeadAndShouldersLwidth = 2.0
    reversedHeadAndShouldersLwidth = 2.0
    defReversedHeadAndShouldersLstyle = '-'
    reversedHeadAndShouldersLstyle = '-'

    defTripleBottomColor = 'm'
    tripleBottomColor = 'm'
    defTripleBottomLwidth = 2.0
    tripleBottomLwidth = 2.0
    defTripleBottomLstyle = '-'
    tripleBottomLstyle = '-'

    defFallingWedgeColor = 'g'
    fallingWedgeColor = 'g'
    defFallingWedgeLwidth = 2.0
    fallingWedgeLwidth = 2.0
    defFallingWedgeLstyle = '-'
    fallingWedgeLstyle = '-'

    defRisingTriangleColor = 'g'
    risingTriangleColor = 'g'
    defRisingTriangleLwidth = 2.0
    risingTriangleLwidth = 2.0
    defRisingTriangleLstyle = '-'
    risingTriangleLstyle = '-'

    defSymetricTriangleColor = 'm'
    symetricTriangleColor = 'm'
    defSymetricTriangleLwidth = 2.0
    symetricTriangleLwidth = 2.0
    defSymetricTriangleLstyle = '-'
    symetricTriangleLstyle = '-'

    defRisingBreakawayGapColor = 'g'
    risingBreakawayGapColor = 'g'
    defRisingBreakawayGapLwidth = 2.0
    risingBreakawayGapLwidth = 2.0
    defRisingBreakawayGapLstyle = '-'
    risingBreakawayGapLstyle = '-'

    defRisingContinuationGapColor = 'g'
    risingContinuationGapColor = 'g'
    defRisingContinuationGapLwidth = 2.0
    risingContinuationGapLwidth = 2.0
    defRisingContinuationGapLstyle = '-'
    risingContinuationGapLstyle = '-'

    defRisingExhaustionGapColor = 'r'
    risingExhaustionGapColor = 'r'
    defRisingExhaustionGapLwidth = 2.0
    risingExhaustionGapLwidth = 2.0
    defRisingExhaustionGapLstyle = '-'
    risingExhaustionGapLstyle = '-'

    defFallingBreakawayGapColor = 'r'
    fallingBreakawayGapColor = 'r'
    defFallingBreakawayGapLwidth = 2.0
    fallingBreakawayGapLwidth = 2.0
    defFallingBreakawayGapLstyle = '-'
    fallingBreakawayGapLstyle = '-'

    defFallingContinuationGapColor = 'r'
    fallingContinuationGapColor = 'r'
    defFallingContinuationGapLwidth = 2.0
    fallingContinuationGapLwidth = 2.0
    defFallingContinuationGapLstyle = '-'
    fallingContinuationGapLstyle = '-'

    defFallingExhaustionGapColor = 'g'
    fallingExhaustionGapColor = 'g'
    defFallingExhaustionGapLwidth = 2.0
    fallingExhaustionGapLwidth = 2.0
    defFallingExhaustionGapLstyle = '-'
    fallingExhaustionGapLstyle = '-'

    defBear3Color = 'r'
    bear3Color = 'r'
    defBear3Lwidth = 2.0
    bear3Lwidth = 2.0
    defBear3Lstyle = '-'
    bear3Lstyle = '-'


    defBull3Color = 'g'
    bull3Color = 'g'
    defBull3Lwidth = 2.0
    bull3Lwidth = 2.0
    defBull3Lstyle = '-'
    bull3Lstyle = '-'

    defMornigStarColor = 'g'
    mornigStarColor = 'g'
    defMornigStarLwidth = 2.0
    mornigStarLwidth = 2.0
    defMornigStarLstyle = '-'
    mornigStarLstyle = '-'

    defEveningStarColor = 'r'
    eveningStarColor = 'r'
    defEveningStarLwidth = 2.0
    eveningStarLwidth = 2.0
    defEveningStarLstyle = '-'
    eveningStarLstyle = '-'

    defDarkCloudColor = 'r'
    darkCloudColor = 'r'
    defDarkCloudLwidth = 2.0
    darkCloudLwidth = 2.0
    defDarkCloudLstyle = '-'
    darkCloudLstyle = '-'

    defPiercingColor = 'g'
    piercingColor = 'g'
    defPiercingLwidth = 2.0
    piercingLwidth = 2.0
    defPiercingLstyle = '-'
    piercingLstyle = '-'
    defFlagPennantColor = 'm'
    flagPennantColor = 'm'
    defFlagPennantLwidth = 2.0
    flagPennantLwidth = 2.0
    defFlagPennantLstyle = '-'
    flagPennantLstyle = '-'
    strategy = None
    
    def __init__(self, chart, strategy = None):
        """chart = obiekt klasy Chart. Domyślnie ustawiamy pustą listę formacji."""
        self.chart = chart
        self.setFormations(strategy)
    
    
    def setTrendColor(self, trendColor):
        self.trendColor = trendColor

    def resetTrendColor(self):
        self.trendColor = self.defTrendColor

    def setTrendLwidth(self, trendLwidth):
        self.trendLwidth = trendLwidth

    def resetTrendLwidth(self):
        self.trendLwidth = self.defTrendLwidth

    def setTrendLstyle(self, trendLstyle):
        self.trendLstyle = trendLstyle

    def resetTrendLstyle(self):
        self.trendLstyle = self.defTrendLstyle


    def setHeadAndShouldersColor(self, headAndShouldersColor):
        self.headAndShouldersColor = headAndShouldersColor

    def resetHeadAndShouldersColor(self):
        self.headAndShouldersColor = self.defHeadAndShouldersColor

    def setHeadAndShouldersLwidth(self, headAndShouldersLwidth):
        self.headAndShouldersLwidth = headAndShouldersLwidth

    def resetHeadAndShouldersLwidth(self):
        self.headAndShouldersLwidth = self.defHeadAndShouldersLwidth

    def setHeadAndShouldersLstyle(self, headAndShouldersLstyle):
        self.headAndShouldersLstyle = headAndShouldersLstyle

    def resetHeadAndShouldersLstyle(self):
        self.headAndShouldersLstyle = self.defHeadAndShouldersLstyle


    def setTripleTopColor(self, tripleTopColor):
        self.tripleTopColor = tripleTopColor

    def resetTripleTopColor(self):
        self.tripleTopColor = self.defTripleTopColor

    def setTripleTopLwidth(self, tripleTopLwidth):
        self.tripleTopLwidth = tripleTopLwidth

    def resetTripleTopLwidth(self):
        self.tripleTopLwidth = self.defTripleTopLwidth

    def setTripleTopLstyle(self, tripleTopLstyle):
        self.tripleTopLstyle = tripleTopLstyle

    def resetTripleTopLstyle(self):
        self.tripleTopLstyle = self.defTripleTopLstyle


    def setRisingWedgeColor(self, risingWedgeColor):
        self.risingWedgeColor = risingWedgeColor

    def resetRisingWedgeColor(self):
        self.risingWedgeColor = self.defRisingWedgeColor

    def setRisingWedgeLwidth(self, risingWedgeLwidth):
        self.risingWedgeLwidth = risingWedgeLwidth

    def resetRisingWedgeLwidth(self):
        self.risingWedgeLwidth = self.defRisingWedgeLwidth

    def setRisingWedgeLstyle(self, risingWedgeLstyle):
        self.risingWedgeLstyle = risingWedgeLstyle

    def resetRisingWedgeLstyle(self):
        self.risingWedgeLstyle = self.defRisingWedgeLstyle


    def setFallingTriangleColor(self, fallingTriangleColor):
        self.fallingTriangleColor = fallingTriangleColor

    def resetFallingTriangleColor(self):
        self.fallingTriangleColor = self.defFallingTriangleColor

    def setFallingTriangleLwidth(self, fallingTriangleLwidth):
        self.fallingTriangleLwidth = fallingTriangleLwidth

    def resetFallingTriangleLwidth(self):
        self.fallingTriangleLwidth = self.defFallingTriangleLwidth

    def setFallingTriangleLstyle(self, fallingTriangleLstyle):
        self.fallingTriangleLstyle = fallingTriangleLstyle

    def resetFallingTriangleLstyle(self):
        self.fallingTriangleLstyle = self.defFallingTriangleLstyle


    def setReversedHeadAndShouldersColor(self, reversedHeadAndShouldersColor):
        self.reversedHeadAndShouldersColor = reversedHeadAndShouldersColor

    def resetReversedHeadAndShouldersColor(self):
        self.reversedHeadAndShouldersColor = self.defReversedHeadAndShouldersColor

    def setReversedHeadAndShouldersLwidth(self, reversedHeadAndShouldersLwidth):
        self.reversedHeadAndShouldersLwidth = reversedHeadAndShouldersLwidth

    def resetReversedHeadAndShouldersLwidth(self):
        self.reversedHeadAndShouldersLwidth = self.defReversedHeadAndShouldersLwidth

    def setReversedHeadAndShouldersLstyle(self, reversedHeadAndShouldersLstyle):
        self.reversedHeadAndShouldersLstyle = reversedHeadAndShouldersLstyle

    def resetReversedHeadAndShouldersLstyle(self):
        self.reversedHeadAndShouldersLstyle = self.defReversedHeadAndShouldersLstyle


    def setTripleBottomColor(self, tripleBottomColor):
        self.tripleBottomColor = tripleBottomColor

    def resetTripleBottomColor(self):
        self.tripleBottomColor = self.defTripleBottomColor

    def setTripleBottomLwidth(self, tripleBottomLwidth):
        self.tripleBottomLwidth = tripleBottomLwidth

    def resetTripleBottomLwidth(self):
        self.tripleBottomLwidth = self.defTripleBottomLwidth

    def setTripleBottomLstyle(self, tripleBottomLstyle):
        self.tripleBottomLstyle = tripleBottomLstyle

    def resetTripleBottomLstyle(self):
        self.tripleBottomLstyle = self.defTripleBottomLstyle


    def setFallingWedgeColor(self, fallingWedgeColor):
        self.fallingWedgeColor = fallingWedgeColor

    def resetFallingWedgeColor(self):
        self.fallingWedgeColor = self.defFallingWedgeColor

    def setFallingWedgeLwidth(self, fallingWedgeLwidth):
        self.fallingWedgeLwidth = fallingWedgeLwidth

    def resetFallingWedgeLwidth(self):
        self.fallingWedgeLwidth = self.defFallingWedgeLwidth

    def setFallingWedgeLstyle(self, fallingWedgeLstyle):
        self.fallingWedgeLstyle = fallingWedgeLstyle

    def resetFallingWedgeLstyle(self):
        self.fallingWedgeLstyle = self.defFallingWedgeLstyle


    def setRisingTriangleColor(self, risingTriangleColor):
        self.risingTriangleColor = risingTriangleColor

    def resetRisingTriangleColor(self):
        self.risingTriangleColor = self.defRisingTriangleColor

    def setRisingTriangleLwidth(self, risingTriangleLwidth):
        self.risingTriangleLwidth = risingTriangleLwidth

    def resetRisingTriangleLwidth(self):
        self.risingTriangleLwidth = self.defRisingTriangleLwidth

    def setRisingTriangleLstyle(self, risingTriangleLstyle):
        self.risingTriangleLstyle = risingTriangleLstyle

    def resetRisingTriangleLstyle(self):
        self.risingTriangleLstyle = self.defRisingTriangleLstyle


    def setSymetricTriangleColor(self, symetricTriangleColor):
        self.symetricTriangleColor = symetricTriangleColor

    def resetSymetricTriangleColor(self):
        self.symetricTriangleColor = self.defSymetricTriangleColor

    def setSymetricTriangleLwidth(self, symetricTriangleLwidth):
        self.symetricTriangleLwidth = symetricTriangleLwidth

    def resetSymetricTriangleLwidth(self):
        self.symetricTriangleLwidth = self.defSymetricTriangleLwidth

    def setSymetricTriangleLstyle(self, symetricTriangleLstyle):
        self.symetricTriangleLstyle = symetricTriangleLstyle

    def resetSymetricTriangleLstyle(self):
        self.symetricTriangleLstyle = self.defSymetricTriangleLstyle


    def setRisingBreakawayGapColor(self, risingBreakawayGapColor):
        self.risingBreakawayGapColor = risingBreakawayGapColor

    def resetRisingBreakawayGapColor(self):
        self.risingBreakawayGapColor = self.defRisingBreakawayGapColor

    def setRisingBreakawayGapLwidth(self, risingBreakawayGapLwidth):
        self.risingBreakawayGapLwidth = risingBreakawayGapLwidth

    def resetRisingBreakawayGapLwidth(self):
        self.risingBreakawayGapLwidth = self.defRisingBreakawayGapLwidth

    def setRisingBreakawayGapLstyle(self, risingBreakawayGapLstyle):
        self.risingBreakawayGapLstyle = risingBreakawayGapLstyle

    def resetRisingBreakawayGapLstyle(self):
        self.risingBreakawayGapLstyle = self.defRisingBreakawayGapLstyle


    def setRisingContinuationGapColor(self, risingContinuationGapColor):
        self.risingContinuationGapColor = risingContinuationGapColor

    def resetRisingContinuationGapColor(self):
        self.risingContinuationGapColor = self.defRisingContinuationGapColor

    def setRisingContinuationGapLwidth(self, risingContinuationGapLwidth):
        self.risingContinuationGapLwidth = risingContinuationGapLwidth

    def resetRisingContinuationGapLwidth(self):
        self.risingContinuationGapLwidth = self.defRisingContinuationGapLwidth

    def setRisingContinuationGapLstyle(self, risingContinuationGapLstyle):
        self.risingContinuationGapLstyle = risingContinuationGapLstyle

    def resetRisingContinuationGapLstyle(self):
        self.risingContinuationGapLstyle = self.defRisingContinuationGapLstyle


    def setRisingExhaustionGapColor(self, risingExhaustionGapColor):
        self.risingExhaustionGapColor = risingExhaustionGapColor

    def resetRisingExhaustionGapColor(self):
        self.risingExhaustionGapColor = self.defRisingExhaustionGapColor

    def setRisingExhaustionGapLwidth(self, risingExhaustionGapLwidth):
        self.risingExhaustionGapLwidth = risingExhaustionGapLwidth

    def resetRisingExhaustionGapLwidth(self):
        self.risingExhaustionGapLwidth = self.defRisingExhaustionGapLwidth

    def setRisingExhaustionGapLstyle(self, risingExhaustionGapLstyle):
        self.risingExhaustionGapLstyle = risingExhaustionGapLstyle

    def resetRisingExhaustionGapLstyle(self):
        self.risingExhaustionGapLstyle = self.defRisingExhaustionGapLstyle


    def setFallingBreakawayGapColor(self, fallingBreakawayGapColor):
        self.fallingBreakawayGapColor = fallingBreakawayGapColor

    def resetFallingBreakawayGapColor(self):
        self.fallingBreakawayGapColor = self.defFallingBreakawayGapColor

    def setFallingBreakawayGapLwidth(self, fallingBreakawayGapLwidth):
        self.fallingBreakawayGapLwidth = fallingBreakawayGapLwidth

    def resetFallingBreakawayGapLwidth(self):
        self.fallingBreakawayGapLwidth = self.defFallingBreakawayGapLwidth

    def setFallingBreakawayGapLstyle(self, fallingBreakawayGapLstyle):
        self.fallingBreakawayGapLstyle = fallingBreakawayGapLstyle

    def resetFallingBreakawayGapLstyle(self):
        self.fallingBreakawayGapLstyle = self.defFallingBreakawayGapLstyle


    def setFallingContinuationGapColor(self, fallingContinuationGapColor):
        self.fallingContinuationGapColor = fallingContinuationGapColor

    def resetFallingContinuationGapColor(self):
        self.fallingContinuationGapColor = self.defFallingContinuationGapColor

    def setFallingContinuationGapLwidth(self, fallingContinuationGapLwidth):
        self.fallingContinuationGapLwidth = fallingContinuationGapLwidth

    def resetFallingContinuationGapLwidth(self):
        self.fallingContinuationGapLwidth = self.defFallingContinuationGapLwidth

    def setFallingContinuationGapLstyle(self, fallingContinuationGapLstyle):
        self.fallingContinuationGapLstyle = fallingContinuationGapLstyle

    def resetFallingContinuationGapLstyle(self):
        self.fallingContinuationGapLstyle = self.defFallingContinuationGapLstyle


    def setFallingExhaustionGapColor(self, fallingExhaustionGapColor):
        self.fallingExhaustionGapColor = fallingExhaustionGapColor

    def resetFallingExhaustionGapColor(self):
        self.fallingExhaustionGapColor = self.defFallingExhaustionGapColor

    def setFallingExhaustionGapLwidth(self, fallingExhaustionGapLwidth):
        self.fallingExhaustionGapLwidth = fallingExhaustionGapLwidth

    def resetFallingExhaustionGapLwidth(self):
        self.fallingExhaustionGapLwidth = self.defFallingExhaustionGapLwidth

    def setFallingExhaustionGapLstyle(self, fallingExhaustionGapLstyle):
        self.fallingExhaustionGapLstyle = fallingExhaustionGapLstyle

    def resetFallingExhaustionGapLstyle(self):
        self.fallingExhaustionGapLstyle = self.defFallingExhaustionGapLstyle


    def setBear3Color(self, bear3Color):
        self.bear3Color = bear3Color

    def resetBear3Color(self):
        self.bear3Color = self.defBear3Color

    def setBear3Lwidth(self, bear3Lwidth):
        self.bear3Lwidth = bear3Lwidth

    def resetBear3Lwidth(self):
        self.bear3Lwidth = self.defBear3Lwidth

    def setBear3Lstyle(self, bear3Lstyle):
        self.bear3Lstyle = bear3Lstyle

    def resetBear3Lstyle(self):
        self.bear3Lstyle = self.defBear3Lstyle




    def setBull3Color(self, bull3Color):
        self.bull3Color = bull3Color

    def resetBull3Color(self):
        self.bull3Color = self.defBull3Color

    def setBull3Lwidth(self, bull3Lwidth):
        self.bull3Lwidth = bull3Lwidth

    def resetBull3Lwidth(self):
        self.bull3Lwidth = self.defBull3Lwidth

    def setBull3Lstyle(self, bull3Lstyle):
        self.bull3Lstyle = bull3Lstyle

    def resetBull3Lstyle(self):
        self.bull3Lstyle = self.defBull3Lstyle



    def setMornigStarColor(self, mornigStarColor):
        self.mornigStarColor = mornigStarColor

    def resetMornigStarColor(self):
        self.mornigStarColor = self.defMornigStarColor

    def setMornigStarLwidth(self, mornigStarLwidth):
        self.mornigStarLwidth = mornigStarLwidth

    def resetMornigStarLwidth(self):
        self.mornigStarLwidth = self.defMornigStarLwidth

    def setMornigStarLstyle(self, mornigStarLstyle):
        self.mornigStarLstyle = mornigStarLstyle

    def resetMornigStarLstyle(self):
        self.mornigStarLstyle = self.defMornigStarLstyle


    def setEveningStarColor(self, eveningStarColor):
        self.eveningStarColor = eveningStarColor

    def resetEveningStarColor(self):
        self.eveningStarColor = self.defEveningStarColor

    def setEveningStarLwidth(self, eveningStarLwidth):
        self.eveningStarLwidth = eveningStarLwidth

    def resetEveningStarLwidth(self):
        self.eveningStarLwidth = self.defEveningStarLwidth

    def setEveningStarLstyle(self, eveningStarLstyle):
        self.eveningStarLstyle = eveningStarLstyle

    def resetEveningStarLstyle(self):
        self.eveningStarLstyle = self.defEveningStarLstyle


    def setDarkCloudColor(self, darkCloudColor):
        self.darkCloudColor = darkCloudColor

    def resetDarkCloudColor(self):
        self.darkCloudColor = self.defDarkCloudColor

    def setDarkCloudLwidth(self, darkCloudLwidth):
        self.darkCloudLwidth = darkCloudLwidth

    def resetDarkCloudLwidth(self):
        self.darkCloudLwidth = self.defDarkCloudLwidth

    def setDarkCloudLstyle(self, darkCloudLstyle):
        self.darkCloudLstyle = darkCloudLstyle

    def resetDarkCloudLstyle(self):
        self.darkCloudLstyle = self.defDarkCloudLstyle


    def setPiercingColor(self, piercingColor):
        self.piercingColor = piercingColor

    def resetPiercingColor(self):
        self.piercingColor = self.defPiercingColor

    def setPiercingLwidth(self, piercingLwidth):
        self.piercingLwidth = piercingLwidth

    def resetPiercingLwidth(self):
        self.piercingLwidth = self.defPiercingLwidth

    def setPiercingLstyle(self, piercingLstyle):
        self.piercingLstyle = piercingLstyle

    def resetPiercingLstyle(self):
        self.piercingLstyle = self.defPiercingLstyle

    def setFlagPennantColor(self, flagPennantColor):
        self.flagPennantColor = flagPennantColor

    def resetFlagPennantColor(self):
        self.flagPennantColor = self.defFlagPennantColor

    def setFlagPennantLwidth(self, flagPennantLwidth):
        self.flagPennantLwidth = flagPennantLwidth

    def resetFlagPennantLwidth(self):
        self.flagPennantLwidth = self.defFlagPennantLwidth

    def setFlagPennantLstyle(self, flagPennantLstyle):
        self.flagPennantLstyle = flagPennantLstyle

    def resetFlagPennantLstyle(self):
        self.flagPennantLstyle = self.defFlagPennantLstyle

    
    def setFormations(self, s):
        """Ustawiamy listę formacji, które będziemy rysować, poprzez przekazanie
        obiektu klasy Strategy. Narysowane zostaną formacje o niezerowej wartości"""                
        self.configuration = {}
        if s == None:
            return
        self.strategy = s
        if abs(s.trendVal)>0:
            self.configuration['trend'] = (self.trendColor,self.trendLwidth,self.trendLstyle)
        if abs(s.headAndShouldersVal)>0:
            self.configuration['head_shoulders'] = (self.headAndShouldersColor,self.headAndShouldersLwidth,self.headAndShouldersLstyle)
        if abs(s.tripleTopVal)>0:
            self.configuration['triple_top'] = (self.tripleTopColor,self.tripleTopLwidth,self.tripleTopLstyle)        
        if abs(s.risingWedgeVal)>0:
            self.configuration['rising_wedge'] = (self.risingWedgeColor,self.risingWedgeLwidth,self.risingWedgeLstyle)        
        if abs(s.fallingTriangleVal)>0:
            self.configuration['falling_triangle'] = (self.fallingTriangleColor,self.fallingTriangleLwidth,self.fallingTriangleLstyle)        
        if abs(s.reversedHeadAndShouldersVal)>0:
            self.configuration['reversed_head_shoulders'] = (self.reversedHeadAndShouldersColor,self.reversedHeadAndShouldersLwidth,self.reversedHeadAndShouldersLstyle)        
        if abs(s.tripleBottomVal)>0:
            self.configuration['triple_bottom'] = (self.tripleBottomColor,self.tripleBottomLwidth,self.tripleBottomLstyle)        
        if abs(s.fallingWedgeVal)>0:
            self.configuration['falling_wedge'] = (self.fallingWedgeColor,self.fallingWedgeLwidth,self.fallingWedgeLstyle)                        
        if abs(s.risingTriangleVal)>0:
            self.configuration['rising_triangle'] = (self.risingTriangleColor,self.risingTriangleLwidth,self.risingTriangleLstyle)                                                                                          
        if abs(s.symetricTriangleVal)>0:
            self.configuration['symmetric_triangle'] = (self.symetricTriangleColor,self.symetricTriangleLwidth,self.symetricTriangleLstyle)                                                                                          
        if abs(s.risingBreakawayGapVal)>0:
            self.configuration['rising_breakaway_gap'] = (self.risingBreakawayGapColor,self.risingBreakawayGapLwidth,self.risingBreakawayGapLstyle)                                                                                          
        if abs(s.risingContinuationGapVal)>0:
            self.configuration['rising_continuation_gap'] = (self.risingContinuationGapColor,self.risingContinuationGapLwidth,self.risingContinuationGapLstyle)                                                                                          
        if abs(s.risingExhaustionGapVal)>0:
            self.configuration['rising_exhaustion_gap'] = (self.risingExhaustionGapColor,self.risingExhaustionGapLwidth,self.risingExhaustionGapLstyle)                                                                                          
        if abs(s.fallingBreakawayGapVal)>0:
            self.configuration['falling_breakaway_gap'] = (self.fallingBreakawayGapColor,self.fallingBreakawayGapLwidth,self.fallingBreakawayGapLstyle)                                                                                                  
        if abs(s.fallingContinuationGapVal)>0:
            self.configuration['falling_breakaway_gap'] = (self.fallingContinuationGapColor,self.fallingContinuationGapLwidth,self.fallingContinuationGapLstyle)                                                                                          
        if abs(s.fallingExhaustionGapVal)>0:
            self.configuration['falling_continuation_gap'] = (self.fallingExhaustionGapColor,self.fallingExhaustionGapLwidth,self.fallingExhaustionGapLstyle)                                                                                          
        if abs(s.bull3Val)>0:
            self.configuration['bull3'] = (self.bull3Color,self.bull3Lwidth,self.bull3Lstyle)                                                                                                      
        if abs(s.bear3Val)>0:
            self.configuration['bear3'] = (self.bear3Color,self.bear3Lwidth,self.bear3Lstyle)                                                                                          
        if abs(s.mornigStarVal)>0:
            self.configuration['morning_star'] = (self.mornigStarColor,self.mornigStarLwidth,self.mornigStarLstyle)                                                                                          
        if abs(s.eveningStarVal)>0:
            self.configuration['evening_star'] = (self.eveningStarColor,self.eveningStarLwidth,self.eveningStarLstyle)                                                                                                  
        if abs(s.darkCloudVal)>0:
            self.configuration['dark_cloud'] = (self.darkCloudColor,self.darkCloudLwidth,self.darkCloudLstyle)                                                                                          
        if abs(s.piercingVal)>0:
            self.configuration['piercing'] = (self.piercingColor,self.piercingLwidth,self.piercingLstyle) 
        if abs(s.flagPennantVal)>0:
            self.configuration['FlagOrPennant'] = (self.flagPennantColor, self.flagPennantLwidth, self.flagPennantLstyle)
                

    def drawFormations(self):
        """Rysujemy formacje, które są zdefiniowane w strategy."""
        if self.strategy == None:
            return
        data = self.chart.getData()        
        geoForm = ['rect', 'symmetric_triangle', 'rising_triangle', 'falling_triangle',
                'rising_wedge', 'falling_wedge']         
        candleForm = ['bull3','bear3','morning_star','evening_star','piercing','dark_cloud']        
        gaps = ['rising_breakaway_gap','rising_continuation_gap','rising_exhaustion_gap',
              'falling_breakaway_gap','falling_continuation_gap','falling_exhaustion_gap']        
        fandp = ['risingTrendFlagOrPennant','fallingTrendFlagOrPennant', 'FlagOrPennant']
        self.chart.clearLines()
        self.chart.clearRectangles()
        computedCandle = False
        computedGeo = False
        computedGaps = False
        computedFandp = False
        for name, values in self.configuration.iteritems():            
            if name in geoForm:
                if not computedGeo:
                    foundGeo = trend.findGeometricFormations(data.close)
                    computedGeo = True
                for formation in foundGeo:
                    if name == formation[0]:
                        self.drawGeometricFormation(formation,values[0],values[1],values[2])
            elif name in candleForm:
                if not computedCandle:
                    foundCandle = candles.findCandleFormations(data.open, data.high, data.low, data.close)
                    computedCandle = True
                for formation in foundCandle:
                    if name == formation[0]:
                        self.drawCandleFormation(formation,values[0],values[1],values[2])
            elif name in gaps:
                if not computedGaps:
                    foundGaps = candles.findGaps(data.high, data.low, data.close)
                    computedGaps = True
                for gapsList in foundGaps:
                    for gap in gapsList:
                        if name == gap[0]:
                            self.drawGap(gap,values[0],values[1],values[2])
            elif name in fandp:
                if not computedFandp:
                    foundFandp = flags = trend.findFlagsAndPennants(self.chart.data.close,self.chart.data.volume, self.chart.data.high, self.chart.data.low)
                    computedFandp = True
                if name == 'FlagOrPennant':
                    self.drawFlagAndPennant(foundFandp,values[0],values[1],values[2])                 
            elif name == 'trend':
                self.drawTrend(values[0],values[1],values[2])
            elif name == 'rate_lines':
                self.drawRateLines(values[0],values[1],values[2])        
            elif name == 'head_shoulders':
                neckline = trend.lookForHeadAndShoulders(self.chart.data.close, self.chart.data.volume)
                self.drawHST(neckline, values[0],values[1],values[2])
            elif name == 'reversed_head_shoulders':   
                neckline = trend.lookForReversedHeadAndShoulders(self.chart.data.close, self.chart.data.volume)
                self.drawHST(neckline, values[0],values[1],values[2])
            elif name == 'triple_top':
                neckline = trend.lookForTripleTop(self.chart.data.close, self.chart.data.volume)
                self.drawHST(neckline, values[0],values[1],values[2])
            elif name == 'triple_bottom':
                neckline = trend.lookForTripleBottom(self.chart.data.close, self.chart.data.volume)
                self.drawHST(neckline, values[0],values[1],values[2])
            # ...
    
    def drawGeometricFormation(self,form,color = 'r',lwidth = 1.0,lstyle = '--'):        
        self.chart.drawLine(form[1][0], form[1][1], form[1][2], form[1][3], 
                            color, lwidth, lstyle)
        self.chart.drawLine(form[2][0], form[2][1], form[2][2], form[2][3], 
                            color, lwidth, lstyle)

    def drawCandleFormation(self,formation,color,lwidth,lstyle):                                
        x = formation[1]-0.5
        y = 0.97*min(self.chart.data.low[formation[1]],self.chart.data.low[formation[2]])
        width = formation[2]-formation[1]+1
        height = 1.06*(max((self.chart.data.high[formation[1]],self.chart.data.high[formation[2]]))
                    -min((self.chart.data.low[formation[1]],self.chart.data.low[formation[2]])))           
        self.chart.drawRectangle(x,y,width,height,color,lwidth,lstyle)     
        
    
    def drawGap(self,gap,color,lwidth,lstyle):        
        x = gap[1]
        width = 1
        data = self.chart.getData()
        if("rising" in gap[0]):
            y = data.high[gap[1]]            
            height = data.low[gap[1]+1]-data.high[gap[1]]
        else:
            y = data.high[gap[1]+1]            
            height = data.low[gap[1]]-data.high[gap[1]+1]
        self.chart.drawRectangle(x,y,width,height,color,lwidth,lstyle)
    
    #head and shoulders /reversed hs, triple top/botom
    def drawHST(self,neckLine,color,lwidth,lstyle): 
        if (neckLine[0] != neckLine[2]):
            self.chart.drawLine(neckLine[0], neckLine[1], neckLine[2], neckLine[3], color, lwidth, lstyle)
    
    def drawFlagAndPennant(self,formation,color,lwidth,lstyle):
        if formation != None:
		self.chart.drawLine(formation[2][0], formation[2][1], formation[2][2], formation[2][3], color, lwidth, lstyle)
		self.chart.drawLine(formation[2][0], formation[2][1], formation[2][3], formation[2][4], color, lwidth, lstyle)
 
    def drawTrend(self,color,lwidth,lstyle):
        data = self.chart.getData()
        sup, res = trend.getChannelLines(self.chart.data.close)
        self.chart.drawLine(sup[0][1], sup[0][0], sup[len(sup)-1][1], sup[len(sup)-1][0], 'g', lwidth, lstyle)
        self.chart.drawLine(res[0][1], res[0][0], res[len(res)-1][1], res[len(res)-1][0], 'r', lwidth, lstyle)
        if len(data.close) > 30:
            sup, res = trend.getChannelLines(self.chart.data.close, 1, 2)
            self.chart.drawLine(sup[0][1], sup[0][0], sup[len(sup)-1][1], sup[len(sup)-1][0], 'g', 2*lwidth, lstyle)
            self.chart.drawLine(res[0][1], res[0][0], res[len(res)-1][1], res[len(res)-1][0], 'r', 2*lwidth, lstyle)
        
    
    def drawRateLines(self,color,lwidth,lstyle):        
        data = self.chart.getData()
        values = trend.rateLines(array(data.close),0.38,0.62)
        print values
        self.chart.drawLine(values[0][0],values[0][1],values[0][2],values[0][3],color,lwidth,lstyle)
        self.chart.drawLine(values[1][0],values[1][1],values[1][2],values[1][3],color,lwidth,lstyle)
        self.chart.drawLine(values[2][0],values[2][1],values[2][2],values[2][3],color,lwidth,lstyle)           
