
from Data.TimeSeries import *

from Data.TimeSeries import *
import pandas as pd
import matplotlib

import cvxopt as opt
from cvxopt import blas, solvers

import numpy as np
import zipline
from zipline.api import (add_history, history, set_slippage,
                         slippage, set_commission, commission,
                         order_target_percent, symbol,symbols)


from zipline import TradingAlgorithm

class AAA:
    def __init__(self, data) :
        self.data = data

    def initialize(self, context) :
        pass

    def handle_data(self, context, data) :
        pass

    def run_trading(self) :
        algo = TradingAlgorithm(initialize=self.initialize, handle_data=self.handle_data)
        results = algo.run(self.data)
        return results


class Portfolio1(AAA):

    def average_weights(self, returns):
        n = len(returns)
        wt = opt.matrix(1.0/n, (n, 1))
        return np.asarray(wt)

    def initialize(self, context):
        add_history(30, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.005))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick % rebalance_period != 0:
            return


        # Get rolling window of past prices and compute returns
        prices = history(30, '1d', 'price').dropna()
        returns = prices.pct_change().dropna()
        try:
            # Perform Markowitz-style portfolio optimization
            weights = self.average_weights(returns.T)
            # Rebalance portfolio accordingly
            for stock, weight in zip(prices.columns, weights):
                order_target_percent(stock, weight)
        except ValueError as e:
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass


