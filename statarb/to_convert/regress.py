#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import glob
import argparse
import re
import math
from collections import defaultdict
from dateutil import parser as dateparser

import time
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

import statsmodels.api as sm

from util import *
from calc import *

ADV_POWER = 1/2

def plot_fit(fits_df, name):
    print("Plotting fits...")
    print(fits_df)
    plt.figure()
    plt.xlim(0, fits_df.horizon.max() + 1)
    plt.errorbar(fits_df.horizon, fits_df.coef, yerr=fits_df.stderr * 2, fmt='o')
    plt.errorbar(fits_df.horizon, fits_df.intercept, yerr=fits_df.stderr * 0, fmt='o', color='red')
    plt.axhline(0, color='black')            
    plt.savefig(name + ".png")

def extract_results(results, indep, horizon):
    ret = dict()
    ret['indep'] = [indep]
    ret['horizon'] = [horizon]
    ret['nobs'] = [results.nobs]
    if len(results.params) > 1:
        ret['coef'] = [results.params[1]]
        ret['stderr'] = [results.bse[1]]
        ret['tstat'] = [results.tvalues[1]]
        ret['intercept'] = [results.params[0]]
    else:
        ret['coef'] = [results.params[0]]
        ret['stderr'] = [results.bse[0]]
        ret['tstat'] = [results.tvalues[0]]
        ret['intercept'] = [0]
        
    return pd.DataFrame(ret)

def get_intercept(daily_df, horizon, name, middate=None):
    insample_daily_df = daily_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr', 'intercept'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, name, ii, True, 'daily') 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    result = dict()
    for ii in range(1, horizon+1):
        result[ii] = float(fits_df.ix[name].ix[ii].ix['intercept'])

    return result

def regress_alpha(results_df, indep, horizon, median=False, rtype='daily', intercept=True, start=None, end=None):
    if start is not None and end is not None:
        print("restrict fit from {} to {}".format(start, end))
        results_df = results_df.truncate(before=dateparser.parse(start), after=dateparser.parse(end))

    if median:
        medians_df = pd.DataFrame(columns=['indep', 'horizon', 'coef', 'stderr', 'tstat', 'nobs', 'intercept'], dtype=float)
        start = 1
        cnt = len(results_df)
        window = int(cnt/3)
        end = window
        while end <= cnt:
            print("Looking at rows {} to {} out of {}".format(start, end, cnt))
            timeslice_df = results_df.iloc[start:end]        
            if rtype == 'intra_eod':
                fitresults_df = regress_alpha_intra_eod(timeslice_df, indep)
            elif rtype == 'daily':
                fitresults_df = regress_alpha_daily(timeslice_df, indep, horizon, intercept)
            elif rtype == 'dow':
                fitresults_df = regress_alpha_dow(timeslice_df, indep, horizon)
            elif rtype == 'intra':
                fitresults_df = regress_alpha_intra(timeslice_df, indep, horizon)
            else:
                raise "Bad regression type: {}".format(rtype)

            print(fitresults_df)
            medians_df = medians_df.append(fitresults_df)
            start += window
            end += window
    
        print("Out of sample coefficients:")
        print(medians_df)
        ret = medians_df.groupby(['indep', 'horizon']).median().reset_index()
        return ret
    else:
        timeslice_df = results_df
        if rtype == 'intra':
            return regress_alpha_intra(timeslice_df, indep, horizon)
        elif rtype == 'daily':
            return regress_alpha_daily(timeslice_df, indep, horizon, intercept)
        elif rtype == 'dow':
            return regress_alpha_dow(timeslice_df, indep, horizon)

def regress_alpha_daily(daily_df, indep, horizon, intercept=True):
    print("Regressing alphas daily for {} with horizon {}...".format(indep, horizon))
    retname = 'cum_ret'+str(horizon) 

    fitdata_df = daily_df[ [retname, 'mdvp', indep] ]
