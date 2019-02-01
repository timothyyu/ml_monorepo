#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

from pandas.stats.moments import ewma

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    print("Mkt return: {} {}".format(group['gdate'], ((d * w).sum() / w.sum())))
    res = b * ((d * w).sum() / w.sum())
    return res


def calc_tgt_daily(daily_df, horizon):
    print("Caculating daily tgt...")
    result_df = filter_expandable(daily_df)

    print("Calculating tgt0...")    
    halflife = horizon / 2
#    result_df['dk'] = np.exp( -1.0 * halflife *  (result_df['gdate'] - result_df['last']).astype('timedelta64[D]').astype(int) )
    print(result_df.columns)
    result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['log_ret'] - result_df['bret']
    result_df['badj0_B'] = winsorize_by_date(result_df[ 'badjret' ])

    #result_df['median_diff'] = result_df['target_median'].unstack().diff().stack()
    #result_df.loc[ result_df['std_diff'] <= 0, 'target_diff_mean'] = 0
    result_df['tgt0'] = winsorize_by_date(np.log(result_df['target_median'] / result_df['close_y']))


    # result_df['median'] = -1.0 * (result_df['median'] - 3)
    # result_df['med_diff'] = result_df['median'].unstack().diff().stack()
    # result_df['med_diff_dk'] = pd.rolling_sum( result_df['dk'] * result_df['med_diff'], window=horizon )
    # result_df['tgt0'] = (np.sign(result_df['med_diff_dk']) * np.sign(result_df['cum_ret'])).clip(lower=0) * result_df['med_diff_dk']


    demean = lambda x: (x - x.mean())
    indgroups = result_df[['tgt0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['tgt0_ma'] = indgroups['tgt0']

#    result_df['tgt0_ma'] = result_df['tgt0_ma'] * (np.sign(result_df['tgt0_ma']) * np.sign(result_df['cum_ret']))

#    result_df['tgt0_ma'] = result_df['tgt0']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['tgt'+str(lag)+'_ma'] = shift_df['tgt0_ma']

    return result_df

def tgt_fits(daily_df, horizon, name, middate=None, intercepts=None):
    insample_daily_df = daily_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_daily_df = daily_df[ daily_df.index.get_level_values('date') >= middate ]

    outsample_daily_df['tgt'] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr', 'intercept'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'tgt0_ma', ii, True, 'daily', True) 
#        fitresults_df['intercept'] = fitresults_df['intercept'] - intercepts[ii]
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 

    plot_fit(fits_df, "tgt_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['tgt0_ma'].ix[horizon].ix['coef']
#    intercept0 = fits_df.ix['tgt0_ma'].ix[horizon].ix['intercept']
    print("Coef{}: {}".format(0, coef0))
    outsample_daily_df[ 'tgt0_ma_coef' ] = coef0
    outsample_daily_df[ 'tgt0_ma_intercept' ] = 0 # intercept0
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['tgt0_ma'].ix[lag].ix['coef'] 
#        intercept = intercept0 - fits_df.ix['tgt0_ma'].ix[lag].ix['intercept'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_daily_df[ 'tgt'+str(lag)+'_ma_coef' ] = coef
 #       outsample_daily_df[ 'tgt'+str(lag)+'_ma_intercept' ] = intercept

    outsample_daily_df[ 'tgt' ] = outsample_daily_df['tgt0_ma'] * outsample_daily_df['tgt0_ma_coef'] #+ outsample_daily_df['tgt0_ma_intercept']
    for lag in range(1,horizon):
        outsample_daily_df[ 'tgt'] += outsample_daily_df['tgt'+str(lag)+'_ma'] * outsample_daily_df['tgt'+str(lag)+'_ma_coef'] #+ outsample_daily_df['tgt'+str(lag)+'_ma_intercept']
    
    return outsample_daily_df


def calc_tgt_forecast(daily_df, horizon, middate):
    daily_results_df = calc_tgt_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

    #results = list()
    # for sector_name in daily_results_df['sector_name'].dropna().unique():
    #     print "Running tgt for sector {}".format(sector_name)
    #     sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #     result_df = tgt_fits(sector_df, horizon, sector_name, middate)
    #     results.append(result_df)
    # result_df = pd.concat(results, verify_integrity=True)

  #  result_df = tgt_fits(daily_results_df, horizon, "", middate)

#    daily_results_df = daily_results_df[ daily_results_df['det_diff'] > 0]

    # results = list()
    # sector_name = 'Energy'
    # print "Running tgt for sector {}".format(sector_name)
    # sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    # res1 = tgt_fits( sector_df[ sector_df['det_diff'] > 0 ], horizon, "energy_up", middate)
    # res2 = tgt_fits( sector_df[ sector_df['det_diff'] < 0 ], horizon, "energy_dn", middate)
    # results.append(res1)
    # results.append(res2)

    # print "Running tgt for not sector {}".format(sector_name)
    # sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    # res1 = tgt_fits( sector_df[ sector_df['det_diff'] > 0 ], horizon, "rest_up", middate)
    # res2 = tgt_fits( sector_df[ sector_df['det_diff'] < 0 ], horizon, "rest_dn", middate)
    # results.append(res1)
    # results.append(res2)

    # result_df = pd.concat(results, verify_integrity=True)
#    intercept_d = get_intercept(daily_results_df, horizon, 'tgt0_ma', middate)
    res1 = tgt_fits( daily_results_df, horizon, "", middate)
#    res2 = tgt_fits( daily_results_df[ daily_results_df['det_diff'] < 0 ], horizon, "dn", middate, intercept_d)
    result_df = pd.concat([res1], verify_integrity=True)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--lag",action="store",dest="lag",default=15)
#    parser.add_argument("--horizon",action="store",dest="horizon",default=20)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.lag)
    pname = "./tgt" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    lag = int(args.lag)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        loaded = True
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1', 'pbeta']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)

        daily_df = merge_barra_data(price_df, barra_df)
        analyst_df = load_target_hist(price_df[['ticker']], start, end, False)
        daily_df = merge_daily_calcs(analyst_df, daily_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')

    result_df = calc_tgt_forecast(daily_df, horizon, middate)
    dump_daily_alpha(result_df, 'tgt')









