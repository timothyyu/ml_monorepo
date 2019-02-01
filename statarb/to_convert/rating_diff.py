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
#    result_df['rtg0'] = -1 * result_df['mean'] * np.abs(result_df['mean'])
#    result_df['rtg0'] = -1.0 * result_df['med_diff_dk'] * result_df['cum_ret']

    result_df['std_diff'] = result_df['rating_std'].unstack().diff().stack()
    print("SEAN")
    print(result_df['rating_diff_mean'].describe())
    result_df.loc[ (result_df['std_diff'] <= 0) | (result_df['std_diff'].isnull()), 'rating_diff_mean'] = 0
    print(result_df['rating_diff_mean'].describe())
    print("SEAN2")
    print(result_df.xs(10000708, level=1))
    result_df['rtg0'] = result_df['rating_diff_mean'] #* result_df['rating_diff_mean'] * np.sign(result_df['rating_diff_mean'])


    # result_df['rtg0'] = -1.0 * result_df['med_diff_dk']
    # demean = lambda x: (x - x.mean())
    # indgroups = result_df[['rtg0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    # result_df['rtg0_ma'] = indgroups['rtg0']
    result_df['rtg0_ma'] = result_df['rtg0']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['rtg'+str(lag)+'_ma'] = shift_df['rtg0_ma']

    return result_df

def rtg_fits(daily_df, horizon, name, middate=None):
    insample_daily_df = daily_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_daily_df = daily_df[ daily_df.index.get_level_values('date') >= middate ]

    outsample_daily_df['rtg'] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'rtg0_ma', ii, True, 'daily', False) 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "rtg_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['rtg0_ma'].ix[horizon].ix['coef']
    print("Coef{}: {}".format(0, coef0))
    outsample_daily_df[ 'rtg0_ma_coef' ] = coef0

    outsample_daily_df[ 'rtg' ] = outsample_daily_df['rtg0_ma'].fillna(0) * outsample_daily_df['rtg0_ma_coef']
    for lag in range(1,horizon):
        weight = (horizon - lag) / float(horizon)
        lagname = 'rtg'+str(lag)+'_ma'
        print("Running lag {} with weight: {}".format(lag, weight))
        outsample_daily_df[ 'rtg'] += outsample_daily_df[lagname].fillna(0) * outsample_daily_df['rtg0_ma_coef'] * weight

    print("Alpha Summary {}".format(name))
    print(outsample_daily_df['rtg'].describe())
    
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

    result_df = rtg_fits(daily_results_df, horizon, "", middate)

    # res1 = rtg_fits( daily_results_df[ daily_results_df['rating_diff_mean'] > 0 ], horizon, "up", middate)
    # res2 = rtg_fits( daily_results_df[ daily_results_df['rating_diff_mean'] < 0 ], horizon, "dn", middate)
    # result_df = pd.concat([res1, res2], verify_integrity=True)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--lag",action="store",dest="lag",default=6)
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
        BARRA_COLS = ['ind1']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)

        daily_df = merge_barra_data(price_df, barra_df)
        analyst_df = load_ratings_hist(price_df[['ticker']], start, end)
        daily_df = merge_daily_calcs(analyst_df, daily_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')

    result_df = calc_rtg_forecast(daily_df, horizon, middate)

    print("Total Alpha Summary")
    print(result_df['rtg'].describe())

    dump_daily_alpha(result_df, 'rtg')









