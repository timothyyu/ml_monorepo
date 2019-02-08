 # coding: utf-8
__author__="Andrzej Smoliński"
__date__ ="$2012-02-23 19:00:48$"

from ChartData import ChartData
from matplotlib.collections import LineCollection
from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.finance import candlestick
from matplotlib.ticker import *
from matplotlib.textpath import TextPath
from matplotlib.text import Text
from numpy import *
from PyQt4 import QtGui
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from TechAnalysisModule.candles import *
import TechAnalysisModule.trendAnalysis as trend
import TechAnalysisModule.oscilators as osc
from TechAnalysisModule.strategy import Strategy

    
class Chart(FigureCanvas):
    """Klasa (widget Qt) odpowiedzialna za rysowanie wykresu. Zgodnie z tym, co zasugerował
    Paweł, na jednym wykresie wyświetlam jeden wskaźnik i jeden oscylator, a jak ktoś
    będzie chciał więcej, to kliknie sobie jakiś guzik, który mu pootwiera kilka wykresów
    w nowym oknie."""
    #margines (pionowy i poziomy oraz maksymalna wysokość/szerokość wykresu)
    margin, maxSize = 0.1, 0.8
    #wysokość wolumenu i wykresu oscylatora
    volHeight, oscHeight = 0.1, 0.15
    
    def __init__(self, parent, finObj=None, width=8, height=6, dpi=100):
        """Konstruktor. Tworzy domyślny wykres (liniowy z wolumenem, bez wskaźników)
dla podanych danych. Domyślny rozmiar to 800x600 pixli"""
        self.mainPlot=None
        self.volumeBars=None
        self.oscPlot=None
        self.additionalLines = [] #lista linii narysowanych na wykresie (przez usera, albo przez wykrycie trendu)
        self.rectangles = [] #lista prostokątów (do zaznaczania świec)
        self.mainType = None #typ głównego wykresu
        self.oscType = None #typ oscylatora (RSI, momentum, ...)
        self.mainIndicator = None #typ wskaźnika rysowany dodatkowo na głównym wykresie (średnia krocząca, ...)
        self.x0, self.y0 = None,None #współrzędne początku linii
        self.drawingMode = False #zakładam, że możliwość rysowania będzie można włączyć/wyłączyć
        self.scaleType = 'linear' #rodzaj skali na osi y ('linear' lub 'log')
        self.grid = True #czy rysujemy grida
        self.setData(finObj)
        self.mainType='line'
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.addMainPlot()
        self.addVolumeBars()
        self.mpl_connect('button_press_event', self.onClick)     
           
    def setData(self, finObj, start=None, end=None, step='daily'):
        """Ustawiamy model danych, który ma reprezentować wykres. Następnie
        konieczne jest jego ponowne odrysowanie"""
        if(finObj==None):
            return;
        self.data=ChartData(finObj, start, end, step)
        if(self.mainPlot!=None):
            self.updatePlot()
    
    def getData(self):
        return self.data
        
    def setGrid(self, grid):
        """Włącza (True) lub wyłącza (False) rysowanie grida"""
        self.grid=grid
        self.updateMainPlot()
            
    def setMainType(self, type):
        """Ustawiamy typ głównego wykresu ('point','line','candlestick','none')"""
        self.mainType=type
        self.updateMainPlot()        
        
    def updatePlot(self):
        """Odświeża wszystkie wykresy"""                
        self.updateMainPlot()
        self.updateVolumeBars()
        self.updateOscPlot()                                
        self.draw()        
        #self.drawGeometricFormation()
        #self.drawRateLines()
        #self.drawTrend()
        #self.drawCandleFormations()
        #self.drawGaps()
		
    
    def addMainPlot(self):
        """Rysowanie głównego wykresu (tzn. kurs w czasie)"""                                            
        bounds=[self.margin, self.margin, self.maxSize, self.maxSize]
        self.mainPlot=self.fig.add_axes(bounds)                        
        self.updateMainPlot()
    
    def updateMainPlot(self):        
        if(self.mainPlot==None or self.data==None or self.data.corrupted):
            return
        ax=self.mainPlot                
        ax.clear()  
        x=range(len(self.data.close))
        if self.mainType=='line' :
            ax.plot(x,self.data.close,'b-',label=self.data.name)
        elif self.mainType=='point':
            ax.plot(x,self.data.close,'b.',label=self.data.name)
        elif self.mainType=='candlestick':
            self.drawCandlePlot()
        elif self.mainType=='bar':
            self.drawBarPlot()
        else:            
            return
        if self.mainIndicator != None:
            self.updateMainIndicator()       
        ax.set_xlim(x[0],x[-1])
        ax.set_yscale(self.scaleType)
        ax.set_ylim(0.995*min(self.data.low),1.005*max(self.data.high))                 
        for line in self.additionalLines:
            ax.add_line(line)
            line.figure.draw_artist(line)         
        for rect in self.rectangles:
            ax.add_patch(rect)
            rect.figure.draw_artist(rect)        
        if(self.scaleType=='log'):            
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))            
            ax.yaxis.set_minor_formatter(FormatStrFormatter('%.2f'))            
        for tick in ax.yaxis.get_major_ticks():
            tick.label2On=True
            if(self.grid):
                tick.gridOn=True        
        for label in (ax.get_yticklabels() + ax.get_yminorticklabels()):
            label.set_size(8)
        #legenda
        leg = ax.legend(loc='best', fancybox=True)
        leg.get_frame().set_alpha(0.5)
        self.formatDateAxis(self.mainPlot)        
        self.fixTimeLabels()
        if(self.grid):
            for tick in ax.xaxis.get_major_ticks():
                # print tick.get_loc()
                tick.gridOn=True
    
    def addVolumeBars(self):
        """Dodaje do wykresu wyświetlanie wolumenu."""        
        #tworzymy nowy wykres tylko za pierwszym razem, potem tylko pokazujemy i odświeżamy                
        if(self.volumeBars==None):
            volBounds=[self.margin, self.margin, self.maxSize, self.volHeight]
            self.volumeBars=self.fig.add_axes(volBounds, sharex=self.mainPlot)                                                                               
        self.updateVolumeBars()
        self.volumeBars.set_visible(True)
        self.fixPositions()
        self.fixTimeLabels()
    
    def rmVolumeBars(self):
        """Ukrywa wykres wolumenu"""
        if self.volumeBars==None:
            return
        self.volumeBars.set_visible(False)        
        self.fixPositions()                            
        self.fixTimeLabels()
    
    def setScaleType(self,type):    
        """Ustawia skalę liniową lub logarytmiczną na głównym wykresie."""
        if(type) not in ['linear','log']:
            return        
        self.scaleType=type
        self.updateMainPlot()
        
    def updateVolumeBars(self):
        """Odświeża rysowanie wolumenu"""                
        if self.data==None or self.data.corrupted:
            return        
        ax=self.volumeBars
        ax.clear()
        x=range(len(self.data.close))
        ax.vlines(x,0,self.data.volume)        
        ax.set_xlim(x[0],x[-1])
        if(max(self.data.volume)>0):
            ax.set_ylim(0,1.2*max(self.data.volume))
        for label in self.volumeBars.get_yticklabels():
            label.set_visible(False)                                
        for o in ax.findobj(Text):
            o.set_visible(False)
        self.formatDateAxis(ax)
        self.fixTimeLabels()
        
    def drawCandlePlot(self):
        """Wyświetla główny wykres w postaci świecowej"""            
        if self.data==None or self.data.corrupted:
            return
        ax=self.mainPlot
        rectsList=[]
        open=self.data.open
        close=self.data.close
        xvals=range(len(close))
        lines=ax.vlines(xvals,self.data.low,self.data.high,label=self.data.name,linewidth=0.5)
        lines.set_zorder(lines.get_zorder()-1)
        for i in xvals:
            height=max(abs(close[i]-open[i]),0.001)
            width=0.7
            x=i-width/2
            y=min(open[i],close[i])
            print x,y,width,height
            if open[i]<=close[i]:
                rectsList.append(Rectangle((x,y),width,height,facecolor='w',edgecolor='k',linewidth=0.5))
            else:
                rectsList.append(Rectangle((x,y),width,height,facecolor='k',edgecolor='k',linewidth=0.5))
        ax.add_collection(PatchCollection(rectsList,match_original=True))     
    
    def drawBarPlot(self):
        """Rysuje główny wykres w postaci barowej."""
        if self.data==None or self.data.corrupted:
            return
        ax=self.mainPlot
        x=range(len(self.data.close))
        lines1=ax.vlines(x,self.data.low,self.data.high,label=self.data.name)
        lines2list=[]
        for i in x:
            lines2list.append(((i-0.3,self.data.open[i]),(i,self.data.open[i])))
            lines2list.append(((i,self.data.close[i]),(i+0.3,self.data.close[i])))   
        lines2=LineCollection(lines2list)
        lines2.color('k')
        ax.add_collection(lines2)
    
    def setMainIndicator(self, type):
        """Ustawiamy, jaki wskaźnik chcemy wyświetlać na głównym wykresie"""
        self.mainIndicator=type        
        self.updateMainPlot()
    
    def updateMainIndicator(self):
        """Odrysowuje wskaźnik na głównym wykresie"""
        if self.data==None or self.data.corrupted:
            return
        ax=self.mainPlot
        type=self.mainIndicator
        ax.hold(True) #hold on 
        x=range(len(self.data.close))
        if type=='SMA':
            indicValues=self.data.movingAverage('SMA')        
        elif type=='WMA':
            indicValues=self.data.movingAverage('WMA')
        elif type=='EMA':
            indicValues=self.data.movingAverage('EMA')
        elif type=='bollinger':            
            if self.data.bollinger('upper')!=None:
                ax.plot(x,self.data.bollinger('upper'),'r-',label=type)
            indicValues=self.data.bollinger('lower')
        else:
            ax.hold(False)
            return
        if indicValues!=None:
            ax.plot(x,indicValues,'r-',label=type)
        ax.hold(False) #hold off        
    
    def setOscPlot(self, type):
        """Dodaje pod głównym wykresem wykres oscylatora danego typu lub ukrywa"""
        if type not in ['momentum','CCI','RSI','ROC','williams']:
            """Ukrywa wykres oscylatora"""
            if self.oscPlot==None:
                return
            self.oscPlot.set_visible(False)        
            self.fixPositions()                            
            self.fixTimeLabels()
        else:
            self.oscType=type                
            if self.oscPlot==None:
                oscBounds=[self.margin, self.margin, self.maxSize, self.oscHeight]
                self.oscPlot=self.fig.add_axes(oscBounds, sharex=self.mainPlot)                                            
            self.updateOscPlot()
            self.oscPlot.set_visible(True)
            self.fixPositions()
            self.fixTimeLabels()                
                                    
    def updateOscPlot(self):
        """Odrysowuje wykres oscylatora"""
        if self.oscPlot==None or self.data.corrupted:
            return
        ax=self.oscPlot                
        type=self.oscType
        ax.clear()            
        if type == 'momentum':
            oscData=self.data.momentum()
        elif type == 'CCI':
            oscData=self.data.CCI()
        elif type == 'ROC':
            oscData=self.data.ROC()
        elif type == 'RSI':
            oscData=self.data.RSI()
        elif type == 'williams':
            oscData=self.data.williams()
        elif type == 'TRIN':
            oscData=self.data.TRIN()
        elif type == 'mcClellan':
            oscData=self.data.mcClellan()
        elif type == 'adLine':
            oscData=self.data.adLine()
        else:            
            return
        if oscData!=None:
            x=range(len(self.data.close))        
            ax.plot(x,oscData,'g-',label=type)
            ax.set_xlim(x[0],x[-1])
            #legenda
            leg = ax.legend(loc='best', fancybox=True)
            leg.get_frame().set_alpha(0.5)
            self.formatDateAxis(self.oscPlot)
            self.fixOscLabels()
            self.fixTimeLabels()
    
    def fixOscLabels(self):
        """Metoda ustawia zakres osi poprawny dla danego oscylatora. Ponadto przenosi
        etykiety na prawą stronę, żeby nie nachodziły na kurs akcji"""
        ax=self.oscPlot
        type=self.oscType                
        if type == 'ROC':
            ax.set_ylim(-100, 100)
        elif type == 'RSI':
            ax.set_ylim(0, 100)
            ax.set_yticks([30,70])
        elif type == 'williams':
            ax.set_ylim(-100,0)        
        for tick in ax.yaxis.get_major_ticks():
            tick.label1On = False
            tick.label2On = True
            tick.label2.set_size(7)

    def formatDateAxis(self,ax):
        """Formatuje etykiety osi czasu."""
        chartWidth=int(self.fig.get_figwidth()*self.fig.get_dpi()*self.maxSize)        
        t = TextPath((0,0), '9999-99-99', size=7)
        labelWidth = int(t.get_extents().width)    
        num_ticks=chartWidth/labelWidth/2          
        length=len(self.data.date)
        if(length>num_ticks):
            step=length/num_ticks        
        else:
            step=1
        x=range(0,length,step)
        ax.xaxis.set_major_locator(FixedLocator(x))
        ticks=ax.get_xticks()        
        labels=[]        
        for i, label in enumerate(ax.get_xticklabels()):
            label.set_size(7)                       
            index=int(ticks[i])            
            if(index>=len(self.data.date)):
                labels.append('')
            else:
                labels.append(self.data.date[index].strftime("%Y-%m-%d"))            
            label.set_horizontalalignment('center')                                    
        ax.xaxis.set_major_formatter(FixedFormatter(labels))        
    
    def fixTimeLabels(self):
        """Włącza wyświetlanie etykiet osi czasu pod odpowiednim (tzn. najniższym)
        wykresem, a usuwa w pozostałych"""
        #oscylator jest zawsze na samym dole
        if self.oscPlot!=None and self.oscPlot.get_visible():
            for label in self.mainPlot.get_xticklabels():
                label.set_visible(False)
            for label in self.volumeBars.get_xticklabels():
                label.set_visible(False)
            for label in self.oscPlot.get_xticklabels():
                label.set_visible(True)
        #jeśli nie ma oscylatora to pod wolumenem
        elif self.volumeBars!=None and self.volumeBars.get_visible():
            for label in self.mainPlot.get_xticklabels():
                label.set_visible(False)
            for label in self.volumeBars.get_xticklabels():
                label.set_visible(True)         
        #a jak jest tylko duży wykres to pod nim
        else:
            for label in self.mainPlot.get_xticklabels():
                label.set_visible(True)                        
    
    def fixPositions(self):
        """Dopasowuje wymiary i pozycje wykresów tak żeby zawsze wypełniały całą
        przestrzeń. Główny wykres puchnie albo się kurczy, a wolumen i oscylator 
        przesuwają się w górę lub dół."""
        #na początek wszystko spychamy na sam dół
        mainBounds=[self.margin, self.margin, self.maxSize, self.maxSize]
        volBounds=[self.margin, self.margin, self.maxSize, self.volHeight]
        oscBounds=[self.margin, self.margin, self.maxSize, self.oscHeight]
        #oscylator wypycha wolumen w górę i kurczy maina
        if self.oscPlot!=None and self.oscPlot.get_visible():
            mainBounds[1]+=self.oscHeight
            mainBounds[3]-=self.oscHeight
            volBounds[1]+=self.oscHeight
            self.oscPlot.set_position(oscBounds)
        #wolumen kolejny raz kurczy maina
        if self.volumeBars.get_visible():                    
            mainBounds[1]+=self.volHeight
            mainBounds[3]-=self.volHeight
            self.volumeBars.set_position(volBounds)
        self.mainPlot.set_position(mainBounds)     
    
    def setDrawingMode(self, mode):
        """Włączamy (True) lub wyłączamy (False) tryb rysowania po wykresie"""
        self.drawingMode=mode            
        self.x0, self.y0 = None,None
    
    def drawLine(self, x0, y0, x1, y1, color='black', lwidth = 1.0, lstyle = '-'):
          """Rysuje linie (trend) na wykresie """
          newLine=Line2D([x0,x1],[y0,y1], linewidth = lwidth, linestyle=lstyle, color=color)                
          self.mainPlot.add_line(newLine)
          self.additionalLines.append(newLine)
          newLine.figure.draw_artist(newLine)                                        
          self.blit(self.mainPlot.bbox)    #blit to taki redraw  
    
    def clearLines(self):
        """Usuwa wszystkie linie narysowane dodatkowo na wykresie (tzn. nie kurs i nie wskaźniki)"""
        for line in self.additionalLines:            
            line.remove()
        self.additionalLines = []
        self.draw()
        self.blit(self.mainPlot.bbox)
    
    def clearLastLine(self):
        """Usuwa ostatnią linię narysowaną na wykresie."""
        if self.additionalLines==[]:
            return
        self.additionalLines[-1].remove()
        self.additionalLines.remove(self.additionalLines[-1])
        self.draw()
        self.blit(self.mainPlot.bbox)
    
    def drawRectangle(self, x, y, width, height, colour='blue', lwidth = 2.0, lstyle = 'dashed'):
        """Zaznacza prostokątem lukę/formację świecową czy coś tam jeszcze"""
        newRect=Rectangle((x,y),width,height,facecolor='none',edgecolor=colour,linewidth=lwidth,linestyle=lstyle)                
        self.mainPlot.add_patch(newRect)
        self.rectangles.append(newRect)
        newRect.figure.draw_artist(newRect)                                        
        self.blit(self.mainPlot.bbox)    #blit to taki redraw        
    
    def clearRectangles(self):
        """Usuwa prostokąty"""
        for rect in self.rectangles:            
            rect.remove()
        self.rectangles = []
        self.draw()
        self.blit(self.mainPlot.bbox)

    def onClick(self, event):
        """Rysujemy linię pomiędzy dwoma kolejnymi kliknięciami."""        
        if self.drawingMode==False:
            return
        if event.button==3: 
            self.clearLastLine()            
        if event.button==2: 
            self.clearLines()
        elif event.button==1:
            if self.x0==None or self.y0==None :
                self.x0, self.y0 = event.xdata, event.ydata
                self.firstPoint=True
            else:
                x1, y1 = event.xdata, event.ydata        
                self.drawLine(self.x0,self.y0,x1,y1)                
                self.x0, self.y0 = None,None                                          
        
    def drawTrend(self):
        self.clearLines()
        a, b = trend.regression(self.data.close)
        trend.optimizedTrend(self.data.close)
        #self.drawTrendLine(0, b, len(self.data.close)-1, a*(len(self.data.close)-1) + b, 'y', 2.0)
        sup, res = trend.getChannelLines(self.data.close)
        self.drawLine(sup[0][1], sup[0][0], sup[len(sup)-1][1], sup[len(sup)-1][0], 'g')
        self.drawLine(res[0][1], res[0][0], res[len(res)-1][1], res[len(res)-1][0], 'r')
        if len(self.data.close) > 30:
            sup, res = trend.getChannelLines(self.data.close, 1, 2)
            self.drawLine(sup[0][1], sup[0][0], sup[len(sup)-1][1], sup[len(sup)-1][0], 'g', 2.0)
            self.drawLine(res[0][1], res[0][0], res[len(res)-1][1], res[len(res)-1][0], 'r', 2.0)
