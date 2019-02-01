#!/usr/bin/env python 
from __future__ import print_function
import logging

from regress import *
from loaddata import *
from load_data_live import *
from util import *

from pandas.stats.moments import ewma

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    print("Mkt return: {} {}".format(group['gdate'], ((d * w).sum() / w.sum())))
    res = b * ((d * w).sum() / w.sum())
    return res

def calc_rtg_daily(daily_df, horizon):
    print("Caculating daily rtg...")
    result_df = filter_expandable(daily_df)

    print("Calculating rtg0...")
#    result_df['cum_ret'] = pd.rolling_sum(result_df['log_ret'], 6)
#    result_df['med_diff'] = result_df['median'].unstack().diff().stack()
#    result_df['rtg0'] = -1.0 * (result_df['median'] - 3) / ( 1.0 + result_df['std'] )
#    result_df['rtg0'] = -1 * result_df['mean'] * np.abs(result_df['mean'])
#    result_df['rtg0'] = -1.0 * result_df['med_diff_dk'] * result_df['cum_ret']

    result_df['std_diff'] = result_df['rating_std'].unstack().diff().stack()
    print(result_df['rating_diff_mean'].describe())
    result_df.loc[ (result_df['std_diff'] <= 0) | (result_df['std_diff'].isnull()), 'rating_diff_mean'] = 0
    print(result_df['rating_diff_mean'].describe())
    result_df['rtg0'] = result_df['rating_diff_mean'] * result_df['rating_diff_mean'] * np.sign(result_df['rating_diff_mean'])


    # result_df['rtg0'] = -1.0 * result_df['med_diff_dk']
    # demean = lambda x: (x - x.mean())
    # indgroups = result_df[['rtg0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    # result_df['rtg0_ma'] = indgroups['rtg0']
    result_df['rtg0_ma'] = result_df['rtg0']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['rtg'+str(lag)+'_ma'] = shift_df['rtg0_ma']

    return result_df

def generate_coefs(daily_df, horizon, fitfile=None):
    insample_daily_df = daily_df

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'rtg0_ma', ii, True, 'daily', False) 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['rtg0_ma'].ix[horizon].ix['coef']
    print("Coef{}: {}".format(0, coef0))

    coef_list = list()
    coef_list.append( { 'name': 'rtg0_ma_coef', 'coef': coef0 } )
    for lag in range(1,horizon):
        weight = (horizon - lag) / float(horizon)
        lagname = 'rtg'+str(lag)+'_ma'
        coef = coef0 * weight
        print("Running lag {} with weight: {}".format(lag, weight))
        coef_list.append( { 'name': 'rtg'+str(lag)+'_ma_coef', 'coef': coef } )

    coef_df = pd.DataFrame(coef_list)
    coef_df.to_csv(fitfile)

    return 1

def rtg_alpha(daily_df, horizon, coeffile=None):
    coef_df = pd.read_csv(coeffile, header=0, index_col=['name'])

    outsample_daily_df = daily_df
    outsample_daily_df['rtg'] = 0

    for lag in range(0,horizon):
        coef = coef_df.ix[ 'rtg'+str(lag)+'_ma_coef' ]['coef']
        print("Coef: {}".format(coef))
        outsample_daily_df[ 'rtg'+str(lag)+'_ma_coef' ] = coef
    print(outsample_daily_df['rtg'].describe())

    outsample_daily_df[ 'rtg' ] = (outsample_daily_df['rtg0_ma'] * outsample_daily_df['rtg0_ma_coef']).fillna(0) #+ outsample_daily_df['rtg0_ma_intercept']
    for lag in range(1,horizon):
        print(outsample_daily_df['rtg'].describe())
        outsample_daily_df[ 'rtg'] += (outsample_daily_df['rtg'+str(lag)+'_ma'] * outsample_daily_df['rtg'+str(lag)+'_ma_coef']).fillna(0) #+ outsample_daily_df['rtg'+str(lag)+'_ma_intercept']
    
    return outsample_daily_df
def calc_rtg_forecast(daily_df, horizon, coeffile, fit):
    daily_results_df = calc_rtg_daily(daily_df, horizon) 

    # results = list()
    # for sector_name in daily_results_df['sector_name'].dropna().unique():
    #     if sector_name == "Utilities" or sector_name == "HealthCare": continue
    #     print "Running rtg for sector {}".format(sector_name)
    #     sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #     result_df = rtg_fits(sector_df, horizon, sector_name, middate)
    #     results.append(result_df)
    # result_df = pd.concat(results, verify_integrity=True)


    # res1 = rtg_fits( daily_results_df[ daily_results_df['rating_diff_mean'] > 0 ], horizon, "up", middate)
    # res2 = rtg_fits( daily_results_df[ daily_results_df['rating_diff_mean'] < 0 ], horizon, "dn", middate)
    # result_df = pd.concat([res1, res2], verify_integrity=True)

    if fit:
        forwards_df = calc_forward_returns(daily_df, horizon)
        daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

        generate_coefs( daily_results_df, horizon, coeffile)
        return
    else:
        res1 = rtg_alpha( daily_results_df, horizon, coeffile)
        #    res2 = tgt_fits( daily_results_df[ daily_results_df['det_diff'] < 0 ], horizon, "dn", middate, intercept_d)
        result_df = pd.concat([res1], verify_integrity=True)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--asof",action="store",dest="asof",default=None)
    parser.add_argument("--inputfile",action="store",dest="inputfile",default=None)
    parser.add_argument("--outputfile",action="store",dest="outputfile",default=None)
    parser.add_argument("--logfile",action="store",dest="logfile",default=None)
    parser.add_argument("--coeffile",action="store",dest="coeffile",default=None)
    parser.add_argument("--fit",action="store",dest="fit",default=False)
    args = parser.parse_args()
    
    horizon = int(6)

    end = datetime.strptime(args.asof, "%Y%m%d")
    if args.fit:
        print("Fitting...")
        coeffile = args.coeffile + "/" + args.asof + ".rtg.csv"
        lookback = timedelta(days=720)    
        start = end - lookback
        uni_df = get_uni(start, end, 30)
    else:
        print("Not fitting...")
        coeffile = args.coeffile
        lookback = timedelta(days=horizon+5)    
        start = end - lookback
        uni_df = load_live_file(args.inputfile)
        end = datetime.strptime(args.asof + '_' + uni_df['time'].min(), '%Y%m%d_%H:%M:%S')
    
    print("Running between {} and {}".format(start, end))

    BARRA_COLS = ['ind1']
    barra_df = load_barra(uni_df, start, end, BARRA_COLS)

    PRICE_COLS = ['close']
    price_df = load_prices(uni_df, start, end, PRICE_COLS)

    daily_df = merge_barra_data(price_df, barra_df)
    analyst_df = load_ratings_hist(price_df[['ticker']], start, end)
    daily_df = merge_daily_calcs(analyst_df, daily_df)
    
    
    result_df = calc_rtg_forecast(daily_df, horizon, coeffile, args.fit)

    if not args.fit:
        print("Total Alpha Summary")
        print(result_df['rtg'].describe())
        dump_prod_alpha(result_df, 'rtg', args.outputfile)


