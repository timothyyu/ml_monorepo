#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *
from calc import *

def calc_rrb_daily(daily_df, horizon):
    print("Caculating daily rrb...")
    result_df = filter_expandable(daily_df)

    print("Calculating rrb0...")
    result_df['rrb0'] = result_df['barraResidRet']
    print(result_df['rrb0'].head())
    result_df['rrb0_B'] = winsorize_by_date(result_df['rrb0'])

    demean = lambda x: (x - x.mean())
    dategroups = result_df[['rrb0_B', 'gdate']].groupby(['gdate'], sort=False).transform(demean)
    result_df['rrb0_B_ma'] = dategroups['rrb0_B']
    print("Calculated {} values".format(len(result_df)))

    print("Calulating lags...")
    for lag in range(1,horizon):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['rrb'+str(lag)+'_B_ma'] = shift_df['rrb0_B_ma']

    return result_df

def calc_rrb_intra(intra_df):
    print("Calculating rrb intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating rrbC...")
    result_df['rrbC'] = result_df['barraResidRetI']
    result_df['rrbC_B'] = winsorize_by_ts(result_df['rrbC'])

    print(result_df['rrbC'].tail())

    print("Calulating rrbC_ma...")
    demean = lambda x: (x - x.mean())
    dategroups = result_df[['rrbC_B', 'giclose_ts']].groupby(['giclose_ts'], sort=False).transform(demean)
    result_df['rrbC_B_ma'] = dategroups['rrbC_B']

    return result_df

def rrb_fits(daily_df, intra_df, horizon, name, middate):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['rrb'] = np.nan
    outsample_intra_df[ 'rrbC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'rrb' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        print(insample_daily_df.head())
        fitresults_df = regress_alpha(insample_daily_df, 'rrb0_B_ma', lag, True, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "rrb_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    coef0 = fits_df.ix['rrb0_B_ma'].ix[horizon].ix['coef']
    outsample_intra_df[ 'rrbC_B_ma_coef' ] = coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['rrb0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'rrb'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df['rrb'] = outsample_intra_df['rrbC_B_ma'] * outsample_intra_df['rrbC_B_ma_coef']
#    outsample_intra_df['rrb_b'] = 0
    for lag in range(1,horizon):
        outsample_intra_df[ 'rrb'] += outsample_intra_df['rrb'+str(lag)+'_B_ma'] * outsample_intra_df['rrb'+str(lag)+'_B_ma_coef']

    return outsample_intra_df

def calc_rrb_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = daily_df
    intra_results_df = intra_df

    sector_name = 'Energy'
    # print "Running rrb for sector {}".format(sector_name)
    # sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    # sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    # result1_df = rrb_fits(sector_df, sector_intra_results_df, horizon, "in", middate)

    print("Running rrb for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]
    result2_df = rrb_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)
  
    result_df = pd.concat([result2_df], verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--horizon",action="store",dest="horizon",default=3)
    parser.add_argument("--freq",action="store",dest="freq",default='15Min')
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.horizon)
    pname = "./rrb" + start + "." + end
    freq = args.freq
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)

    loaded = False
    try:        
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Could not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        barra_df = load_barra(uni_df, start, end)    
        barra_df = transform_barra(barra_df)
        PRICE_COLS = ['close', 'overnight_log_ret']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        daily_df = merge_barra_data(price_df, barra_df)
        DBAR_COLS = ['close', 'dvolume', 'dopen']
        daybar_df = load_daybars(price_df[ ['ticker'] ], start, end, DBAR_COLS, freq)
        intra_df = merge_intra_data(daily_df, daybar_df)

        daily_df, factorRets_df = calc_factors(daily_df, True)
        daily_df = calc_rrb_daily(daily_df, horizon) 
        forwards_df = calc_forward_returns(daily_df, horizon)
        daily_df = pd.concat( [daily_df, forwards_df], axis=1)
        intra_df, factorRets_df = calc_intra_factors(intra_df, True)
        intra_df = calc_rrb_intra(intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    full_df = calc_rrb_forecast(daily_df, intra_df, horizon, middate)
    print(full_df.columns)
    dump_alpha(full_df, 'rrb')
    # dump_alpha(full_df, 'rrbC_B_ma')
    # dump_alpha(full_df, 'rrb0_B_ma')
    # dump_all(full_df)

