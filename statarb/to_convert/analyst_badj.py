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

def calc_rtg_daily(daily_df, horizon):
    print("Caculating daily rtg...")
    result_df = filter_expandable(daily_df)

    print("Calculating rtg0...")    
#    result_df['cum_ret'] = pd.rolling_sum(result_df['log_ret'], 6)
#    result_df['med_diff'] = result_df['median'].unstack().diff().stack()
#    result_df['rtg0'] = -1.0 * (result_df['median'] - 3) / ( 1.0 + result_df['std'] )

    result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['rtg0_B'] = winsorize_by_date(result_df['log_ret'] / result_df['pbeta'])

    result_df['rating'] = -1 * result_df['rating_diff_mean'].fillna(0)
    result_df['ret_rating'] = result_df['rtg0_B'] * result_df['rating']
#    result_df['rtg0'] = -1.0 * result_df['med_diff_dk'] * result_df['cum_ret']

    # result_df['rtg0'] = -1.0 * result_df['med_diff_dk']
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['rtg0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['rtg0_B_ma'] = indgroups['rtg0_B']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['rtg'+str(lag)+'_B_ma'] = shift_df['rtg0_B_ma']

    return result_df

def calc_rtg_intra(intra_df):
    print("Calculating rtg intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating rtgC...")
    result_df['rtgC'] = (result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))) / result_df['pbeta']
    result_df['rtgC_B'] = winsorize_by_ts(result_df[ 'rtgC' ])

    print("Calulating rtgC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['rtgC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=True).transform(demean)
    result_df['rtgC_B_ma'] = indgroups['rtgC_B']
    
    print("Calculated {} values".format(len(result_df['rtgC_B_ma'].dropna())))
    return result_df

def rtg_fits(daily_df, intra_df, horizon, name, middate=None, intercepts=None):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
#        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_daily_df = daily_df[ daily_df.index.get_level_values('date') >= middate ]
#        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_daily_df['rtg'] = np.nan
    outsample_daily_df[ 'rtg0_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_daily_df[ 'rtg' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'rtg0_B_ma', lag, True, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "rtg_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    coef0 = fits_df.ix['rtg0_B_ma'].ix[horizon].ix['coef']
    outsample_daily_df[ 'rtg0_B_ma_coef' ] = coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['rtg0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_daily_df[ 'rtg'+str(lag)+'_B_ma_coef' ] = coef

    outsample_daily_df['rtg'] = outsample_daily_df['rtg0_B_ma'] * outsample_daily_df['rtg0_B_ma_coef']
    for lag in range(1,horizon):
        outsample_daily_df[ 'rtg'] += outsample_daily_df['rtg'+str(lag)+'_B_ma'] * outsample_daily_df['rtg'+str(lag)+'_B_ma_coef']

    return outsample_daily_df


def calc_rtg_forecast(daily_df, horizon, middate):
    daily_results_df = calc_rtg_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

    # results = list()
    # for sector_name in daily_results_df['sector_name'].dropna().unique():
    #     if sector_name == "Utilities" or sector_name == "HealthCare": continue
    #     print "Running rtg for sector {}".format(sector_name)
    #     sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #     result_df = rtg_fits(sector_df, horizon, sector_name, middate)
    #     results.append(result_df)
    # result_df = pd.concat(results, verify_integrity=True)

    # result_df = rtg_fits(daily_results_df, horizon, "", middate)
    intercept_d = get_intercept(daily_results_df, horizon, 'rtg0_B_ma', middate)
    sector_name = 'Energy'
    print("Running qhl for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
 #   sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    # res1 = rtg_fits( sector_df[ sector_df['ret_rating'] > 0 ], horizon, "en_up", middate)
#    res2 = rtg_fits( sector_df[ sector_df['ret_rating'] == 0 ], None, horizon, "en_eq", middate, intercept_d)
    # res3 = rtg_fits( sector_df[ sector_df['ret_rating'] < 0 ], horizon, "en_dn", middate)

    
    print("Running qhl for not sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
#    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]    
#    res4 = rtg_fits( sector_df[ sector_df['ret_rating'] > 0 ], horizon, "ot_up", middate)
    res5 = rtg_fits( sector_df[ sector_df['ret_rating'] == 0 ], None, horizon, "ot_eq", middate, intercept_d)
#    res6 = rtg_fits( sector_df[ sector_df['ret_rating'] < 0 ], horizon, "ot_dn", middate)

#    result_df = pd.concat([res1, res2, res3, res4, res5, res6], verify_integrity=True).sort()
    result_df = pd.concat([res5], verify_integrity=True).sort()
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--lag",action="store",dest="lag",default=4)
#    parser.add_argument("--horizon",action="store",dest="horizon",default=20)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.lag)
    pname = "./rtg" + start + "." + end
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
        analyst_df = load_ratings_hist(price_df[['ticker']], start, end, False, True)
        daily_df = merge_daily_calcs(daily_df, analyst_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')

    result_df = calc_rtg_forecast(daily_df, horizon, middate)

    print("Total Alpha Summary")
    print(result_df['rtg'].describe())

    dump_daily_alpha(result_df, 'rtg')









