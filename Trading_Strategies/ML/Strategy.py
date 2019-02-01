
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
                         order_target_percent, symbol,symbols, record)


from zipline import TradingAlgorithm
from ETF.AAA import AAA
from ML.Features import *
from ML.Targets import *

import matplotlib.pyplot as plt

class TestNN(AAA) :

    params = {}
    train_win = 0
    nn_win = 0
    ml = 'SVM'
    atr = []
    enable_stoploss = False

    def set_params(self, t_win, n_win, ml='SVM', stoploss=False, rsi=False, vol=False) :
        self.train_win = t_win
        self.nn_win = n_win
        self.ml = ml
        self.atr_len = self.train_win
        self.enable_stoploss = stoploss
        self.enable_RSI = rsi
        self.enable_VOL = vol
        return self

    '''
    Using the last N days price directions as the features
    Target using the next day price direction
    '''
    def create_features(self, df, n = 5) :
        df_target = target_direction(df, 1)
        df_target.columns = ['target']

        list_df_features = []
        for i in xrange(n):
            list_df_features.append(direction(df, i+1))

        df_features = pd.DataFrame()
        for l in list_df_features:
            df_features = df_features.join(l, how='outer')

        if self.enable_RSI:
            df_features['RSI_3'] = ta.RSI(df.values.ravel(), n-1)
            # df_features['RSI_3'] = (ta.RSI(df.values.ravel(), n) > 50) * 1

        if self.enable_VOL:
            df_features['Std'] = pd.rolling_std(df, n-1)

        # adding the target
        df_features = df_features.join(df_target, how='outer')
        #df_features.dropna(inplace=True)

        return df_features.iloc[:, :-1], df_features.iloc[:, [-1]]

    def initialize(self, context):
        add_history(200, '1d', 'price')
        set_slippage(slippage.FixedSlippage(spread=0.0))
        set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.0))
        context.tick = 0

        dp_data = self.data
        df_data = pd.DataFrame(index=dp_data.axes[1])
        df_data['close'] = dp_data[:, :, 'close']
        df_data['open'] = dp_data[:, :, 'open']
        df_data['high'] = dp_data[:, :, 'high']
        df_data['low'] = dp_data[:, :, 'low']
        df_data['volume'] = dp_data[:, :, 'volume']

        self.atr = atr_per_close(df_data, atrLen = self.atr_len)
        context.longstop = 0

    def handle_data(self, context, data):

        context.tick += 1
        total_window = self.train_win + self.nn_win + 1

        if context.tick < (total_window):
            return

        try :
#             print 'tick = {t}'.format(t = context.tick)
            price = history(total_window - 1, '1d', 'price').dropna()
            df_price = pd.DataFrame(data=price.values, index=price.index, columns=['close'])

            features, target = self.create_features(df_price, self.nn_win)
            features_insample = features.iloc[(self.nn_win -1):-1, :].values
            target_insample = target.iloc[(self.nn_win -1):-1, :].values.ravel()

            features_oosample = features.iloc[-1, :]
            features_oosample = features_oosample.values.reshape([1, len(features_oosample)])

            ATR = self.atr.loc[price.index[-1], :][0]

            symbol = price.columns[0]


            if self.enable_stoploss:
                if data[symbol].price < context.longstop:
                    print 'Stop Loss '
                    order_target_percent(symbol, 0.0)
                    context.longstop = 0.0
                    return

            if self.ml == 'SVM' :
                ### Training the SVM
                from sklearn import svm
                model_svm = svm.SVC()
                model_svm.fit(features_insample, target_insample)

                preds_svm = model_svm.predict(features_oosample)[0]
                if preds_svm < 0.5:
                    #print "Sell "
                    order_target_percent(symbol, 0.0)
                    context.longstop = 0.0

                else :
                    #print "Buy"
                    order_target_percent(symbol, 1.0)
                    context.longstop = max(context.longstop, data[symbol].price * (1 - 0.7*ATR))
                    print "target sl = {n}".format(n=context.longstop)

            if self.ml == 'KNN' :
                ### Training the SVM
                from sklearn import neighbors
                k = 10

                model_knn = neighbors.KNeighborsClassifier(k, 'distance')
                model_knn.fit(features_insample, target_insample)

                preds_knn = model_knn.predict(features_oosample)[0]

                if preds_knn < 0.5:
                    #print "Sell "
                    order_target_percent(symbol, 0.0)
                else :
                    #print "Buy"
                    order_target_percent(symbol, 1.0)

            record('price', data[symbol]['price'])
        except :
            pass


