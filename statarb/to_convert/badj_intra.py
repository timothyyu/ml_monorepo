#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser
import argparse

def calc_o2c(daily_df, horizon):
    print("Caculating daily o2c...")

    result_df = daily_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['log_ret', 'pbeta', 'date', 'ind1', 'sid', 'mkt_cap' ]]

    print("Calculating o2c0...")
    result_df['o2c0'] = result_df['log_ret'] / result_df['pbeta'] 
    result_df['o2c0_B'] = winsorize_by_group(result_df[ ['date', 'o2c0'] ], 'date')

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['o2c0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['o2c0_B_ma'] = indgroups['o2c0_B']
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    
    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['o2c' + str(lag) + '_B_ma'] = shift_df['o2c0_B_ma']

    result_df = pd.merge(daily_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['', '_dead'])
    result_df = remove_dup_cols(result_df)
    return result_df

def calc_o2c_intra(intra_df, daily_df):
    print("Calculating o2c intra...")

    result_df = filter_expandable_intra(intra_df, daily_df)
    result_df = result_df.reset_index()    
    result_df = result_df[ ['iclose_ts', 'iclose', 'dopen', 'overnight_log_ret', 'pbeta', 'date', 'ind1', 'sid', 'mkt_cap' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating o2cC...")
    result_df['o2cC'] = (result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))) / result_df['pbeta']
    result_df['o2cC_B'] = winsorize_by_group(result_df[ ['iclose_ts', 'o2cC'] ], 'iclose_ts')

    print("Calulating o2cC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['o2cC_B', 'iclose_ts', 'ind1']].groupby(['iclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['o2cC_B_ma'] = indgroups['o2cC_B']

    #important for keeping NaTs out of the following merge
    del result_df['date']

    print("Merging...")
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = pd.merge(intra_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['_dead', ''])
    result_df = remove_dup_cols(result_df)

    return result_df

def o2c_fits(daily_df, intra_df, full_df, horizon, name, middate=None):
    if 'badj_i' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['badj_i'] = np.nan
        full_df[ 'o2cC_B_ma_coef' ] = np.nan

    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    outsample = False
    if middate is not None:
        outsample = True
        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df['date'] < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    intra_horizon = horizon
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df, intraForwardRets_df = regress_alpha(insample_intra_df, 'o2cC_B_ma', intra_horizon, outsample, True)
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "badj_intra_"+name+"_" + df_dates(insample_intra_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    unstacked = outsample_intra_df[ ['ticker', 'name'] ].unstack()
    coefs = dict()
    coefs[1] = unstacked.between_time('09:30', '10:31').stack().index
    coefs[2] = unstacked.between_time('10:30', '11:31').stack().index
    coefs[3] = unstacked.between_time('11:30', '12:31').stack().index
    coefs[4] = unstacked.between_time('12:30', '13:31').stack().index
    coefs[5] = unstacked.between_time('13:30', '14:31').stack().index
    coefs[6] = unstacked.between_time('14:30', '15:31').stack().index
    unstacked = None

    for ii in range(1,7):
        full_df.ix[ coefs[ii], 'o2cC_B_ma_coef' ] = fits_df.ix['o2cC_B_ma'].ix[ii].ix['coef']

    full_df.ix[ outsample_intra_df.index, 'badj_i'] = full_df['o2cC_B_ma'] * full_df['o2cC_B_ma_coef']
    
    return full_df

def calc_o2c_forecast(daily_df, intra_df, horizon, outsample):
    daily_df = calc_o2c(daily_df, horizon) 
    intra_df = calc_o2c_intra(intra_df, daily_df)
    full_df = merge_intra_data(daily_df, intra_df)

    middate = None
    if outsample:
        middate = intra_df.index[0][0] + (intra_df.index[len(intra_df)-1][0] - intra_df.index[0][0]) / 2
        print("Setting fit period before {}".format(middate))

    sector_name = 'Energy'
    print("Running o2c for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] == sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] == sector_name ]
    full_df = o2c_fits(sector_df, sector_intra_df, full_df, horizon, "in", middate)

    print("Running o2c for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] != sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] != sector_name ]
    full_df = o2c_fits(sector_df, sector_intra_df, full_df, horizon, "ex", middate)

    outsample_df = full_df
    if outsample_df:
        full_df = full_df[ full_df['date'] >= middate ]
  
    return full_df, outsample_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--os",action="store",dest="outsample",default=False)
    args = parser.parse_args()    

    start = args.start
    end = args.end
    outsample = args.outsample
    lookback = 30
    horizon = 3

    pname = "./badj_i." + start + "." + end

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
        print("Successfully loaded cached data...")
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        barra_df = load_barra(uni_df, start, end)
        price_df = load_prices(uni_df, start, end)
        daily_df = merge_barra_data(price_df, barra_df)
        daybar_df = load_daybars(uni_df, start, end)
        intra_df = merge_intra_data(daily_df, daybar_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    full_df, outsample_df = calc_o2c_forecast(daily_df, intra_df, horizon, outsample)

    dump_alpha(outsample_df, 'badj_i')
    dump_all(outsample_df)
