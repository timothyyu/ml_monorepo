# coding: utf-8
__author__="Andrzej Smoliński"
__date__ ="$2012-03-31 18:57:55$"

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import *
from PyQt4 import QtGui

class LightweightChart(FigureCanvas):
    """Jest to klasa do wyświetlania "lekkich" wykresów, tzn. takich które będą na
    głównej stronie i odnoszą się do rynku jako całości (indeksy, A/D line itd.)
    Nie można po nich rysować, wyświetlać wolumenu, zmieniać skali etc. Ponadto 
    klasa ta nie korzysta z ChartData tylko rysuje na pałę zwykłą tablicę."""    
    
    fig = None #rysowany wykres (tzn. obiekt klasy Figure)
    plot = None #rysowany wykres (tzn. obiekt klasy Axes)
    
    num_ticks = 4 #tyle jest etykiet pod wykresem
    
    #margines (pionowy i poziomy oraz maksymalna wysokość/szerokość wykresu)
    margin, maxSize = 0.0, 1.0         
    
    def __init__(self, parent, dates=None, values=None, name=None, width=3.2, height=2.4, dpi=100):
        """Konstruktor. Tworzy wykres dla podanych danych. Domyślny rozmiar to 320x240 pixli."""                                
        self.fig = Figure(figsize=(width, height), dpi=dpi)        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)                 
        bounds=[self.margin, self.margin, self.maxSize, self.maxSize]
        self.plot=self.fig.add_axes(bounds)     
        self.setData(dates,values,name)                                           
    
    def setData(self, dates, values,name=None):
        """Ustawiamy model danych, który ma reprezentować wykres. Przekazujemy tablicę
        z datami oraz wartości y. Następnie następuje ponowne odrysowanie wykresu."""        
        if(dates==None or values==None or len(dates)!=len(values)):
            return        
        self.dates=dates        
        self.values=values        
        if(name!=None):
            self.name=name
        if(self.plot!=None):
            self.updatePlot()
    
    def updatePlot(self):
        """Odrysowuje wykres"""
        if(self.plot==None or self.dates==None or self.values==None):            
            return
        ax=self.plot                
        ax.clear()  
        x=range(len(self.dates))        
        #rysujemy wykres          
        ax.plot(x,self.values,'b-',label=self.name)
        ax.set_xlim(x[0],x[-1])        
        minVal=min(self.values)
        maxVal=max(self.values)
        ax.set_ylim(minVal-0.01*abs(minVal),maxVal+0.01*abs(maxVal))      
        self.formatDateAxis(ax)
        self.draw()
    
    def formatDateAxis(self,ax):
        """Formatuje etykiety osi czasu. Ponieważ nie chcemy mieć dni, w których nie było notowań,
        a jednocześnie nie chcemy mieć "dziur" na osi x musiałem zrezygnować z traktowania
        wartości x jak dat. Zamiast tego indeksuje je kolejnymi liczbami naturalnymi, dopiero
        w momencie etykietowania osi sprawdzam jaka data odpowiada danej liczbie. Oprócz tego funkcja
        odpowiada za ilość etykiet rozmiar ich fonta, i wyrównanie (do środka)"""
        length=len(self.dates)
        if(length>self.num_ticks):
            step=length/self.num_ticks        
        else:
            step=1
        x=range(0,length,step)
        ax.xaxis.set_major_locator(FixedLocator(x))
        ticks=ax.get_xticks()        
        labels=[]        
        for i, label in enumerate(ax.get_xticklabels()):
            label.set_size(5)                       
            index=int(ticks[i])            
            if(index>=len(self.dates)):
                labels.append('')
            else:
                labels.append(self.dates[index])            
            label.set_horizontalalignment('center')                                            
        ax.xaxis.set_major_formatter(FixedFormatter(labels))    
        for label in ax.get_yticklabels():
            label.set_size(5)                       




