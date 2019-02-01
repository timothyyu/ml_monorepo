#!/usr/bin/env python

from __future__ import print_function
import numpy as np
import pandas as pd
import gc

from scipy import stats
from pandas.stats.api import ols
from pandas.stats import moments
from lmfit import minimize, Parameters, Parameter, report_errors
from collections import defaultdict

from util import *


INDUSTRIES = ['CONTAINR', 'HLTHSVCS', 'SPLTYRET', 'SPTYSTOR', 'DIVFIN', 'GASUTIL', 'BIOLIFE', 'SPTYCHEM', 'ALUMSTEL', 'AERODEF', 'COMMEQP', 'HOUSEDUR', 'CHEM', 'LEISPROD', 'AUTO', 'CONGLOM', 'HOMEBLDG', 'CNSTENG', 'LEISSVCS', 'OILGSCON', 'MEDIA', 'FOODPROD', 'PSNLPROD', 'OILGSDRL', 'SOFTWARE', 'BANKS', 'RESTAUR', 'FOODRET', 'ROADRAIL', 'APPAREL', 'INTERNET', 'NETRET', 'PAPER', 'WIRELESS', 'PHARMA', 'MGDHLTH', 'CNSTMACH', 'OILGSEQP', 'REALEST', 'COMPELEC', 'BLDGPROD', 'TRADECO', 'MULTUTIL', 'CNSTMATL', 'HLTHEQP', 'PRECMTLS', 'INDMACH', 'TRANSPRT', 'SEMIEQP', 'TELECOM', 'OILGSEXP', 'INSURNCE', 'AIRLINES', 'SEMICOND', 'ELECEQP', 'ELECUTIL', 'LIFEINS', 'COMSVCS', 'DISTRIB']
BARRA_FACTORS = ['country', 'growth', 'size', 'sizenl', 'divyild', 'btop', 'earnyild', 'beta', 'resvol', 'betanl', 'momentum', 'leverage', 'liquidty']
PROP_FACTORS = ['srisk_pct_z', 'rating_mean_z']
ALL_FACTORS = BARRA_FACTORS + INDUSTRIES + PROP_FACTORS

def calc_vol_profiles(full_df):
    full_df['dpvolume_med_21'] = np.nan
    full_df['dpvolume_std_21'] = np.nan
    full_df['dpvolume'] = full_df['dvolume'] * full_df['dvwap']
    print("Calculating trailing volume profile...")
    for timeslice in ['09:45', '10:00', '10:15', '10:30', '10:45', '11:00', '11:15', '11:30', '11:45', '12:00', '12:15', '12:30', '12:45', '13:00', '13:15', '13:30', '13:45', '14:00', '14:15', '14:30', '14:45', '15:00', '15:15', '15:30', '15:45', '16:00' ]:
        timeslice_df = full_df[ ['dpvolume', 'tradable_med_volume_21', 'close'] ]
        timeslice_df = timeslice_df.unstack().between_time(timeslice, timeslice).stack()
        timeslice_df = timeslice_df.dropna()
        if len(timeslice_df) == 0: continue
        timeslice_df['dpvolume_med_21'] = timeslice_df['dpvolume'].groupby(level='sid').apply(lambda x: pd.rolling_median(x.shift(1), 21))
        timeslice_df['dpvolume_std_21'] = timeslice_df['dpvolume'].groupby(level='sid').apply(lambda x: pd.rolling_std(x.shift(1), 21))
        m_df = timeslice_df.dropna()
        print(m_df.head())
        print("Average dvol frac at {}: {}".format(timeslice, (m_df['dpvolume_med_21'] / (m_df['tradable_med_volume_21'] * m_df['close'])).mean()))
        full_df.ix[ timeslice_df.index, 'dpvolume_med_21'] = timeslice_df['dpvolume_med_21']
        full_df.ix[ timeslice_df.index, 'dpvolume_std_21'] = timeslice_df['dpvolume_std_21']

    return full_df

