#!/usr/bin/env python 

from __future__ import print_function
from util import *
from regress import *
from loaddata import *
from calc import *
import opt
import gc

from collections import defaultdict

import argparse

def pnl_sum(group):
    cum_pnl = ((np.exp(group['cum_log_ret_i_now' ] - group['cum_log_ret_i_then']) - 1) * group['position_then']).fillna(0).sum()
    return cum_pnl

parser = argparse.ArgumentParser(description='G')
parser.add_argument("--start",action="store",dest="start",default=None)
parser.add_argument("--end",action="store",dest="end",default=None)
parser.add_argument("--fcast",action="store",dest="fcast",default=None)
parser.add_argument("--horizon",action="store",dest="horizon",default=3)
parser.add_argument("--mult",action="store",dest="mult",default=1.0)
parser.add_argument("--vwap",action="store",dest="vwap",default=False)
parser.add_argument("--maxiter",action="store",dest="maxiter",default=1500)
parser.add_argument("--kappa",action="store",dest="kappa",default=2.0e-8)
parser.add_argument("--slipnu",action="store",dest="slip_nu",default=.18)
parser.add_argument("--slipbeta",action="store",dest="slip_beta",default=.6)
parser.add_argument("--fast",action="store",dest="fast",default=False)
parser.add_argument("--exclude",action="store",dest="exclude",default=None)
parser.add_argument("--earnings",action="store",dest="earnings",default=None)
parser.add_argument("--locates",action="store",dest="locates",default=True)
parser.add_argument("--maxnot",action="store",dest="maxnot",default=200e6)
parser.add_argument("--maxdollars",action="store",dest="maxdollars",default=1e6)
parser.add_argument("--maxforecast",action="store",dest="maxforecast",default=0.0050)
parser.add_argument("--nonegutil",action="store",dest="nonegutil",default=True)
args = parser.parse_args()

print(args)

mkdir_p("opt")

ALPHA_MULT = float(args.mult)
horizon = int(args.horizon)
start = args.start
end = args.end

factors = ALL_FACTORS
max_forecast = float(args.maxforecast)
max_adv = 0.02
max_dollars = float(args.maxdollars)
participation = 0.015
opt.min_iter = 50
opt.max_iter = int(args.maxiter)
opt.kappa = float(args.kappa) # 4.3e-7
opt.max_sumnot = float(args.maxnot) 
opt.max_expnot = 0.04
opt.max_trdnot = 0.5
opt.slip_alpha = 1.0
opt.slip_delta = 0.25
opt.slip_beta = float(args.slip_beta) # 0.6
opt.slip_gamma = 0 # 0.3 
opt.slip_nu = float(args.slip_nu) # 0.14
opt.execFee= 0.00015
opt.num_factors = len(factors)

cols = ['ticker', 'iclose', 'tradable_volume', 'close', 'bvwap_b', 'tradable_med_volume_21_y', 'mdvp_y', 'overnight_log_ret', 'date', 'log_ret', 'bvolume', 'capitalization', 'cum_log_ret', 'srisk_pct', 'dpvolume_med_21', 'volat_21_y', 'mkt_cap_y', 'cum_log_ret_y', 'open', 'close_y', 'indname1', 'barraResidRet', 'split', 'div'] 
cols.extend( BARRA_FACTORS ) 
#cols.extend( BARRA_INDS )
cols.extend( INDUSTRIES )

forecasts = list()
forecastargs = args.fcast.split(',')
for fcast in forecastargs:
    fdir, name, mult, weight = fcast.split(":")
    forecasts.append(name)

factor_df = load_factor_cache(dateparser.parse(start), dateparser.parse(end))
pnl_df = load_cache(dateparser.parse(start), dateparser.parse(end), cols)