class MLStrategy :
    def __init__(self):
        pass

    def getData(self, tickers) :
        settings = Settings()
        dp = TimeSeries(settings).get_agg_ETF_data(tickers)
        dp = dp.fillna(method='pad', axis=0)
        dp = dp.fillna(method='bfill', axis=0)
        dp = dp.dropna()

        dp = dp.reindex_axis(['open', 'high', 'low', 'close', 'volume', 'price'], axis=2)
        return dp


    def load_data(self, tickers) :
        dp = self.getData(tickers)
        dfs = {}

        for ticker in tickers:
            dfs[ticker] = dp[ticker]
        return dfs

    def create_features(self, df):
        pass



###################################################################
from numpy import *
from scipy.optimize import minimize


def cost_function(theta, *args ):
    '''
    X_n - standardized returns
    X - returns
    theta - parameter set as [1, xt, ... xt-m, Ft-1]
    miu - number of shares to buy/sell
    delta - transaction cost
    '''
    (Xn, X) = args[0]
    M = len(theta) - 2
    T = len(X) - M

    miu = 1 # buy/sell 1 share
    delta = 0.001 # 0.1% transaction cost

    Ft, dFt = update_Ft(Xn, theta)
    Ret, A, B, D, sharpe = reward_function(X, Ft, miu, delta)
    J = sharpe_ratio(Ret) * -1

    # dD_dRet = (B[-2] - A[-2]*Ret[-1]) / power(B[-2] - A[-2]*A[-2], 1.5)
    # dRet_dFt = -1 * miu * delta * abs(Ft[-1] - Ft[-2])
    # dRet_dFtt = miu * Ret[-1] + miu * delta * abs(Ft[-1] - Ft[-2])
    # dFt_dw = dFt[-1,:]
    # dFtt_dw = dFt[-2,:]
    #
    #
    #
    #
    # grad = dD_dRet * (dRet_dFt * dFt_dw + dRet_dFtt * dFtt_dw)
    # grad = grad.ravel() * -1
    print "J={j}".format(j=J)
    return J

    ''' test1
    A = mean(Ret)
    B = mean(Ret*Ret)
    dS_dA = (B-3*A*A) / power(B-A*A, 1.5)
    dS_dB = A / power(B-A*A, 1.5)

    dA_dRet = np.ones(T) / float(T)
    dB_dRet = np.ones(T) * 2 * Ret[M:]  / float(T)


    dRet_dFt = np.zeros(len(Ft))
    dRet_dFtt = np.zeros(len(Ft))
    dRet_dFt[1:] = -1 * miu * sign(Ft[1:] - Ft[:-1])
    dRet_dFtt[1:] = miu * Ret[1:] + miu * delta * sign(Ft[1:] - Ft[:-1])


    part1 = dot(dS_dA, dA_dRet) + dot(dS_dB, dB_dRet)


    a = np.dot(dRet_dFt[M:].reshape([T,1]), np.ones([1, M+2]))
    a = a * dFt[M:]
    b = np.dot(dRet_dFtt[M:].reshape([T,1]), np.ones([1, M+2]))
    b = b * dFt[M-1:-1]

    grad = np.dot(part1.reshape([1,T]), (a+b))
    grad = grad.ravel() * -1
    '''




def cost_function1(theta, *args ):
    '''
    X_n - standardized returns
    X - returns
    theta - parameter set as [1, xt, ... xt-m, Ft-1]
    miu - number of shares to buy/sell
    delta - transaction cost
    '''
    (Xn, X) = args[0]



    M = len(theta) - 2
    T = len(X) - M

    miu = 1 # buy/sell 1 share
    delta = 0.001 # 0.1% transaction cost

    Ft, dFt = update_Ft(Xn, theta)
    Ret, sharpe, D = reward_function(X, Ft, miu, delta)
    J = sharpe * -1
    return J

def update_Ft(Xn, theta) :
    '''
    update_Ft: create a series of Ft(the action decision)
    based on the theta , and the input paramters
    Ft = tanh(theta * xt), where xt = [1, X1, ... Xm, Ft-1].
    '''

    M = len(theta) - 2 # theta contains M+2 factors

    Ft = np.zeros(len(Xn))
    dFt = np.zeros([len(Xn), len(theta)])
    for i in range(len(Xn)) :
        if i < M -1 :
            continue
        xt = [1] + list(Xn[i-M+1:i+1]) + [Ft[i-1], Ft[i-2]]
        Ft[i] = tanh(np.dot(xt, theta))
        dFt[i, :] = (1-Ft[i]*Ft[i])* (xt + theta[-1] * dFt[i-1, :])
    return Ft, dFt






def feature_normalization(X) :
    mu = mean(X)
    sigma = std(X)
    Xn = (X - mu) / sigma
    return Xn