def calc_price_extras(daily_df):    
    daily_df['volat_ratio'] = daily_df['volat_21'] / daily_df['volat_60']
    daily_df['volume_ratio'] = daily_df['tradable_volume'] / daily_df['shares_out']
    daily_df['volume_ratio'] = daily_df['tradable_volume'] / daily_df['comp_volume']
    daily_df['volat_move'] = daily_df['volat_21'].diff()
    return daily_df

def calc_forward_returns(daily_df, horizon):
    print("Calculating forward returns...")
    results_df = pd.DataFrame( index=daily_df.index )
    for ii in range(1, horizon+1):
        retname = 'cum_ret'+str(ii) 
        cum_rets = daily_df['log_ret'].groupby(level='sid').apply(lambda x: pd.rolling_sum(x, ii))
        shift_df = cum_rets.unstack().shift(-ii).stack()
        results_df[retname] = shift_df
    return results_df

def winsorize(data, std_level=5):
    result = data.copy()
    std = result.std() * std_level
    mean = result.mean()
    result[result > mean + std] = mean + std
    result[result < mean - std] = mean - std
    return result

def winsorize_by_date(data):
    print("Winsorizing by day...")
    return data.groupby(level='date', sort=False).transform(winsorize)

def winsorize_by_ts(data):
    print("Winsorizing by day...")
    return data.groupby(level='iclose_ts', sort=False).transform(winsorize)

def winsorize_by_group(data, group):
    print("Winsorizing by day...")
    return data.groupby([group], sort=False).transform(winsorize)

def rolling_ew_corr_pairwise(df, halflife):
    all_results = {}
    for col, left in df.iteritems():
        all_results[col] = col_results = {}
        for col, right in df.iteritems():
            col_results[col] = moments.ewmcorr(left, right, span=(halflife-1)/2.0)

    ret = pd.Panel(all_results)
    ret = ret.swapaxes(0,1, copy=False)
    return ret

def push_data(df, col):
    #Careful, can push to next day...
    lagged_df = df[[col]].unstack(level='sid').shift(-1).stack()
    merged_df = pd.merge(df, lagged_df, left_index=True, right_index=True, sort=True, suffixes=['', '_n'])
    return merged_df

def lag_data(daily_df):
    lagged_df = daily_df.unstack(level=-1).shift(1).stack()
    merged_df = pd.merge(daily_df, lagged_df, left_index=True, right_index=True, sort=True, suffixes=['', '_y'])
    return merged_df

def calc_med_price_corr(daily_df):
    pass

def calc_resid_vol(daily_df):
    lookback = 20
    daily_df['barraResidVol'] = np.sqrt(pd.rolling_var(daily_df['barraResidRet'], lookback))
    return daily_df['barraResidVol']

def calc_factor_vol(factor_df):
    halflife = 20.0
    #    factors = factor_df.index.get_level_values('factor').unique()
    factors = ALL_FACTORS
    ret = dict()
    for factor1 in factors:
        for factor2 in factors:
            key = (factor1, factor2)
            if key not in ret.keys():                
                ret[key] = moments.ewmcov(factor_df.xs(factor1, level=1)['ret'], factor_df.xs(factor2, level=1)['ret'], span=(halflife-1)/2.0)
#                ret[key] = pd.rolling_cov(factor_df.xs(factor1, level=1)['ret'], factor_df.xs(factor2, level=1)['ret'], window=20)
#                print "Created factor Cov on {} from {} to {}".format(key, min(ret[key].index), max(ret[key].index))
    return ret

weights_df = None

def create_z_score(daily_df, name):
    zscore = lambda x: ( (x - x.mean()) / x.std())
    indgroups = daily_df[[name, 'gdate']].groupby(['gdate'], sort=True).transform(zscore)
    daily_df[name + "_z"] = indgroups[name]
    return daily_df
    
