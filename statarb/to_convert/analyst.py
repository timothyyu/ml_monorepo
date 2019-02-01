#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

from pandas.stats.moments import ewma

def calc_rtg_daily(daily_df, horizon):
    print("Caculating daily rtg...")
    result_df = filter_expandable(daily_df)

    print("Calculating rtg0...")    
    halflife = horizon / 2
#    result_df['dk'] = np.exp( -1.0 * halflife *  (result_df['gdate'] - result_df['last']).astype('timedelta64[D]').astype(int) )

    result_df['cum_ret'] = pd.rolling_sum(result_df['log_ret'], horizon)

    result_df['sum'] = result_df['mean'] * result_df['count']
    result_df['det_diff'] = result_df['sum'].diff()    
    result_df['det_diff_dk'] = ewma(result_df['det_diff'], halflife=horizon )   
    result_df['rtg0'] = result_df['det_diff_dk'] * result_df['det_diff_dk']

    # result_df['median'] = -1.0 * (result_df['median'] - 3)
    # result_df['med_diff'] = result_df['median'].unstack().diff().stack()
    # result_df['med_diff_dk'] = pd.rolling_sum( result_df['dk'] * result_df['med_diff'], window=horizon )
    # result_df['rtg0'] = (np.sign(result_df['med_diff_dk']) * np.sign(result_df['cum_ret'])).clip(lower=0) * result_df['med_diff_dk']


    demean = lambda x: (x - x.mean())
    indgroups = result_df[['rtg0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['rtg0_ma'] = indgroups['rtg0']

#    result_df['rtg0_ma'] = result_df['rtg0_ma'] * (np.sign(result_df['rtg0_ma']) * np.sign(result_df['cum_ret']))

#    result_df['rtg0_ma'] = result_df['rtg0']

    shift_df = result_df.unstack().shift(1).stack()
    result_df['rtg1_ma'] = shift_df['rtg0_ma']

    return result_df

def rtg_fits(daily_df, horizon, name, middate=None):
    insample_daily_df = daily_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_daily_df = daily_df[ daily_df.index.get_level_values('date') >= middate ]

    outsample_daily_df['rtg'] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'rtg0_ma', ii, False, 'daily') 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "rtg_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['rtg0_ma'].ix[horizon].ix['coef']
    print("Coef{}: {}".format(0, coef0))
    outsample_daily_df[ 'rtg0_ma_coef' ] = coef0

    outsample_daily_df[ 'rtg' ] = outsample_daily_df['rtg0_ma'] * outsample_daily_df['rtg0_ma_coef']
    
    return outsample_daily_df

def calc_rtg_forecast(daily_df, horizon, middate):
    daily_results_df = calc_rtg_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

    # results = list()
    # for sector_name in daily_results_df['sector_name'].dropna().unique():
    #     print "Running rtg for sector {}".format(sector_name)
    #     sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #     result_df = rtg_fits(sector_df, horizon, sector_name, middate)
    #     results.append(result_df)
    # result_df = pd.concat(results, verify_integrity=True)

    result_df = rtg_fits(daily_results_df, horizon, "", middate)

    # res1 = rtg_fits( daily_results_df[ daily_results_df['med_diff_dk'] > 0 ], horizon, "up", middate)
    # res2 = rtg_fits( daily_results_df[ daily_results_df['med_diff_dk'] < 0 ], horizon, "dn", middate)
    # result_df = pd.concat([res1, res2], verify_integrity=True)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--lag",action="store",dest="lag",default=20)
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
    dump_daily_alpha(result_df, 'rtg')









