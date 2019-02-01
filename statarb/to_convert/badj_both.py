#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def calc_badj_daily(daily_df, horizon):
    print("Caculating daily badj...")
    result_df = filter_expandable(daily_df)

    print("Calculating badj0...")
    result_df['badj0'] = result_df['log_ret'] / result_df['pbeta'] 
    result_df['badj0_B'] = winsorize_by_date(result_df[ 'badj0' ])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['badj0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    result_df['badj0_B_ma'] = indgroups['badj0_B']

    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['badj'+str(lag)+'_B_ma'] = shift_df['badj0_B_ma']
    
    return result_df

def calc_badj_intra(intra_df):
    print("Calculating badj intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating badjC...")
    result_df['badjC'] = (result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))) / result_df['pbeta']
    result_df['badjC_B'] = winsorize_by_ts(result_df[ 'badjC' ])

    print("Calulating badjC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['badjC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=True).transform(demean)
    result_df['badjC_B_ma'] = indgroups['badjC_B']
    
    print("Calculated {} values".format(len(result_df['badjC_B_ma'].dropna())))
    return result_df

def badj_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['badj_b'] = np.nan
    outsample_intra_df[ 'badjC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'badj' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'badj0_B_ma', lag, True, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "badj_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    coef0 = fits_df.ix['badj0_B_ma'].ix[horizon].ix['coef']
    outsample_intra_df[ 'badjC_B_ma_coef' ] = coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['badj0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'badj'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df['badj_b'] = outsample_intra_df['badjC_B_ma'] * outsample_intra_df['badjC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'badj_b'] += outsample_intra_df['badj'+str(lag)+'_B_ma'] * outsample_intra_df['badj'+str(lag)+'_B_ma_coef']

    return outsample_intra_df

def calc_badj_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = calc_badj_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_badj_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    sector_name = 'Energy'
    print("Running badj for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    result1_df = badj_fits(sector_df, sector_intra_results_df, horizon, "in", middate)

    print("Running badj for not sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]    
    result2_df = badj_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)    

    result_df = pd.concat([result1_df, result2_df], verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = 3
    pname = "./badj_b" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    freq="15Min"
    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1', 'pbeta']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close', 'overnight_log_ret']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['close', 'dopen', 'dvolume']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)

        daily_df = merge_barra_data(price_df, barra_df)
        daily_df = merge_intra_eod(daily_df, intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    result_df = calc_badj_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(result_df, 'badj_b')



