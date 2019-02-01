import pandas as pd
import argparse
import numpy as np
import random
import matplotlib.pyplot as plt
from sklearn import linear_model


class Portfolio(object):
    def __init__(self, sec1mean, sec2mean, sec1vol, sec2vol, corr, rebalance_threshold):
        self.numberOfStocks = 2
        self.initprices = np.asarray([5, 5])
        self.prices = self.initprices
        self.initholdings = [10, 10]
        self.holdings = self.initholdings
        self.inittotal = 100
        self.total = self.inittotal
        self.initweightings = [.5, .5]
        self.weightings = self.initweightings
        # input
        self.means = np.asarray([sec1mean, sec2mean])
        self.corr = corr
        self.sec1vol = sec1vol
        self.sec2vol = sec2vol
        self.dailymeans = self.means / 252
        self.dailysec1vol = self.sec1vol / np.sqrt(252)
        self.dailysec2vol = self.sec2vol / np.sqrt(252)
        dailycov = self.dailysec1vol * self.dailysec2vol * self.corr
        self.dailycovmat = np.asarray([[self.dailysec1vol ** 2, dailycov], [dailycov, self.dailysec2vol ** 2]])
        self.rebalance_threshold = rebalance_threshold

    # simulate price movements
    def Brownian(self, periods):
        dt = 1
        # standard brownian increment = multivariate_normal distribution * sqrt of dt
        b = np.random.multivariate_normal((0., 0.), ((1., 0.), (0., 1.)), int(periods)) * np.sqrt(dt)
        # standard brownian motion for two variables ~ N(0,t)
        W = np.cumsum(b, axis=0)
        W = np.insert(W, 0, (0., 0.), axis=0)
        W = np.asarray(W)
        return W

    # So:     initial stock price
    # W:      brownian motion
    # T:      time period
    def GBM(self, W, T):
        S = []
        # divide time axis from 0 to 1 into T pieces,
        t = np.linspace(0, T, T + 1)
        L = np.linalg.cholesky(self.dailycovmat)
        var = self.dailycovmat.diagonal()
        for i in range(T + 1):
            drift = (self.dailymeans - (0.5 * var)) * t[i]
            diffusion = np.dot(L, W[i])
            S.append(self.initprices * np.exp(drift + diffusion))
        S = np.asarray(S)
        return S

    def PriceMove(self, periods):
        W = self.Brownian(periods)
        return self.GBM(W, periods)

    # simulate portfolio performance
    def Simulate(self, paths, tcost, periods, seed):
        cost = 0
        trade = 0
        nRebalance = 0
        decreaseReturn = 0
        fig, ax = plt.subplots(nrows=1, ncols=1)
        np.random.seed(seed)
        for i in range(paths):
            pricemovements = self.PriceMove(periods)
            print("path %d: " % (i + 1))
            tradePath, costPath, nRebalancePath, decreaseReturnPath = self.Rebalance(pricemovements, tcost, periods)
            cost += costPath
            trade += tradePath
            nRebalance += nRebalancePath
            decreaseReturn += decreaseReturnPath
            t = np.linspace(0, periods, periods + 1)
            image, = ax.plot(t, pricemovements[:, 0], label="stock1")
            image, = ax.plot(t, pricemovements[:, 1], label="stock2", ls='--')
            plt.ylabel('stock price, $')
            plt.xlabel('time, day')
            plt.title('correlated brownian simulation')
            plt.draw()
            fig.savefig("simulate.png")
        averageRebalance = nRebalance / paths
        averageDollarTraded = trade / paths
        averageTcost = cost / paths
        averageDecreaseReturn = decreaseReturn / paths
        print(
            "average number of rebalances: %.3f\naverage dollars traded: %.3f$\naverage transaction cost as percentage of book value: %.3f%%\nexpected transaction costs: %.3f%%"
            % (averageRebalance, averageDollarTraded, averageTcost * 100, averageDecreaseReturn * 100))

    def Rebalance(self, pricemovements, tcost, periods):
        trades = []
        priceSpread = []
        costs = []
        nRebalance = 0
        # len(pricemovements) = periods + 1
        for i in range(1, periods + 1):
            newPrices = pricemovements[i]
            # update prices, dollar value, and weightings of a portfolio each time prices change
            self.updatePrices(newPrices)
            difference = np.subtract(self.weightings, self.initweightings)
            # max returns a (positive) percentage difference between the actual weigntings and the desired weightings
            if max(difference) >= self.rebalance_threshold:
                # change the holdings so that the actual weightings are as desired
                self.updateHoldings()
                # difference in weightings * total = change of the amount of dollar invested in two stocks
                trade = np.sum(np.absolute(difference * self.total))
                trades.append(trade)
                costs.append(trade * tcost)
                priceSpread.append(np.round(self.prices, 2))
                nRebalance += 1
        # pandaframe
        data = {"price spread, $": priceSpread,
                "size of the trade, $": trades,
                "transaction cost, $": costs}
        df = pd.DataFrame(data=data, index=range(1, nRebalance + 1))
        df.index.name = "#rebalancing"
        print(df)
        # return metrics
        tradeTotal = sum(trades)
        costTotal = tradeTotal * tcost
        annualizedPeriods = periods / 252
        annualizedReturn = (self.total / self.inittotal) ** (1 / annualizedPeriods) - 1
        postcost = ((self.total - costTotal) / self.inittotal) ** (1 / annualizedPeriods) - 1
        decreaseReturn = annualizedReturn - postcost
        costTotalPer = costTotal / self.total
        # set parameters back to initial value
        self.reset()
        return tradeTotal, costTotalPer, nRebalance, decreaseReturn

    def reset(self):
        self.weightings = self.initweightings
        self.holdings = self.initholdings
        self.prices = self.initprices
        self.total = self.inittotal

    def updatePrices(self, newPrices):
        self.prices = newPrices
        # dot product of the number of shares and price per share
        self.total = np.dot(self.holdings, newPrices)
        # the weight of stocks after stock prices change = (number of share * price of stock per share)/total amount of asset
        self.weightings = [holding * price / self.total for price, holding in zip(self.prices, self.holdings)]

    def updateHoldings(self):
        self.holdings = [self.total * initWeight / price for initWeight, price in zip(self.initweightings, self.prices)]
        self.weightings = [price * holding / self.total for holding, price in zip(self.holdings, self.prices)]

    # compute how tcost vary with respect to other variables
    def decreaseReturn(self, pricemovements, tcost, periods):
        costTotal = 0
        for i in range(1, len(pricemovements)):
            newPrices = pricemovements[i]
            self.updatePrices(newPrices)
            difference = np.subtract(self.weightings, self.initweightings)
            if max(difference) >= self.rebalance_threshold:
                self.updateHoldings()
                trade = np.sum(np.absolute(difference * self.total))
                costTotal += trade * tcost
        annualizedPeriods = periods / 252
        annualizedReturn = (self.total / self.inittotal) ** (1 / annualizedPeriods) - 1
        postcost = ((self.total - costTotal) / self.inittotal) ** (1 / annualizedPeriods) - 1
        decreaseReturn = annualizedReturn - postcost
        self.reset()
        return decreaseReturn

    def Tests(self, paths, tcost, periods, step, seed):
        meanDecrease = []
        totalDecrease = 0
        fig, ax = plt.subplots(nrows=1, ncols=1)
        np.random.seed(seed)
        for i in range(1, paths + 1):
            pricemovements = self.PriceMove(periods)
            decreaseReturn = self.decreaseReturn(pricemovements, tcost, periods)
            totalDecrease += decreaseReturn * 100
            if (i % step == 0):
                meanDecrease.append(totalDecrease / i)
        print("when seed = %d, paths = %d, the average transaction cost is: %f%%" % (seed, paths, meanDecrease[-1]))
        t = np.linspace(1, paths, len(meanDecrease))
        image, = ax.plot(t, meanDecrease)
        plt.ylabel('sample mean transaction cost (%)')
        plt.xlabel('number of paths')
        plt.title('convergence test (seed = %d)' % (seed))
        plt.draw()
        fig.savefig("convergence test (seed=%d).png" % (seed))

    def updateCorr(self, corr):
        dailycov = self.dailysec1vol * self.dailysec2vol * corr
        self.dailycovmat = np.asarray([[self.dailysec1vol ** 2, dailycov], [dailycov, self.dailysec2vol ** 2]])

    def updateSec1Vol(self, sec1vol):
        self.sec1vol = sec1vol
        self.dailysec1vol = sec1vol / np.sqrt(252)
        dailycov = self.dailysec1vol * self.dailysec2vol * self.corr
        self.dailycovmat = np.asarray([[self.dailysec1vol ** 2, dailycov], [dailycov, self.dailysec2vol ** 2]])

    def updateThreshold(self, threshold):
        self.rebalance_threshold = threshold

    def updateSec1Mean(self, sec1mean):
        self.means[0] = sec1mean
        self.dailymeans = self.means / 252

    def solveCorr(self, paths, tcost, periods, seed):
        start = 0
        end = 1
        x = np.linspace(0, 1, 11)
        y = []
        for i in range(len(x)):
            totalDecrease = 0
            self.updateCorr(x[i])
            np.random.seed(seed)
            for i in range(paths):
                pricemovements = self.PriceMove(periods)
                decreaseReturn = self.decreaseReturn(pricemovements, tcost, periods)
                totalDecrease += decreaseReturn * 100
            meanDecrease = np.round(totalDecrease / paths, 1)
            y.append(meanDecrease)
        fig, ax = plt.subplots(nrows=1, ncols=1)
        image, = ax.plot(x, y)
        plt.ylabel('transaction cost (%)')
        plt.xlabel('correlation coefficient')
        plt.title('corr - tcost graph')
        plt.draw()
        fig.savefig('corr-tcost graph')
        print(
            'corr-tcost:\nseed=%d\nsec1vol=%.2f\nsec2vol=%.2f\ncorr=%.2f-%.2f\nsec1mean=%.2f\nsec2mean=%.2f\nthreshold=%.2f'
            % (seed, self.sec1vol, self.sec2vol, start, end, self.means[0], self.means[1], self.rebalance_threshold))
        print('coeff:', np.polyfit(x, y, 1))
        '''reg = linear_model.Lasso(alpha = 0.1)
        reg.fit(x,y)
        print('lasso coeff:',reg.coef_)
        print('lasso intercept',reg.intercept_)'''

    def solveSec1Vol(self, paths, tcost, periods, seed):
        start = .01
        end = .51
        x = np.linspace(start, end, 11)
        y = []
        for i in range(len(x)):
            totalDecrease = 0
            self.updateSec1Vol(x[i])
            np.random.seed(seed)
            for i in range(paths):
                pricemovements = self.PriceMove(periods)
                decreaseReturn = self.decreaseReturn(pricemovements, tcost, periods)
                totalDecrease += decreaseReturn * 100
            meanDecrease = np.round(totalDecrease / paths, 1)
            y.append(meanDecrease)
        fig, ax = plt.subplots(nrows=1, ncols=1)
        image, = ax.plot(x, y)
        plt.ylabel('transaction cost (%)')
        plt.xlabel('security 1 volatility')
        plt.title('sec1vol - tcost graph')
        plt.draw()
        fig.savefig('sec1vol-tcost graph')
        print(
            'sec1vol_tcost:\nseed=%d\nsec1vol=%.2f-%.2f\nsec2vol=%.2f\ncorr=%.2f\nsec1mean=%.2f\nsec2mean=%.2f\nthreshold=%.2f'
            % (seed, start, end, self.sec2vol, self.corr, self.means[0], self.means[1], self.rebalance_threshold))
        print("coeff:", np.polyfit(x, y, 1))

    def solveSec1Mean(self, paths, tcost, periods, seed):
        start = 0
        end = .5
        x = np.linspace(0, .5, 11)
        paths = 500
        y = []
        for i in range(len(x)):
            totalDecrease = 0
            self.updateSec1Mean(x[i])
            np.random.seed(seed)
            for i in range(paths):
                pricemovements = self.PriceMove(periods)
                decreaseReturn = self.decreaseReturn(pricemovements, tcost, periods)
                totalDecrease += decreaseReturn * 100
            meanDecrease = np.round(totalDecrease / paths, 1)
            y.append(meanDecrease)
        fig, ax = plt.subplots(nrows=1, ncols=1)
        image, = ax.plot(x, y)
        plt.ylabel('transaction cost (%)')
        plt.xlabel('security 1 return')
        plt.title('sec1mean - tcost graph')
        plt.draw()
        fig.savefig('sec1mean-tcost graph')
        print(
            'sec1mean-tcost:\nseed=%d\nsec1vol=%.2f\nsec2vol=%.2f\ncorr=%.2f\nsec1mean=%.2f-%.2f\nsec2mean=%.2f\nthreshold=%.2f'
            % (seed, self.sec1vol, self.sec2vol, self.corr, start, end, self.means[1], self.rebalance_threshold))
        print('coef:', np.polyfit(x, y, 1))

    def solveThreshold(self, paths, tcost, periods, seed):
        start = 1
        end = 10
        x = np.linspace(1, 10, 11)
        y = []
        for i in range(len(x)):
            totalDecrease = 0
            self.updateThreshold(x[i] / 100)
            np.random.seed(seed)
            for i in range(paths):
                pricemovements = self.PriceMove(periods)
                decreaseReturn = self.decreaseReturn(pricemovements, tcost, periods)
                totalDecrease += decreaseReturn * 100
            meanDecrease = np.round(totalDecrease / paths, 1)
            y.append(meanDecrease)
        fig, ax = plt.subplots(nrows=1, ncols=1)
        image, = ax.plot(x, y)
        plt.ylabel('transaction cost (%)')
        plt.xlabel('rebalance threshold (%)')
        plt.title('threshold - tcost graph')
        plt.draw()
        fig.savefig("threshold-tcost graph")
        print(
            "threshold-tcost:\nseed=%d\nsec1vol=%.2f\nsec2vol=%.2f\ncorr=%.2f\nsec1mean=%.2f\nsec2mean=%.2f\nthreshold=%.2f-%.2f"
            % (seed, self.sec1vol, self.sec2vol, self.corr, self.means[0], self.means[1], start, end))
        print('coef:', np.polyfit(x, y, 1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sec1vol", help="annualized volatility of security 1", type=float, default=.4)
    parser.add_argument("--sec2vol", help="annualized volatility of security 2", type=float, default=.3)
    parser.add_argument("--corr", help="correlation between security 1 and 2", type=float, default=.8)
    parser.add_argument("--sec1mean", help="annualized return of security 1", type=float, default=.05)
    parser.add_argument("--sec2mean", help="annualized return of security 2", type=float, default=.1)
    parser.add_argument("--paths", help="number of monte carlo iterations", type=int, default=500)
    parser.add_argument("--periods", help="number of days", type=int, default=252)
    parser.add_argument("--tcost", help="transaction cost per trade", type=float, default=.1)
    parser.add_argument("--rebalance_threshold", help="the minimal divergence that causes rebalance", type=float,
                        default=.01)
    parser.add_argument("--seed", help="set seed for the simulation", type=int, default=5)
    parser.add_argument("--simulate",
                        help="plot price movements of two stocks and print information about their transaction costs",
                        type=bool, default=False)
    parser.add_argument("--convergence_test", help="test convergence of transaction cost", type=bool, default=False)
    parser.add_argument("--step", help="set the step for convergence test", type=int, default=10)
    parser.add_argument("--solveCorr", help="solve transaction cost with respect to correlation coefficient", type=bool,
                        default=False)
    parser.add_argument("--solveVol", help="solve transaction cost with respect to the volatity of a security",
                        type=bool, default=False)
    parser.add_argument("--solveReturn", help="solve transaction cost with respect to the return of a security",
                        type=bool, default=False)
    parser.add_argument("--solveThreshold", help="solve transaction cost with respect to the rebalance threshold",
                        type=bool, default=False)
    args = parser.parse_args()
    portfolio = Portfolio(args.sec1mean, args.sec2mean,
                          args.sec1vol, args.sec2vol, args.corr, args.rebalance_threshold)
    if args.simulate == True:
        portfolio.Simulate(args.paths, args.tcost, args.periods, args.seed)
    elif args.convergence_test == True:
        portfolio.Tests(args.paths, args.tcost, args.periods, args.step, args.seed)
    elif args.solveCorr == True:
        portfolio.solveCorr(args.paths, args.tcost, args.periods, args.seed)
    elif args.solveVol == True:
        portfolio.solveSec1Vol(args.paths, args.tcost, args.periods, args.seed)
    elif args.solveThreshold == True:
        portfolio.solveThreshold(args.paths, args.tcost, args.periods, args.seed)
    elif args.solveReturn == True:
        portfolio.solveSec1Mean(args.paths, args.tcost, args.periods, args.seed)


main()