def calc_factors(daily_df, barraOnly=False):
    print("Calculating factors...")
    
    allreturns_df = pd.DataFrame(columns=['barraResidRet'], index=daily_df.index)
    if barraOnly:
        factors = BARRA_FACTORS + INDUSTRIES
    else:
        daily_df = create_z_score(daily_df, 'srisk_pct')
        daily_df = create_z_score(daily_df, 'rating_mean')
        factors = ALL_FACTORS

    print("Total len: {}".format(len(daily_df)))
    cnt = 0
    cnt1 = 0
    factorrets = list()
    for name, group in daily_df.groupby(level='date'):
        print("Regressing {}".format(name))
        cnt1 += len(group)
        print("Size: {} {}".format(len(group), cnt1))

        loadings_df = group[ factors ]
        loadings_df = loadings_df.reset_index().fillna(0)

        del loadings_df['sid']
        del loadings_df['date']

#        print "loadings len {}".format(len(loadings_df))
#        print loadings_df.head()

        returns_df = group['log_ret'].fillna(0)
 #       print "returns len {}".format(len(returns_df))

 #       print returns_df.head()
        global weights_df
        weights_df = np.log(group['capitalization']).fillna(0)
#        print weights_df.head()
        weights_df = pd.DataFrame( np.diag(weights_df) )

        #        print "weights len {}".format(len(weights_df))
        indwgt = dict()
        capsum = (group['capitalization'] / 1e6).sum()
        for ind in INDUSTRIES:
            indwgt[ind] = (group[ group['indname1'] == ind]['capitalization'] / 1e6).sum() / capsum
#        print returns_df.head()

        fRets, residRets = factorize(loadings_df, returns_df, weights_df, indwgt)        
        print("Factor Returns:")
#        print fRets
#        print residRets
        
        cnt += len(residRets)
        print("Running tally: {}".format(cnt))
        fdf = pd.DataFrame([ [i,v] for i, v in fRets.items() ], columns=['factor', 'ret'])
        fdf['date'] = name
        factorrets.append( fdf )
        allreturns_df.ix[ group.index, 'barraResidRet'] = residRets

        fRets = residRets = None
        gc.collect()

#    print allreturns_df.tail()
    factorRets_df = pd.concat(factorrets).set_index(['date', 'factor']).fillna(0)
    print("Final len {}".format(len(allreturns_df)))
    daily_df['barraResidRet'] = allreturns_df['barraResidRet']
    return daily_df, factorRets_df

def calc_intra_factors(intra_df, barraOnly=False):
    print("Calculating intra factors...")
    
    allreturns_df = pd.DataFrame(columns=['barraResidRetI'], index=intra_df.index)

    if barraOnly:
        factors = BARRA_FACTORS + INDUSTRIES
    else:
        factors = ALL_FACTORS
    
    print("Total len: {}".format(len(intra_df)))
    cnt = 0
    cnt1 = 0
    factorrets = list()
    for name, group in intra_df.groupby(level='iclose_ts'):
        print("Regressing {}".format(name))
        cnt1 += len(group)
        print("Size: {} {}".format(len(group), cnt1))

        loadings_df = group[ factors ]
        loadings_df = loadings_df.reset_index().fillna(0)

        del loadings_df['sid']
        del loadings_df['iclose_ts']

#        print "loadings len {}".format(len(loadings_df))
#        print loadings_df.head()

        returns_df = (group['overnight_log_ret'] + np.log(group['iclose'] / group['dopen'])).fillna(0)
 #       print "returns len {}".format(len(returns_df))

 #       print returns_df.head()
        global weights_df
        weights_df = np.log(group['capitalization']).fillna(0)
#        print weights_df.head()
        weights_df = pd.DataFrame( np.diag(weights_df) )
        #        print "weights len {}".format(len(weights_df))
        indwgt = dict()
        capsum = (group['capitalization'] / 1e6).sum()
        for ind in INDUSTRIES:
            indwgt[ind] = (group[ group['indname1'] == ind]['capitalization'] / 1e6).sum() / capsum