class Portfolio2(AAA):

    def vol_weighting(self, returns):
        n = len(returns)
        weight_target = 1.0 / n

        vol = np.std(returns, axis=1)
        vol_target = 0.01 # daily vol 1% target

        wt = vol_target / vol * weight_target
        wt[wt > weight_target] = weight_target
        return np.asarray(wt)

    def initialize(self, context):
        add_history(60, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick % rebalance_period != 0:
            return


        # Get rolling window of past prices and compute returns
        prices = history(60, '1d', 'price').dropna()
        returns = prices.pct_change().dropna()
        try:
            # Perform Markowitz-style portfolio optimization
            weights = self.vol_weighting(returns.T)
            # Rebalance portfolio accordingly
            for stock, weight in zip(prices.columns, weights):
                order_target_percent(stock, weight)
        except ValueError as e:
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass


class Portfolio3(AAA) :
    def MOM(self, returns):
        mom = returns.sum(axis=1)
        wt = (mom > np.median(mom)) * 0.2
        return np.asarray(wt)

    def initialize(self, context):
        add_history(120, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick % rebalance_period != 0:
            return

        # Get rolling window of past prices and compute returns
        prices = history(120, '1d', 'price').dropna()
        returns = prices.pct_change().dropna()
        try:
            weights = self.MOM(returns.T)
            for stock, weight in zip(prices.columns, weights):
                order_target_percent(stock, weight)
        except ValueError as e:
            pass


class Portfolio4(AAA) :
    def initialize(self, context):
        add_history(120, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick % rebalance_period != 0:
            return


        # Get rolling window of past prices and compute returns
        prices_6m = history(120, '1d', 'price').dropna()
        returns_6m = prices_6m.pct_change().dropna()
        prices_60d = history(60, '1d', 'price').dropna()
        returns_60d = prices_60d.pct_change().dropna()

        try:
            # Get the strongest 5 in momentum
            mom = returns_6m.T.sum(axis=1)
            selected = (mom > np.median(mom)) * 1

            # 60 days volatility
            vol = np.std(returns_60d.T, axis=1)
            vol_target = 0.01
            wt = vol_target / vol * 0.2
            wt[wt > 0.2] = 0.2
            #
            weights = wt * selected
            # Rebalance portfolio accordingly
            for stock, weight in zip(prices_60d.columns, weights):
                order_target_percent(stock, weight)
        except ValueError as e:
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass




from cvxpy import *

class Portfolio5(AAA) :
    def minimize_vol(self,returns):
        n = len(returns)
        w  = Variable(n)

        gamma = Parameter(sign='positive')
        mu = returns.mean(axis=1)
        ret = np.array(mu)[np.newaxis] * w

        Sigma = np.cov(returns)
        risk = quad_form(w, Sigma)
        prob = Problem(Maximize(ret - 200*risk), [sum_entries(w)==1, w >=0])
        prob.solve()
        #print w.value.T * Sigma * w.value
        return np.asarray(w.value)

    def initialize(self, context):
        add_history(120, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick < 120 :
            return
        if context.tick % rebalance_period != 0:
            return


        # Get rolling window of past prices and compute returns
        prices_6m = history(120, '1d', 'price').dropna()
        returns_6m = prices_6m.pct_change().dropna()
        prices_60d = history(60, '1d', 'price').dropna()
        returns_60d = prices_60d.pct_change().dropna()

        try:
            # Get the strongest 5 in momentum
            mom = returns_6m.T.sum(axis=1)
            #selected_indices = mom[mom>0].order().tail(len(mom) /2).index
            selected_indices = mom.index
            #selected_indices = mom[mom > 0 ].index
            selected_returns = returns_60d[selected_indices]

            weights = self.minimize_vol(selected_returns.T)
    #         weights = minimize_vol(returns_60d.T)
            # Rebalance portfolio accordingly
            for stock, weight in zip(selected_returns.columns, weights):
                order_target_percent(stock, weight)
        except :
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass

class Portfolio6(AAA) :
    def initialize(self, context):
        add_history(200, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20

        context.tick += 1
        if context.tick < 120 :
            return
        if context.tick % rebalance_period != 0:
            return


        # Get rolling window of past prices and compute returns
        prices_1d = history(1, '1d', 'price').dropna()
        prices_6m = history(120, '1d', 'price').dropna()
        returns_6m = prices_6m.pct_change().dropna()

        prices_200d = history(200, '1d', 'price').dropna()
        ma200 = np.mean(prices_200d)
        prices_60d = history(60, '1d', 'price').dropna()
        returns_60d = prices_60d.pct_change().dropna()

        try:
            # Get the strongest 5 in momentum

            mom = returns_6m.T.sum(axis=1)
            #selected_indices = mom[mom>0].order().tail(len(mom) /2).index
            selected_indices = prices_1d[prices_1d > ma200].value
            #selected_indices = mom[mom > 0 ].index
            selected_returns = returns_60d[selected_indices]

            weights = self.minimize_vol(selected_returns.T)
    #         weights = minimize_vol(returns_60d.T)
            # Rebalance portfolio accordingly
            for stock, weight in zip(selected_returns.columns, weights):
                order_target_percent(stock, weight)
        except :
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass


class Momentum(AAA) :
    ticker_spy = 'GOOG/NYSE_SPY'

    def filtering(self, data, f) :
        for i in range(len(data)) :
            if i%f == 0:
                #print i
                continue
            data.iloc[i, :] = np.NAN
        return data.dropna()

    def initialize(self, context):
        add_history(200, '1d', 'price')

        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

    def handle_data(self, context, data):
        rebalance_period = 20
        context.tick += 1

        if context.tick < 200 :
            return
        if context.tick % rebalance_period != 0:
            return

        # condition 1: momentum conditons, current monthly prices > 10 months MA
        prices_200d = history(200, '1d', 'price').dropna()
        prices_m = self.filtering(prices_200d, rebalance_period)
        prices_ma_10m = pd.rolling_mean(prices_m, 10)
        con1 = prices_m.tail(1) > prices_ma_10m.tail(1)


        # condition 2: picking up the ETF, which outperforms the SPY
        moving_win = 3
        symbol_spy = symbol(self.ticker_spy)
        rets_3m = (prices_m / prices_m.shift(moving_win) - 1)
        rets_spy_3m = (prices_m[symbol_spy] / prices_m[symbol_spy].shift(moving_win) - 1)
        con2 = rets_3m.tail(1) > np.asarray(rets_spy_3m.tail(1))

        # condition 3: picking up the ETF, which have positive returns
        rets = prices_m.pct_change()
        con3 = rets.tail(1) >  0

        # signals
        sig1 = con1
        sig2 = con1 & con2
        sig3 = con2 & con3
        sig4 = con1 & con3
        sig5 = con1 & con2 & con3

        sig = sig1

        # Trading
        count = np.asarray(sig.sum(axis=1))
        if count == 0:
            weights = sig * 0.0
        else :
            weights = sig * 1.0 / count
        weights = np.asarray(weights.fillna(0))
        stocks = np.asarray(sig.columns)

        try:
            # Rebalance portfolio accordingly
            for stock, weight in zip(stocks, weights.T):
               #print 'stock={stock}:weight={weight}'.format(stock=stock, weight=weight)

                order_target_percent(stock, weight)
        except :
            # Sometimes this error is thrown
            # ValueError: Rank(A) < p or Rank([P; A; G]) < n
            pass


class Momentum_Sector_Rotation(AAA) :
    ticker_spy = 'GOOG/NYSE_SPY'
    ticker_gld = 'GOOG/NYSEARCA_GLD'
    ticker_tlt = 'GOOG/NYSE_TLT'

    sector_tickers = [
            'GOOG/NYSEARCA_XLB',
            'GOOG/NYSEARCA_XLE',
            'GOOG/NYSEARCA_XLF',
            'GOOG/NYSEARCA_XLI',
            'GOOG/NYSEARCA_XLK',
            'GOOG/NYSEARCA_XLP',
            'GOOG/NYSEARCA_XLU',
            'GOOG/NYSEARCA_XLV',
            'GOOG/NYSEARCA_XLY',
            'GOOG/NYSEARCA_GLD'
            ]


    def initialize(self, context):



        #context.equities = symbols(sector_tickers)
        context.trade_days = 0
        #context.gold = symbol('GLD')

    def top_rets(self, tickers, win) :
        hist = history(bar_count = 241, frequency='1d', field='price')

        ret = ((hist/hist.shift(win)) - 1).tail(1)
        mean_ret = float(np.median(ret))
        max_ret = float(ret.max(axis=1))
        spy_ret = float(ret[symbol(self.ticker_spy)])

        lst = {}
        lst['mean'] = []
        lst['spy'] = []
        lst['zero'] = []
        lst['max'] = []

        for ticker in tickers :
            ticker_ret = float(ret[ticker])
            if ticker_ret > mean_ret :
                lst['mean'].append(ticker)
            if ticker_ret > spy_ret:
                lst['spy'].append(ticker)
            if ticker_ret > 0:
                lst['zero'].append(ticker)
            if ticker_ret >= max_ret:
                lst['max'].append(ticker)
        return lst

    # Will be called on every trade event for the securities you specify.
    def handle_data(self, context, data):
        # Implement your algorithm logic here.

        # data[sid(X)] holds the trade event data for that security.
        # context.portfolio holds the current portfolio state.

        # Place orders with the order(SID, amount) method.

        # TODO: implement your own logic here.
        context.trade_days += 1
        if context.trade_days <> 5 :
           return
        context.trade_days = 0


        ## checking the market status:
        ## if SPY > price one year ago, Market is in uptrend
        ## otherwise, market is in downtrend
        hist = history(bar_count = 241, frequency='1d', field='price')
        cash = context.portfolio.cash
        current_price_spy = data[symbol(self.ticker_spy)].price


        try:
            if current_price_spy > hist[symbol(self.ticker_spy)][200] :

                lst = self.top_rets(context.equities, 240)
                lst_mean = lst['zero']
                count = len(lst_mean)



                for ticker in sector_tickers:
                    if ticker in lst_mean:
                        order_target_percent(symbol(ticker), 1.0/count)
                    else :
                        order_target_percent(symbol(ticker), 0)

                order_target_percent(symbol(self.ticker_gld),  0)
                order_target_percent(symbol(self.ticker_tlt), 0)
            else :
                for ticker in sector_tickers:
                    order_target_percent(symbol(ticker), 0)

                order_target_percent(symbol(self.ticker_spy),  0)
                order_target_percent(symbol(self.ticker_gld),  0.5)
                order_target_percent(symbol(self.ticker_tlt),  0.5)
        except:
            pass




if __name__  == "__main__" :
    tickers = ['GOOG/NYSE_SPY', #S&P 500 ETF
           'GOOG/AMEX_EWJ', # iShares MSCI Japan ETF
           'GOOG/NYSE_IEV', # iShares Europe ETF
           #'GOOG/NYSE_VWO', # Vanguard Emerging Market Stock ETF

           #'GOOG/NYSE_VNQ', # Vanguard MSCI US Reits
           'GOOG/NYSE_IYR', # iShares U.S. Real Estate ETF
           'GOOG/NYSE_RWX', # SPDR DJ Wilshire Intl Real Estate ETF

           'GOOG/NYSEARCA_TLT',  # 20 Years Treasury ETF
           'GOOG/NYSEARCA_TLH',  # 15-20 Years Treasury

           'GOOG/AMEX_GSG', # GSCI Commodity-Indexed Trust Fund
           'GOOG/NYSEARCA_GLD',  # SPDR Gold ETF

          ]

    sector_tickers = [
            'GOOG/NYSEARCA_XLB',
            'GOOG/NYSEARCA_XLE',
            'GOOG/NYSEARCA_XLF',
            'GOOG/NYSEARCA_XLI',
            'GOOG/NYSEARCA_XLK',
            'GOOG/NYSEARCA_XLP',
            'GOOG/NYSEARCA_XLU',
            'GOOG/NYSEARCA_XLV',
            'GOOG/NYSEARCA_XLY'
            ]

    bm_tickers = [
            'GOOG/NYSE_SPY',
            'GOOG/NYSEARCA_TLT',
            'GOOG/NYSEARCA_GLD' #gold
            ]

    settings = Settings()
    dp = TimeSeries(settings).get_agg_data(sector_tickers+bm_tickers)
    dp = dp.fillna(method='pad', axis=0)
    dp = dp.fillna(method='bfill', axis=0)
    dp = dp[:,'2000-01-01'::,:]
    dp = dp.dropna()



    rets = pd.DataFrame()
    rets[1] = Momentum_Sector_Rotation(dp).run_trading().portfolio_value
    #rets[1] = Portfolio1(dp).run_trading().portfolio_value
    #rets[2] = Portfolio2(dp).run_trading().portfolio_value
    # rets[3] = Portfolio3(dp).run_trading().portfolio_value
    # rets[4] = Portfolio4(dp).run_trading().portfolio_value
    # rets[5] = Portfolio5(dp).run_trading().portfolio_value
    #
    # rets[6] = Portfolio6(dp).run_trading().portfolio_value
    # rets[7] = Momentum(dp).run_trading().portfolio_vlaue
    rets.plot(figsize=[20,12])

    print 'done!'

