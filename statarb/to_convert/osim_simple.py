#!/usr/bin/env python 

#from util import *
#from regress import *
#from loaddata import *

from __future__ import print_function
import openopt

from collections import defaultdict
from datetime import timedelta
import argparse
import glob

import pandas as pd
import numpy as np

dflist = list()
for file in glob.glob("*.txt"):
    df = pd.read_csv(file, sep=" ", names=['fcast', "blah", "date", "time", "not", "cumpnl", "dpnl", "bps", "turn", "other"])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index(['date', 'fcast'])
    dflist.append(df)
    df = pd.concat(dflist)

cols = df['bps'].unstack().columns

def fcn(weights, start, end):
    cov_one_df = df[ (df.index.get_level_values('date') > start) & (df.index.get_level_values('date') < end) ]['bps'].unstack().fillna(0).cov()
    pvar = 0
    for ii in range(0,10):
        pvar += weights[ii] * cov_one_df.values[ii,ii] * cov_one_df.values[ii,ii] 

    for ii in range(0,10):
        for jj in range(0,10):
            pvar += 2 * weights[ii] * weights[jj] * cov_one_df.values[ii, jj]

    pret = 1
    ret_df = df[ (df.index.get_level_values('date') > start) & (df.index.get_level_values('date') < end) ]['bps'].unstack().fillna(0).mean()
    for ii in range(0,10):
        pret += weights[ii] * ret_df.values[ii]

#    print "{} {} {}".format((pret * 252) / np.sqrt(pvar * 252), pret * 252, np.sqrt(pvar * 252))
    return 1 / np.sqrt(pvar)

def sharpe_fcn(weights, start, end):
    cov_one_df = df[ (df.index.get_level_values('date') > start) & (df.index.get_level_values('date') < end) ]['bps'].unstack().fillna(0).cov()
    pvar = 0
    for ii in range(0,10):
        pvar += weights[ii] * cov_one_df.values[ii,ii] * cov_one_df.values[ii,ii] 

    for ii in range(0,10):
        for jj in range(0,10):
            pvar += 2 * weights[ii] * weights[jj] * cov_one_df.values[ii, jj]

    pret = 0
    ret_df = df[ (df.index.get_level_values('date') > start) & (df.index.get_level_values('date') < end) ]['bps'].unstack().fillna(0).mean()
    for ii in range(0,10):
        pret += weights[ii] * ret_df.values[ii]

    print("{} {} {}".format((pret * 252) / np.sqrt(pvar * 252), pret * 252, np.sqrt(pvar * 252)))
    return (pret * 252) / np.sqrt(pvar * 252)

mean = 0 
cnt = 0
gstart = pd.to_datetime("20110101")
start = pd.to_datetime("20110101")
end = pd.to_datetime("20110101") + timedelta(days=30)
while end < pd.to_datetime("20130101"):
    lb = np.ones(10) * 0.0
    ub = np.ones(10) 
    plotit = False
    initial_weights = np.asarray([.5, .5, .5, .5, .5, .5, .5, .5, .5, .5])
    #initial_weights = np.asarray([0, 0, 0, 0, 1, 0, 0, 0, 0, 0])

    p = openopt.NSP(goal='max', f=fcn, x0=initial_weights, lb=lb, ub=ub)
    p.args.f = (start, end)
    p.ftol = 0.001
    p.maxFunEvals = 300
    r = p.solve('ralg')
    if (r.stopcase == -1 or r.isFeasible == False):
        print(objective_detail(target, *g_params))
        raise Exception("Optimization failed")

    print(r.xf)

    for ii in range(0,10):
        print("{}: {}".format(cols[ii], r.xf[ii]))
        ii += 1

    wtrecent = r.xf

    p = openopt.NSP(goal='max', f=fcn, x0=initial_weights, lb=lb, ub=ub)
    p.args.f = (gstart, end)
    p.ftol = 0.001
    p.maxFunEvals = 300
    r = p.solve('ralg')
    if (r.stopcase == -1 or r.isFeasible == False):
        print(objective_detail(target, *g_params))
        raise Exception("Optimization failed")

    print(r.xf)

    for ii in range(0,10):
        print("{}: {}".format(cols[ii], r.xf[ii]))
        ii += 1

    wtall = r.xf
    
    #fcn(initial_weights, start='20110701', end='20120101')
    wts = np.ones(10) * 0.0
    for ii in range(0, 10):
        wts[ii] = (wtall[ii] + wtrecent[ii]) / 2

    start = end
    end = end + timedelta(days=30)
    sharpe = sharpe_fcn(wts, start, end)
    print("OS: {} {}".format(end, sharpe))
    mean += sharpe
    cnt += 1

print(mean/cnt)

