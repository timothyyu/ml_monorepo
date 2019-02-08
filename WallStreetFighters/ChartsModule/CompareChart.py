# coding: utf-8
__author__="Andrzej Smoliński"
__date__ ="$2012-03-24 12:05:55$"

from ChartData import ChartData
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import *
from PyQt4 import QtGui
from matplotlib.lines import Line2D

class CompareChart(FigureCanvas):
    """To będzie klasa reprezentująca wykres porównujący kilka instrumentów na jednym
    wykresie. Jest to dość okrojona wersja zwykłego Chart-a (nie mamy wolumenu, wskaźników, oscylatorów,
    jedyny typ do wyboru to liniowy)."""
    data = [] #lista obiektów klasy ChartData
    
    fig = None #rysowany wykres (tzn. obiekt klasy Figure)
    mainPlot = None #główny wykres (punktowy, liniowy, świecowy)
    additionalLines = [] #lista linii narysowanych na wykresie (przez usera, albo przez wykrycie trendu)
    
    x0, y0 = None,None #współrzędne początku linii
    drawingMode = False #zakładam, że możliwość rysowania będzie można włączyć/wyłączyć
    
    scaleType = 'linear' #rodzaj skali na osi y ('linear' lub 'log')
    
    num_ticks = 8 #tyle jest etykiet pod wykresem
    
    #margines (pionowy i poziomy oraz maksymalna wysokość/szerokość wykresu)
    margin, maxSize = 0.1, 0.8
    #kolorki!
    lineColors=['b-','k-','r-','g-','m-']
    
    def __init__(self, parent, width=8, height=6, dpi=100):
        """Konstruktor. Tworzy domyślny wykres (liniowy z wolumenem, bez wskaźników)
        dla podanych danych. Domyślny rozmiar to 800x600 pixli. W przeciwieństwie do zwykłego
        Charta tutej nie podajemy w konstruktorze danych (trzeba wywołać setData żeby cokolwiek
        się narysowało). Wynika to z tego że dane muszą mieć dokładnie tę samą długość, a domyślnie
        pobieram je od początku do końca."""
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        bounds=[self.margin, self.margin, self.maxSize, self.maxSize]
        self.mainPlot=self.fig.add_axes(bounds)
        self.mpl_connect('button_press_event', self.onClick)
    
    def setData(self, data, start=None, end=None, step='monthly'):
        """Ustawiamy model danych, który ma reprezentować wykres. (przekazujemy
            tablicę FinancialObjectów). Następnie konieczne jest jego ponowne odrysowanie."""
        self.data=[]
        for finObj in data:
            #sprawdzmy czy wszystkie dane są poprawne i tej samej długości
            newData=ChartData(finObj, start, end, step,compare = True)
            if(self.data==[]):
                length=len(newData.date)
            newlength=len(newData.date)
            if newData.corrupted or length!=newlength:
                self.data=[]
                break;
            else:
                self.data.append(newData)
            
        if(self.mainPlot!=None):
            self.updatePlot()
    
    def updatePlot(self):
        """Odrysowuje główny wykres (czyli w zasadzie wszystko)"""
        if(self.mainPlot==None or self.data==[]):
            return
        ax=self.mainPlot
        ax.clear()
        x=range(len(self.data[0].percentChng))
        minVal=maxVal=None
        #rysujemy wykresy
        for i, data in enumerate(self.data):
            ax.plot(x,data.percentChng,self.lineColors[i%len(self.lineColors)],label=data.name)
            if(minVal==None or min(data.percentChng)<minVal):
                minVal=min(data.percentChng)
            if(maxVal==None or max(data.percentChng)>maxVal):
                maxVal=max(data.percentChng)
        #skalujemy osie
        ax.set_xlim(x[0],x[-1])
        ax.set_yscale(self.scaleType)
        #przy skali logarytmicznej ustawiamy etykietki żeby były gęściej niż przy 10^k
        if(self.scaleType=='log'):
            ax.set_ylim(minVal-0.1*abs(minVal),max(210,maxVal+0.1*abs(maxVal)))
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f%%'))
            ax.yaxis.set_minor_formatter(FormatStrFormatter('%.2f%%'))
        else:
            ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f%%'))
            ax.set_ylim(minVal-0.01*abs(minVal),maxVal+0.01*abs(maxVal))
        for label in (ax.get_yticklabels() + ax.get_yminorticklabels()):
            label.set_size(8)
        #legenda
        leg = ax.legend(loc='best', fancybox=True)
        leg.get_frame().set_alpha(0.5)
        self.formatDateAxis(self.mainPlot)
    
    def setScaleType(self,type):
        """Ustawia skalę liniową lub logarytmiczną na głównym wykresie."""
        if(type) not in ['linear','log']:
            return
        self.scaleType=type
        self.updatePlot()
    
    def formatDateAxis(self,ax):
        """Formatuje etykiety osi czasu. Ponieważ nie chcemy mieć dni, w których nie było notowań,
        a jednocześnie nie chcemy mieć "dziur" na osi x musiałem zrezygnować z traktowania
        wartości x jak dat. Zamiast tego indeksuje je kolejnymi liczbami naturalnymi, dopiero
        w momencie etykietowania osi sprawdzam jaka data odpowiada danej liczbie. Oprócz tego funkcja
        odpowiada za ilość etykiet rozmiar ich fonta, i wyrównanie (do środka)"""
        length=len(self.data[0].date)
        if(length>self.num_ticks):
            step=length/self.num_ticks
        else:
            step=1
        x=range(0,length,step)
        ax.xaxis.set_major_locator(FixedLocator(x))
        ticks=ax.get_xticks()
        labels=[]
        for i, label in enumerate(ax.get_xticklabels()):
            label.set_size(7)
            index=int(ticks[i])
            if(index>=len(self.data[0].date)):
                labels.append('')
            else:
                labels.append(self.data[0].date[index].strftime("%Y-%m-%d"))
            label.set_horizontalalignment('center')
        ax.xaxis.set_major_formatter(FixedFormatter(labels))        
    
    def setDrawingMode(self, mode):
        """Włączamy (True) lub wyłączamy (False) tryb rysowania po wykresie"""
        self.drawingMode=mode
        x0, y0 = None,None
    
    def drawLine(self, x0,y0,x1,y1):
        """Dodaje linię (trend) do wykresu."""
        newLine=Line2D([x0,x1],[y0,y1],color='k')
        self.mainPlot.add_line(newLine)
        self.additionalLines.append(newLine)
        newLine.figure.draw_artist(newLine)
        self.blit(self.mainPlot.bbox) #blit to taki redraw
    
    def clearLines(self):
        """Usuwa wszystkie linie narysowane dodatkowo na wykresie (tzn. nie kurs i nie wskaźniki)"""
        for line in self.additionalLines:
            line.remove()
        self.additionalLines = []
        self.draw()
        self.blit(self.mainPlot.bbox)
    
    def onClick(self, event):
        """Rysujemy linię pomiędzy dwoma kolejnymi kliknięciami."""
        if self.drawingMode==False:
            return
        if event.button==3: 
            self.clearLines()
        elif event.button==1:
            if self.x0==None or self.y0==None :
                self.x0, self.y0 = event.xdata, event.ydata
                self.firstPoint=True
            else:
                x1, y1 = event.xdata, event.ydata
                self.drawLine(self.x0,self.y0,x1,y1)
                self.x0, self.y0 = None,None
