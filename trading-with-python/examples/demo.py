''' simulate a buy/sale strategy on a stock & evaluate its PnL (profit and Lost) '''
#!pip install mlboost
from util import strategy 
reload(strategy)

charts = True
verbose = True
debug=True
signalType='shares'

months=12

#stock ="AAPL"
#stock='TA' #oil
#stock='BP' # oil

stock = 'NYMX'

summary = strategy.eval(stock, field='open', months=months, 
                  initialCash=20000, min_stocks=40, 
                  charts=charts, verbose=verbose, debug=True,
                  signalType='orders');

print stock, summary.ix[-1:,'cash':]