#        print returns_df.head()

        fRets, residRets = factorize(loadings_df, returns_df, weights_df, indwgt)        
        print("Factor Returns:")
        print(fRets)
#        print residRets
        
        cnt += len(residRets)
        print("Running tally: {}".format(cnt))
        fdf = pd.DataFrame([ [i,v] for i, v in fRets.items() ], columns=['factor', 'ret'])
        fdf['iclose_ts'] = name
        factorrets.append( fdf )
        allreturns_df.ix[ group.index, 'barraResidRetI'] = residRets

        fRets = residRets = None
        gc.collect()

#    print allreturns_df.tail()
    factorRets_df = pd.concat(factorrets).set_index(['iclose_ts', 'factor']).fillna(0)
    print("Final len {}".format(len(allreturns_df)))
    intra_df['barraResidRetI'] = allreturns_df['barraResidRetI']
    return intra_df, factorRets_df

def factorize(loadings_df, returns_df, weights_df, indwgt):
    print("Factorizing...")
    params = Parameters()
    for colname in loadings_df.columns:
        expr = None

        if colname == 'country':
            expr = "0"
            for ind in INDUSTRIES:
                expr += "+" + ind + "*" + str(indwgt[ind])
#                expr += "+" + ind
            print(expr)
        params.add(colname, value=0.0, expr=expr)

    print("Minimizing...")
    result = minimize(fcn2min, params, args=(loadings_df, returns_df))
    print("Result: ") 
    if not result.success:
        print("ERROR: failed fit")
        exit(1)

    fRets_d = dict()
    for param in params:
        val = params[param].value
        error = params[param].stderr

        fRets_d[param] = val

        upper = val + error * 2
        lower = val - error * 2
        if upper * lower < 0:
            print("{} not significant: {}, {}".format(param, val, error))

    print("SEAN")
    print(result)
    print(result.residual)
    print(result.message)
    print(result.lmdif_message)
    print(result.nfev)
    print(result.ndata)

    residRets_na = result.residual
    return fRets_d, residRets_na

def fcn2min(params, x, data):
    # f1 = params['BBETANL_b'].value    
    # f2 = params['SIZE_b'].value    
    # print "f1: " + str(type(f1))
    # print f1
    ps = list()
    for param in params:
        val = params[param].value 
        # if val is None: val = 0.0
        ps.append(val)
#        print "adding {} of {}".format(param, val)
    # print ps
    f = np.array(ps)
    f.shape = (len(params),1)
    # print "f: " + str(f.shape)
    # print f
    # print "x: " + str(type(x)) + str(x.shape)
    # print x
    model = np.dot(x, f) 
 #   print "model: " + str(type(model)) + " " + str(model.shape)
    # print model
#    print "data: " + str(type(data)) + " " + str(data.shape)
    # 
    # print data

    global weights_df
    cap_sq = weights_df.as_matrix()
#    cap_sq.shape = (cap_sq.shape[0], 1)

#    print model.shape
#    print data.values.shape
#    print cap_sq.shape    
    # print "SEAN2"
    # print model
    # print data.values
    # print cap_sq

    #ret = np.multiply((model - data.values), cap_sq) / cap_sq.mean()    
    ret = np.multiply((model - data.values), cap_sq)

    # print str(ret)
#    ret = model - data

    ret = ret.diagonal()
    # print ret.shape
#    ret = ret.as_matrix()
    ret.shape = (ret.shape[0], )

    #UGH XXX should really make sure types are correct at a higher level
    ret = ret.astype(np.float64, copy=False)

    # print
 #   print "ret: " + str(type(ret)) + " " + str(ret.shape)
    # print ret
    return ret

def mkt_ret(group):
    d = group['cum_ret1']
    w = group['mkt_cap'] / 1e6
    res = (d * w).sum() / w.sum()
    return res