def reward_function(X, Ft,  miu, delta):
    '''
    reward_function: calcualte R - the wealth gain during each
    decision Ft. Rt = mu * (Ft-1 * Xt - delta * abs(Ft - Ft-1))
    '''
    Ret = np.zeros(len(Ft))
    Ret[1:] = miu * (Ft[:-1] * X[1:] - delta * abs(Ft[1:] - Ft[:-1]))

    T = len(Ft)

    A = np.zeros(T)
    B = np.zeros(T)
    sharpe = np.zeros(T)
    D = np.zeros(T)

    seta = 0.05
    for i in range(T) :
        if i < 1:
            continue
        A[i] = A[i-1] + seta * (Ret[i] - A[i-1])
        B[i] = B[i-1] + seta * (Ret[i] * Ret[i] - B[i-1])
        D[i] = B[i-1]*(Ret[i] - A[i-1]) - 0.5 * A[i-1] * (Ret[i]*Ret[i] - B[i-1])
        D[i] = D[i] / power(B[i-1] - A[i-1]*A[i-1], 1.5)
        if isnan(D[i]) :
            D[i] = 0
        sharpe[i] = sharpe[i-1] + seta * D[i]



#     dD_dRt = (B[-2] - A[-2]*Ret[-1]) / power(B[-2] - A[-2]*A[-2], 1.5)
    return Ret, A, B, D, sharpe

def sharpe_ratio(X) :
    return mean(X)/std(X)


if __name__  == "__main__" :
    '''
    tickers = ['GOOG/NYSE_SPY']

    settings = Settings()
    dp = TimeSeries(settings).get_agg_ETF_data(tickers)
    dp = dp.fillna(method='pad', axis=0)
    dp = dp.fillna(method='bfill', axis=0)
    dp = dp[:,'2010-01-01'::,:]
    dp = dp.dropna()

    #dp1 = dp.reindex_axis(['open_price', 'high', 'low', 'close_price', 'volume', 'price'], axis=2)


    rets = pd.DataFrame()
    #nn = [2, 5, 10, 20, 50]
    #nn = [50, 100]
    nn = [10]
    for n in nn:
        print "running {n}".format(n=n)
        rets['nn={n}, with rsi, vol'.format(n=n)] = TestNN(dp).set_params(30, n, ml='KNN', rsi=True, vol=True).run_trading().portfolio_value
        rets['nn={n}, with rsi, w/o vol'.format(n=n)] = TestNN(dp).set_params(30, n, ml='KNN', rsi=True, vol=False).run_trading().portfolio_value
        rets.plot(figsize=[20,12])

    print 'done!'
    '''

    import Quandl
    df_spy = Quandl.get('GOOG/NYSE_XLF')

    X = df_spy['Close'].pct_change().dropna().values
    Xn = feature_normalization(X)

    T = len(X)
    M = 10
    miu = 1
    delta = 0.001
    rho = -0.1

    ### in-sample test
    init_theta = np.ones(M+2)
    output= minimize(cost_function, init_theta, args=[Xn, X]
                     , options={'xtol': 1e-8, 'disp': True})

    theta = output.x #+ rho * output.jac


    Ft_i, _ = update_Ft(X, theta)
    Ret_i, _, _, _, sharpe = reward_function(X, Ft_i, miu, delta)
    print "oos sharpe={s}".format(s=sharpe_ratio(X)*np.sqrt(252))
    plt.plot(np.cumprod(1+Ret_i))

    ####

    LB = 1000
    LF = 100



    Ret = []
    Ft = []
    plt.figure(figsize=[10,10])
    for i in range(T) :
        if i < (LB+M+2):
            continue
        if (i+1)%LF == 0: # time to train the data and invest
            print "i={i}".format(i=i)
            t_start = i+1 - LB -(M+2)
            t_end = i
            i_start = i+1
            i_end = i+LF

            init_theta = np.ones(M+2)
            output= minimize(cost_function, init_theta, args=[Xn[t_start:t_end+1], X[t_start:t_end+1]]
                             ,jac=True, options={'xtol': 1e-8, 'disp': True})

            theta = output.x #+ rho * output.jac


            Ft_i, _ = update_Ft(X[i_start-(M+2):i_end+1], theta)
            Ret_i, _, _, _, sharpe = reward_function(X[i_start-(M+2):i_end+1], Ft_i, miu, delta)
            print "oos sharpe={s}".format(s=sharpe_ratio(X[i_start-(M+2):i_end+1])*np.sqrt(252))
            Ret = Ret + list(Ret_i[M+2:])
            Ft = Ft + list(Ft_i[M+2:])
            print Ft_i[M+2:]


            plt.plot(np.cumprod(1+np.array(Ret)))
    plt.plot(np.cumprod(1+X))
    plt.plot(np.cumprod(1+X)*(Ft<0), 'ro')