#    print fitdata_df.tail()
    fitdata_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    fitdata_df = fitdata_df.dropna()

    weights = fitdata_df['mdvp'] ** ADV_POWER
    ys = winsorize_by_date(fitdata_df[retname])
    ys = np.exp(ys) - 1
    xs = winsorize(fitdata_df[indep])
    if intercept:
        xs = sm.add_constant(xs)
    results_wls = sm.WLS(ys, xs, weights=weights).fit()
    print(results_wls.summary())
    results_df = extract_results(results_wls, indep, horizon)
    return results_df

def regress_alpha_intra_eod(intra_df, indep):
    print("Regressing intra alphas for {} on EOD...".format(indep))
    results_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'], dtype=float)
    fitdata_df = intra_df[  ['log_ret', indep, 'mdvp', 'close', 'iclose'] ]
    fitdata_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    fitdata_df = fitdata_df.dropna()

    it = 1
    for timeslice in ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00' ]:
        print("Fitting for timeslice: {}".format(timeslice))

        timeslice_df = fitdata_df.unstack().between_time(timeslice, timeslice).stack()
        timeslice_df['day_ret'] = (timeslice_df['close'] - timeslice_df['iclose']) / timeslice_df['iclose']
 #       timeslice_df['day_ret'] = np.log(timeslice_df['close'] / timeslice_df['iclose'])

        weights = np.sqrt(timeslice_df['mdvp'])
        weights = timeslice_df['mdvp'] ** ADV_POWER
        results_wls = sm.WLS(winsorize(timeslice_df['day_ret']), sm.add_constant(timeslice_df[indep]), weights=weights).fit()
        print(results_wls.summary())
        results_df = results_df.append(extract_results(results_wls, indep, it), ignore_index=True)
        
        it += 1

    return results_df

def regress_alpha_intra(intra_df, indep, horizon):    
    print("Regressing intra alphas for {} on horizon {}...".format(indep, horizon))
    assert horizon > 0
    results_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'], dtype=float)
    retname = 'cum_ret'+str(horizon)
    fitdata_df = intra_df[  ['log_ret', indep, 'mdvp', 'close', 'iclose'] ]
    fitdata_df[retname] = np.nan
    fitdata_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    it = 1
    for timeslice in ['10:30', '11:30', '12:30', '13:30', '14:30', '15:30' ]:
        print("Fitting for timeslice: {} at horizon {}".format(timeslice, horizon))

        timeslice_df = fitdata_df.unstack().between_time(timeslice, timeslice).stack()
        shift_df = timeslice_df.unstack().shift(-horizon).stack()
        timeslice_df[retname] = shift_df['log_ret'].groupby(level='sid').apply(lambda x: pd.rolling_sum(x, horizon))
#        intra_df.ix[ timeslice_df.index, retname ] = timeslice_df[retname]
        timeslice_df['day_ret'] = np.exp(np.log(timeslice_df['close'] / timeslice_df['iclose']) + timeslice_df[retname]) - 1
        timeslice_df = timeslice_df.dropna()

        weights = np.sqrt(timeslice_df['mdvp'])
        weights = timeslice_df['mdvp'] ** ADV_POWER
        ys = winsorize_by_ts(timeslice_df['day_ret'])
        results_wls = sm.WLS(ys, sm.add_constant(timeslice_df[indep]), weights=weights).fit()
        print(results_wls.summary())
        results_df = results_df.append(extract_results(results_wls, indep, it), ignore_index=True)
        it += 1

    return results_df
                                
def regress_alpha_dow(daily_df, indep, horizon):
    print("Regressing alphas day of week for {} with horizon {}...".format(indep, horizon))
    retname = 'cum_ret'+str(horizon) 
    fitdata_df = daily_df[ [retname, 'mdvp', indep, 'dow'] ]
    fitdata_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    fitdata_df = fitdata_df.dropna()
    results_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'], dtype=float)
    for name, daygroup in fitdata_df.groupby('dow'):        
        weights = np.sqrt(daygroup['mdvp'])
        weights = daygroup['mdvp'] ** ADV_POWER
        ys = winsorize_by_date(daygroup[retname])
        results_wls = sm.WLS(ys, sm.add_constant(daygroup[indep]), weights=weights).fit()
        print(results_wls.summary())
        results_df = results_df.append(extract_results(results_wls, indep, horizon * 10 + int(name)), ignore_index=True)

    return results_df


