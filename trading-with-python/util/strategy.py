import numpy as np
import pandas as pd
from filter import movingaverage
import math
from trendy import segtrends

#!pip install mlboost
from mlboost.core.pphisto import SortHistogram

# little hack to make in working inside heroku twp submodule
import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
      
def orders_from_trends(x, segments=2, charts=True, window=7, momentum=False):
    ''' generate orders from segtrends '''
    x_maxima, maxima, x_minima, minima = segtrends(x, segments, charts, window)
    n = len(x)
    y = np.array(x)
    movy = movingaverage(y, window)

    # generate order strategy
    orders = np.zeros(n)
    last_buy = y[0]
    last_sale = y[0]

    for i in range(1,n):
        # get 2 latest support point y values prior to x
        pmin = list(minima[np.where(x_minima<=i)][-2:])
        pmax = list(maxima[np.where(x_maxima<=i)][-2:])
        # sell if support slop is negative
        min_sell = True if ((len(pmin)==2) and (pmin[1]-pmin[0])<0) else False 
        max_sell = True if ((len(pmax)==2) and (pmax[1]-pmax[0])<0) else False 

        # if support down, sell
        buy = -1 if (min_sell and max_sell) else 0
        # buy only if lower the moving average else sale
        buy = 1 if ((buy == 0) and (y[i]<movy[i])) else -1
        # sell only if ...
        buy= -1 if ((buy == -1) and y[i]>last_buy) else 1
      
        buy_price_dec = y[i]<last_buy
        sale_price_dec = y[i]<last_sale
        orders[i] = buy
        last_buy = y[i] if (buy==1) else last_buy
        last_sale = y[i] if (buy==-1) else last_sale
        
        if momentum:
            # add momentum for buy 
            if (buy==1) and (orders[i-1]>=1):
                #if buy_price_dec:
                orders[i]=orders[i-1]*2#round(math.log(2*orders[i-1])+1)
                #else:
                 #   orders[i]=max(1, round(orders[i-1]/2))
            # add momentum for sale
            elif (buy==-1) and (orders[i-1]<=-1):
                #if sale_price_dec:
                orders[i]*=round(math.log(abs(orders[i-1]*2))+1)
                #else:
                #    orders[i]=max(1, round(orders[i-1]/2))

    # OUTPUT
    return orders

def orders2strategy(orders, price, min_stocks=1):
    strategy = pd.Series(index=price.index) 
    orders=[el*min_stocks for el in orders]
    # create a stratgy from order
    for i, idx in enumerate(price.index):
        if orders[i]!=0:
            strategy[idx] = orders[i]
    return strategy

def eval(stockname='TSLA', field='open', months=12, initialCash=20000, 
        min_stocks=30, charts=True, verbose=False, debug=False,
        signalType='shares'):

    if verbose:
      print "Evaluation ", stockname
    
    import lib.yahooFinance as yahoo 
    import lib.backtest as bt
    
    from pylab import title, figure, savefig, subplot
    n = (5*4)*months
    price = yahoo.getHistoricData(stockname)[field][-n:] 
    if (charts and debug):
        figure()
        title('automatic strategy base %s' %stockname)

    orders = orders_from_trends(price, segments=n/5, charts=(charts and debug), 
                                momentum=True); 
    strategy = orders2strategy(orders, price, min_stocks)
        
    # do the backtest
    btr = bt.Backtest(price, strategy, initialCash=initialCash, signalType=signalType)
    if charts:
        print "#1) Automatic buy/sales visualisation of the current strategy (buy=long, short=sale)"
	subplot(211)        
	#figure()
        btr.plotTrades(stockname)
	subplot(212)
        print "#2) Evaluation of the strategy (PnL (Profit & Log) = Value today - Value yesterday)"
        #figure()
        btr.pnl.plot()
        title('pnl '+stockname)
	savefig('eval.png')
        print "#3) big picture: Price, shares, value, cash & PnL"
        btr.data.plot()
        title('all strategy data %s' %stockname)
        
    return btr.data

def eval_best(stocks=["TSLA", "GS", "SCTY", "AMZN", "CSCO", 'UTX','JCI',"GOOGL",'AAPL','BP','MSFT'],
              field='open', months=12, 
              initialCash=20000, min_stocks=30, 
              charts=True, verbose=False, debug=False):
  # try current strategy on different stock
  trademap = {}
  tradedetails = {}

  for i, stock in enumerate(stocks):
    trade = eval(stock, field=field, months=months, initialCash=initialCash, 
                 min_stocks=min_stocks, charts=charts, verbose=False, debug=debug)
    if False:
      print i, stock, trade.ix[-1:,'cash':]
    trademap[stock] = trade[-1:]['pnl'][-1]
    tradedetails[stock] = trade[-1:]
  st = SortHistogram(trademap, False, True)
  if verbose:
    print "Here are the Stocks sorted by PnL"
    for i,el in enumerate(st):
      stock, value = el
      print "#", i+1, stock, tradedetails[stock]
  return st

if __name__ == "__main__":
    #eval(charts=True)
    pass