#print pnl_df.xs(10027954, level=1)['indname1']
pnl_df = pnl_df.truncate(before=dateparser.parse(start), after=dateparser.parse(end))
pnl_df.index.names = ['iclose_ts', 'sid']
pnl_df['forecast'] = np.nan
pnl_df['forecast_abs'] = np.nan
for fcast in forecastargs:
    print("Loading {}".format(fcast))
    fdir, name, mult, weight = fcast.split(":")
    mu_df = load_mus(fdir, name, start, end)
    pnl_df = pd.merge(pnl_df, mu_df, how='left', left_index=True, right_index=True)

#daily_df = pnl_df.unstack().between_time('15:30', '15:30').stack()
daily_df = pnl_df.unstack().between_time('15:45', '15:45').stack()
daily_df = daily_df.dropna(subset=['date'])
daily_df = daily_df.reset_index().set_index(['date', 'sid'])

pca_df = pd.read_csv("/q/work/sean/forecasts_final/pcadata/eig.txt", sep=" ", names=['date', 'eig']).drop_duplicates(take_last=True)
pca_df['date'] = pd.to_datetime(pca_df['date'])
pca_df = pca_df.set_index('date')

if args.locates is not None:
    locates_df = load_locates(daily_df[['ticker']], dateparser.parse(start), dateparser.parse(end))
    daily_df = pd.merge(daily_df, locates_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)         
    locates_df = None

if args.earnings is not None:
    earnings_df = load_earnings_dates(daily_df[['ticker']], dateparser.parse(start), dateparser.parse(end))
    daily_df = pd.merge(daily_df, earnings_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)         
    earnings_df = load_past_earnings_dates(daily_df[['ticker']], dateparser.parse(start), dateparser.parse(end))
    daily_df = pd.merge(daily_df, earnings_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)         
    earnings_df = None

#daily_df = transform_barra(daily_df)
pnl_df = pd.merge(pnl_df.reset_index(), daily_df.reset_index(), how='left', left_on=['date', 'sid'], right_on=['date', 'sid'], suffixes=['', '_dead'])
pnl_df = remove_dup_cols(pnl_df)                     
pnl_df.set_index(['iclose_ts', 'sid'], inplace=True)

#    resid_df, factor_df = calc_factors(daily_df)
daily_df['residVol'] = horizon * (calc_resid_vol(pnl_df) / 100.0) / np.sqrt(252.0)
factor_df = calc_factor_vol(factor_df)
pnl_df = pd.merge(pnl_df.reset_index(), daily_df.reset_index(), how='left', left_on=['date', 'sid'], right_on=['date', 'sid'], suffixes=['', '_dead'])
pnl_df = remove_dup_cols(pnl_df)         
pnl_df.set_index(['iclose_ts', 'sid'], inplace=True)

pnl_df['residVol'] = horizon * (pnl_df['srisk_pct'] / 100.0) / np.sqrt(252.0)

pnl_df['bvolume_d'] = pnl_df['bvolume'].groupby(level='sid').diff()
pnl_df.loc[ pnl_df['bvolume_d'] < 0, 'bvolume_d'] = pnl_df['bvolume']
pnl_df = push_data(pnl_df, 'bvolume_d')
pnl_df = push_data(pnl_df, 'bvwap_b')

#MIX FORECASTS
pnl_df[ 'forecast' ] = 0
for fcast in forecastargs:
    fdir, name, mult, weight = fcast.split(":")
    pnl_df[ name + '_adj' ] = pnl_df[ name ] * float(weight) * float(mult)
    pnl_df[ 'forecast' ] += pnl_df[name + '_adj'].fillna(0)

pnl_df['forecast'] = (ALPHA_MULT * pnl_df['forecast']).clip(-max_forecast, max_forecast)
pnl_df['forecast_abs'] = np.abs(pnl_df['forecast'])
pnl_df['max_trade_shares'] = pnl_df[ 'bvolume_d_n' ] * participation

