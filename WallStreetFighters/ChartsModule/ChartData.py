# coding: utf-8
__author__="Andrzej Smoliński"
__date__ ="$2012-03-24 12:05:55$"

import datetime
import matplotlib.dates as mdates
import numpy as np
import TechAnalysisModule.oscilators as indicators
import DataParserModule.dataParser as parser
from copy import deepcopy


class ChartData:
    """Ta klasa służy mi jako pomost pomiędzy tym, czego potrzebuje wykres, a tym
    co daje mi FinancialObject Marcina. Czwarty parametr określa czy obliczamy dane
    do wykresu zwykłego, czy do porównującego. Wersja porównująca wykresy potrzebuje
    znacznie mniej danych (jedynie procentowa zmiana kursów jednego i drugiego instrumentu
    w czasie), podczas gdy zwykły chart pobiera OHLC"""     
    defaultSettings={'avgDur':20, 'RSIDur':10, 'CCIDur':10, 'bollingerD':2.0,
                        'ROCDur':10, 'momentumDur':10, 'williamsDur': 10}
    
    def __init__(self, finObj, start=None, end=None, step='monthly', settings=defaultSettings, compare=False):
        self.settings = settings
        if start>=end:
            self.corrupted=True
            return        
        self.step=(step)
	self.fullArray=finObj.getArray(step)
        if(start==None):
            start=datetime.datetime.strptime(self.fullArray(step)['date'][0],"%Y-%m-%d")
        if(end==None):
            end=datetime.datetime.strptime(self.fullArray(step)['date'][-1],"%Y-%m-%d")      
        indexes=finObj.getIndex(start.date(),end.date(),step)
        dataArray=self.fullArray[indexes[0]:indexes[1]:1]                              
        if(len(dataArray)==0):
            self.corrupted=True
            return
        self.name=finObj.name
        self.date = []
        self.close=dataArray['close'].tolist()
        for date in dataArray['date']:
            self.date.append(datetime.datetime.strptime(date,"%Y-%m-%d"))
        if(compare==False):                        
            #potrzebujemy pełnej tabeli do obliczania wskaźników                      
            self.open=dataArray['open'].tolist()            
            self.low=dataArray['low'].tolist()
            self.high=dataArray['high'].tolist()
            self.volume=dataArray['volume'].tolist()   
            if(not(len(self.low)==len(self.high)==len(self.open)==len(self.close)
                    ==len(self.volume)==len(self.date))):
                self.corrupted=True
                return
            #dane w formacie dla candlesticka
            self.quotes=[]
	    a = datetime.datetime.now()
            for i in range(len(dataArray)):
                time=float(i)
                open=self.open[i] 
                close=self.close[i]
                high=self.high[i]
                low=self.low[i]
                self.quotes.append((time, open, close, high, low))               
        else:
            self.percentChng=[]
            firstValue=self.close[0]
            for value in self.close:                
                change=100+(value-firstValue)*100.0/firstValue                                
                self.percentChng.append(change)
            if(len(self.date)!=len(self.percentChng)):
                self.corrupted=True
                return
        self.corrupted=False
    
    def getEarlierValues(self, length, type='close'):
        """Funkcja używana do wskaźników, które potrzebują wartości z okresu
        wcześniejszego niż dany okres (czyli chyba do wszystkich). Jeśli wcześniejsze
        wartości istnieją, są one pobierane z tablicy self.fullArray. W przeciwnym wypadku
        kopiujemy wartość początkową na wcześniejsze wartości.
        length = ilość dodatkowych wartości, które potrzebujemy"""
        if(type=='open'):
            array=self.open[:]
        elif(type=='close'):
            array=self.open[:]
        elif(type=='high'):
            array=self.high[:]
        elif(type=='low'):
            array=self.low[:]
        else:
            return None
        startIdx=self.fullArray['date'].tolist().index(self.date[0].strftime("%Y-%m-%d"))
        first=array[0]
        if(startIdx-length < 0):
            for i in range (length-startIdx):
                array.insert(0,first)            
            for i in range (startIdx):
                array.insert(0,self.fullArray[type][i])                                
        else:
            for i in range (length):
                array.insert(0,self.fullArray[type][startIdx-length+i])
        return array
    
    #poniższe funkcje obliczają wartości wskaźników zdefiniowanych w TechAnalysisModule,
    #z uwzględnieniem ograniczeń na długość danych
    
    def momentum(self):
        duration=self.settings['momentumDur']
        array=self.getEarlierValues(duration)
        return indicators.momentum(np.array(array), duration)
    
    def RSI(self):
        duration=self.settings['RSIDur']        
        array=self.getEarlierValues(duration)        
        return indicators.RSI(np.array(array), duration)
    
    def CCI(self):
        duration=self.settings['CCIDur']
        highs=np.array(self.getEarlierValues(duration-1,'high'))
        lows=np.array(self.getEarlierValues(duration-1,'low'))
        closes=np.array(self.getEarlierValues(duration-1,'close'))        
        return indicators.CCI(closes,lows,highs,duration)        
    
    def ROC(self):
        duration=self.settings['ROCDur']
        array=self.getEarlierValues(duration)
        return indicators.ROC(np.array(array), duration)
    
    def williams(self):
        duration=self.settings['williamsDur']
        highs=np.array(self.getEarlierValues(duration,'high'))
        lows=np.array(self.getEarlierValues(duration,'low'))
        closes=np.array(self.getEarlierValues(duration,'close'))        
        return indicators.williamsOscilator(highs,lows,closes,duration)
    
    def movingAverage(self, type):
        duration=self.settings['avgDur']
        if type=='SMA':
            type=1
        elif type=='WMA':
            type=2
        elif type=='EMA':
            type=3
        else:
            return None
        length=len(self.close)
        if(length>=2*(duration+1)):
            array=self.getEarlierValues(length)                
            return indicators.movingAverage(np.array(array),duration,type)
        else:
            array=self.getEarlierValues(2*(duration+1)+length%2)
            return indicators.movingAverage(np.array(array),duration,type)[(duration+1)-length/2:]                            
    
    def bollinger(self, type):
        duration=self.settings['avgDur']
        D=self.settings['bollingerD']
        if type=='upper':
            type=1
        elif type=='lower':
            type=2        
        else:
            return None
        length=len(self.close)
        if(length>=2*(duration+1)):
            array=self.getEarlierValues(length)                
            return indicators.bollingerBands(np.array(array),duration,type,D)
        else:
            array=self.getEarlierValues(2*(duration+1)+length%2)
            return indicators.bollingerBands(np.array(array),duration,type,D)[(duration+1)-length/2:]                                 
            
    def getSettings(self):
        """Zwraca głęboką kopię słownika settings"""
        return deepcopy(self.settings)
    
    def setSettings(self, settings):
        """Podstawia pod settings podaną wartość. Oczywiście settings musi być słownikiem
        o odpowiednich kluczach (patrz init)"""
        self.settings=settings
        
    """Jeśli chcemy np. zmienić długość dla RSI robimy:
    sett=chart.getData().getSettings()
    sett['RSIDur']=30
    chart.getData().setSettings(sett)
    chart.updatePlot()
    """
