#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser
import argparse

def calc_o2c(daily_df, horizon):
    print("Caculating daily o2c...")
    result_df = daily_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['log_ret', 'pbeta', 'date', 'ind1', 'sid' ]]

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

    result_df = merge_daily_calcs(daily_df, result_df)
    return result_df

def calc_o2c_intra(intra_df, daily_df):
    print("Calculating o2c intra...")

    result_df = filter_expandable_intra(intra_df, daily_df)
    result_df = result_df[ ['iclose', 'dopen', 'overnight_log_ret', 'pbeta', 'date', 'ind1' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating o2cC...")
    result_df['o2cC'] = (result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))) / result_df['pbeta']
    result_df['o2cC_B'] = winsorize_by_ts(result_df[ ['o2cC'] ])

    print("Calulating o2cC_ma...")
    result_df.reset_index(inplace=True)
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['o2cC_B', 'iclose_ts', 'ind1']].groupby(['iclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['o2cC_B_ma'] = indgroups['o2cC_B']
    result_df.set_index(['iclose_ts', 'sid'], inplace=True)

    result_df = merge_intra_calcs(intra_df, result_df)
    return result_df

def o2c_fits(daily_df, intra_df, full_df, horizon, name, middate=None):
    if 'badj_m' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['badj_m'] = np.nan
        full_df[ 'o2cC_B_ma_coef' ] = np.nan
        for lag in range(1, horizon+1):
            full_df[ 'o2c' + str(lag) + '_B_ma_coef' ] = np.nan

    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    outsample = False
    if middate is not None:
        outsample = True
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    insample_daily_df = insample_daily_df.reset_index()
    insample_daily_df['dow'] = insample_daily_df['date'].apply(lambda x: x.weekday())
    insample_daily_df.set_index(['date', 'sid'], inplace=True)
    outsample_intra_df['dow'] = outsample_intra_df['date'].apply(lambda x: x.weekday())

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'o2c0_B_ma', lag, True, 'dow')
        fits_df = fits_df.append(fitresults_df, ignore_index=True)  
    plot_fit(fits_df, "badj_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    for day, daygroup in insample_daily_df.groupby('dow'):
        idx = outsample_intra_df[ outsample_intra_df['dow'] == day ].index
        day = int(day)
        coef0 = fits_df.ix['o2c0_B_ma'].ix[horizon * 10 + day].ix['coef']
        full_df.ix[ idx, 'o2cC_B_ma_coef' ] = 0#coef0
        print("{} {} Coef0: {}".format(name, day, coef0))
        for lag in range(1,horizon):
            coef = coef0 - fits_df.ix['o2c0_B_ma'].ix[lag * 10 + day].ix['coef'] 
            print("{} {} Coef{}: {}".format(name, day, lag, coef))
            full_df.ix[ idx, 'o2c'+str(lag)+'_B_ma_coef' ] = coef

    full_df.ix[ outsample_intra_df.index, 'badj_m'] = full_df['o2cC_B_ma'] * full_df['o2cC_B_ma_coef']
    for lag in range(1,horizon):
        full_df.ix[ outsample_intra_df.index, 'badj_m'] += full_df['o2c'+str(lag)+'_B_ma'] * full_df['o2c'+str(lag)+'_B_ma_coef']

    return full_df

def calc_o2c_forecast(daily_df, intra_df, horizon, outsample):
    daily_df = calc_o2c(daily_df, horizon) 
    daily_df = calc_forward_returns(daily_df, horizon)
    intra_df = calc_o2c_intra(intra_df, daily_df)
    full_df = merge_intra_data(daily_df, intra_df)

    middate = None
    if outsample:
        middate = daily_df.index[0][0] + (daily_df.index[len(daily_df)-1][0] - daily_df.index[0][0]) / 2
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

    if outsample:
        full_df = full_df[ full_df['date'] > middate ]
    return full_df

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

    pname = "./badj_m" + start + "." + end

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
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

    outsample_df = calc_o2c_forecast(daily_df, intra_df, horizon, outsample)

    dump_alpha(outsample_df, 'badj_m')
    dump_all(outsample_df)