pnl_df['position'] = 0
pnl_df['traded'] = 0
pnl_df['target'] = 0
pnl_df['dutil'] = 0
pnl_df['dsrisk'] = 0
pnl_df['dfrisk'] = 0
pnl_df['dmu'] = 0
pnl_df['eslip'] = 0
pnl_df['cum_pnl'] = 0

pnl_df['max_notional'] = (pnl_df['tradable_med_volume_21_y'] * pnl_df['close_y'] * max_adv).clip(0, max_dollars)
pnl_df['min_notional'] = (-1 * pnl_df['tradable_med_volume_21_y'] * pnl_df['close_y'] * max_adv).clip(-max_dollars, 0)

if args.locates is not None:
    pnl_df['borrow_notional'] = pnl_df['borrow_qty'] * pnl_df['iclose']
    pnl_df['min_notional'] = pnl_df[ ['borrow_notional', 'min_notional'] ].max(axis=1)
    
last_pos = pd.DataFrame(pnl_df.reset_index()['sid'].unique(), columns=['sid'])
last_pos['shares_last'] = 0
last_pos.set_index(['sid'], inplace=True)
last_pos = last_pos.sort()

lastday = None

it = 0
groups = pnl_df.groupby(level='iclose_ts')

pnl_df = None
daily_df = None
new_pnl_df = None
gc.collect()

