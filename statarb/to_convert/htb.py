#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def calc_htb_daily(daily_df, horizon):
    print("Caculating daily htb...")
    result_df = filter_expandable(daily_df)

    print("Calculating htb0...")
    result_df['htbC'] = result_df['fee_rate'] 
    result_df['htbC_B'] = winsorize_by_date(result_df[ 'htbC' ])

    print("Calulating lags...")
    for lag in range(0,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['htb'+str(lag) + "_B"] = shift_df['htbC_B']
    
    return result_df

def htb_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['htb'] = np.nan
    outsample_intra_df[ 'htbC_B_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'htb' + str(lag) + '_B_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'htb0_B', lag, True, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "htb_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    coef0 = fits_df.ix['htb0_B'].ix[horizon].ix['coef']
    outsample_intra_df['htbC_B_coef'] = coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['htb0_B'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'htb'+str(lag)+'_B_coef' ] = coef

    outsample_intra_df['htb'] = outsample_intra_df['htbC_B'] * outsample_intra_df['htbC_B_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'htb'] += outsample_intra_df['htb'+str(lag)+'_B'] * outsample_intra_df['htb'+str(lag)+'_B_coef']

    return outsample_intra_df

def calc_htb_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = calc_htb_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    #    intra_results_df = calc_htb_intra(intra_df)
    intra_results_df = intra_df
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    result_df = htb_fits(daily_results_df, intra_results_df, horizon, "", middate)

    return result_df

if __name__== "__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='30Min')
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = 5
    pname = "./htb" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    freq = args.freq
    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['close', 'qhigh', 'qlow']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)
        daily_df = merge_barra_data(price_df, barra_df)
        intra_df = merge_intra_data(daily_df, intra_df)

        locates_df = load_locates(price_df[['ticker']], start, end)
        daily_df = pd.merge(daily_df, locates_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
        daily_df = remove_dup_cols(daily_df)         

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    result_df = calc_htb_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(result_df, 'htb')