for name, date_group in groups:
    dayname = name.strftime("%Y%m%d")
    if (int(dayname) < int(start)) or (int(dayname) > int(end)): continue

    # if args.fast:
    #     minutes = int(name.strftime("%M"))
    #     if minutes != 30: continue

    hour = int(name.strftime("%H"))
    if hour >= 16: continue

    print("Looking at {}".format(name))
    monthname = name.strftime("%Y%m")
    timename = name.strftime("%H%M%S")
    weekdayname = name.weekday()

    print(pca_df.ix[ dateparser.parse(dayname), 'eig' ])
    eig = 1
    try:
        eig = float(pca_df.ix[ dateparser.parse(dayname), 'eig' ][0])
    except:
        try:
            eig = float(pca_df.ix[ dateparser.parse(dayname), 'eig' ])
        except:
            pass
    
    date_group['forecast'] = date_group['forecast'] / eig

    date_group = date_group[ (date_group['iclose'] > 0) & (date_group['bvolume_d'] > 0) & (date_group['mdvp_y'] > 0) ].sort()
    if len(date_group) == 0:
        print("No data for {}".format(name))
        continue

    date_group = pd.merge(date_group.reset_index(), last_pos.reset_index(), how='outer', left_on=['sid'], right_on=['sid'], suffixes=['', '_last'])
    date_group['iclose_ts'] = name
    date_group = date_group.dropna(subset=['sid'])
    date_group.set_index(['iclose_ts', 'sid'], inplace=True)
    if lastday is not None and lastday != dayname:
        date_group['shares_last'] = date_group['shares_last'] * date_group['split']
    date_group['position_last'] = (date_group['shares_last'] * date_group['iclose']).fillna(0)
    date_group.ix[ date_group['iclose'].isnull() | date_group['mdvp_y'].isnull() | (date_group['mdvp_y'] == 0) | date_group['bvolume_d'].isnull() | (date_group['bvolume_d'] == 0) | date_group['residVol'].isnull(), 'max_notional' ] = 0
    date_group.ix[ date_group['iclose'].isnull() | date_group['mdvp_y'].isnull() | (date_group['mdvp_y'] == 0) | date_group['bvolume_d'].isnull() | (date_group['bvolume_d'] == 0) | date_group['residVol'].isnull(), 'min_notional' ] = 0

    # if args.exclude is not None:
    #     attr, val = args.exclude.split(":")
    #     val = float(val)
    #     date_group.ix[ date_group[attr] < val, 'forecast' ] = 0
    #     date_group.ix[ date_group[attr] < val, 'max_notional' ] = 0
    #     date_group.ix[ date_group[attr] < val, 'min_notional' ] = 0

    date_group.ix[ (date_group['mkt_cap_y'] < 1.6e9) | (date_group['iclose'] > 500.0) | (date_group['indname1'] == "PHARMA") , 'forecast' ] = 0
    date_group.ix[ (date_group['mkt_cap_y'] < 1.6e9) | (date_group['iclose'] > 500.0) | (date_group['indname1'] == "PHARMA"), 'max_notional' ] = 0
    date_group.ix[ (date_group['mkt_cap_y'] < 1.6e9) | (date_group['iclose'] > 500.0) | (date_group['indname1'] == "PHARMA"), 'min_notional' ] = 0


    if args.earnings is not None:
        days = int(args.earnings)
        date_group[ date_group['daysToEarn'] == 3 ]['residVol'] = date_group['residVol'] * 2
        date_group[ date_group['daysToEarn'] == 2 ]['residVol'] = date_group['residVol'] * 3
        date_group[ date_group['daysToEarn'] == 1 ]['residVol'] = date_group['residVol'] * 4
        
        date_group[ ( (date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (date_group['position_last'] >= 0)]['max_notional'] = date_group['position_last']
        date_group[ ( (date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (date_group['position_last'] >= 0)]['min_notional'] = 0
        date_group[ ( (date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (date_group['position_last'] <= 0)]['max_notional'] = 0
        date_group[ ( (date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (date_group['position_last'] <= 0)]['min_notional'] = date_group['position_last']

    #OPTIMIZATION
    opt.num_secs = len(date_group)
    opt.init()
    opt.sec_ind = date_group.reset_index().index.copy().values
    opt.sec_ind_rev = date_group.reset_index()['sid'].copy().values
    opt.g_positions = date_group['position_last'].copy().values
    opt.g_lbound = date_group['min_notional'].fillna(0).values
    opt.g_ubound = date_group['max_notional'].fillna(0).values
    opt.g_mu = date_group['forecast'].copy().fillna(0).values
    opt.g_rvar = date_group['residVol'].copy().fillna(0).values
    opt.g_advp = date_group[ 'mdvp_y'].copy().fillna(0).values
    opt.g_price = date_group['iclose'].copy().fillna(0).values
    opt.g_advpt = (date_group['bvolume_d'] * date_group['iclose']).fillna(0).values
    opt.g_vol = date_group['volat_21_y'].copy().fillna(0).values * horizon
    opt.g_mktcap = date_group['mkt_cap_y'].copy().fillna(0).values

    find = 0 
    for factor in factors:
        opt.g_factors[ find, opt.sec_ind ] = date_group[factor].fillna(0).values
        find += 1

    find1 = 0
    for factor1 in factors:
        find2 = 0
        for factor2 in factors:
            try:
                factor_cov = factor_df[(factor1, factor2)].fillna(0).ix[pd.to_datetime(dayname)]
                #                factor1_sig = np.sqrt(factor_df[(factor1, factor1)].fillna(0).ix[pd.to_datetime(dayname)])
                #               factor2_sig = np.sqrt(factor_df[(factor2, factor2)].fillna(0).ix[pd.to_datetime(dayname)])
                #                print "Factor Correlation {}, {}: {}".format(factor1, factor2, factor_cov/(factor1_sig*factor2_sig))
            except:
                #                print "No cov found for {} {}".format(factor1, factor2)
                factor_cov = 0

            opt.g_fcov[ find1, find2 ] = factor_cov * horizon
            opt.g_fcov[ find2, find1 ] = factor_cov * horizon

            find2 += 1
        find1 += 1
        
    try:
        (target, dutil, eslip, dmu, dsrisk, dfrisk, costs, dutil2) = opt.optimize()
    except:
        date_group.to_csv("problem.csv")
        raise

    optresults_df = pd.DataFrame(index=date_group.index, columns=['target', 'dutil', 'eslip', 'dmu', 'dsrisk', 'dfrisk', 'costs', 'dutil2', 'traded'])
    optresults_df['target'] = target
    optresults_df['dutil'] = dutil
    optresults_df['eslip'] = eslip
    optresults_df['dmu'] = dmu
    optresults_df['dsrisk'] = dsrisk
    optresults_df['dfrisk'] = dfrisk
    optresults_df['costs'] = costs
    optresults_df['dutil2'] = dutil2
    
    # pnl_df.ix[ date_group.index, 'target'] = optresults_df['target']
    # pnl_df.ix[ date_group.index, 'eslip'] = optresults_df['eslip']
    # pnl_df.ix[ date_group.index, 'dutil'] = optresults_df['dutil']
    # pnl_df.ix[ date_group.index, 'dsrisk'] = optresults_df['dsrisk']
    # pnl_df.ix[ date_group.index, 'dfrisk'] = optresults_df['dfrisk']
    # pnl_df.ix[ date_group.index, 'dmu'] = optresults_df['dmu']

    date_group['target'] = optresults_df['target']
    date_group['dutil'] = optresults_df['dutil']
    #    tmp = pd.merge(last_pos.reset_index(), date_group['forecast'].reset_index(), how='inner', left_on=['sid'], right_on=['sid'])
    #    date_group['last_position'] = tmp.set_index(['iclose_ts', 'sid'])['position']

    if args.nonegutil:
        date_group.ix[ date_group['dutil'] <= 0, 'target'] = date_group['position_last']

    date_group['max_move'] = date_group['position_last'] + date_group['max_trade_shares'] * date_group['iclose'] 
    date_group['min_move'] = date_group['position_last'] - date_group['max_trade_shares'] * date_group['iclose'] 
    date_group['position'] = date_group['target']
    date_group['position'] = date_group[ ['position', 'max_move'] ].min(axis=1)
    date_group['position'] = date_group[ ['position', 'min_move'] ].max(axis=1)
    
    # df = date_group[ date_group['target'] > date_group['max_move']]
    # print df[['max_move', 'min_move', 'target', 'position', 'max_trade_shares', 'position_last', 'bvolume_d_n']].head()
    # print date_group.xs(10000108, level=1)[['max_move', 'min_move', 'target', 'position', 'max_trade_shares', 'position_last', 'bvolume_d_n']]
    
    date_group['traded'] = date_group['position'] - date_group['position_last']
    date_group['shares'] = date_group['position'] / date_group['iclose']
    #    pnl_df.ix[ date_group.index, 'traded'] = date_group['traded']

    postmp = pd.merge(last_pos.reset_index(), date_group['shares'].reset_index(), how='outer', left_on=['sid'], right_on=['sid']).set_index('sid')
    last_pos['shares_last'] = postmp['shares'].fillna(0)
    postmp = None
#    pnl_df.ix[ date_group.index, 'position'] = date_group['position']

    optresults_df['forecast'] = date_group['forecast']
    optresults_df['traded'] = date_group['traded']
    optresults_df['shares'] = date_group['shares']
    optresults_df['position'] = date_group['position']
    optresults_df['iclose'] = date_group['iclose']
    optresults_df = optresults_df.reset_index()
    optresults_df['sid'] = optresults_df['sid'].astype(int)
    optresults_df.set_index(['iclose_ts', 'sid'], inplace=True)
    optresults_df.to_csv("./opt/opt." + "-".join(forecasts) + "." + dayname + "_" + timename + ".csv")

    lastday = dayname
    it += 1
#    groups.remove(name)
    date_group = None
    gc.collect()
    
email("bsim done: " + args.fcast, "")

#pnl_df.to_csv("debug." + "-".join(forecasts) + "." + str(start) + "." + str(end) + ".csv")
#pnl_df.xs(testid, level=1).to_csv("debug.csv")
    
