#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser

def calc_qhl_daily(daily_df, horizon):
    print("Caculating daily qhl...")

    result_df = daily_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['close', 'qhigh', 'qlow', 'date', 'ind1', 'sid' ]]

    print("Calculating qhl0...")
    result_df['qhl0'] = result_df['close'] / np.sqrt(result_df['qhigh'] * result_df['qlow'])
    result_df['qhl0_B'] = winsorize_by_group(result_df[ ['date', 'qhl0'] ], 'date')

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['qhl0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=True).transform(demean)
    result_df['qhl0_B_ma'] = indgroups['qhl0_B']
    result_df.set_index(keys=['date', 'sid'], inplace=True)

    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['qhl'+str(lag)+'_B_ma'] = shift_df['qhl0_B_ma']

    result_df = merge_daily_calcs(daily_df, result_df)
    return result_df

def calc_qhl_intra(intra_df, daily_df):
    print("Calculating qhl intra...")

    result_df = filter_expandable_intra(intra_df, daily_df)
    result_df = result_df.reset_index()    
    result_df = result_df[ ['iclose_ts', 'iclose', 'qhigh', 'qlow', 'date', 'ind1', 'sid' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating qhlC...")
    result_df['qhlC'] = result_df['iclose'] / np.sqrt(result_df['qhigh'] * result_df['qlow'])
    result_df['qhlC_B'] = winsorize_by_group(result_df[ ['iclose_ts', 'qhlC'] ], 'iclose_ts')

    print("Calulating qhlC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['qhlC_B', 'iclose_ts', 'ind1']].groupby(['iclose_ts', 'ind1'], sort=True).transform(demean)
    result_df['qhlC_B_ma'] = indgroups['qhlC_B']

    result_df = merge_intra_calcs(intra_df, result_df)
    return result_df

def qhl_fits(daily_df, intra_df, full_df, horizon, name, middate=None):
    if 'qhl_m' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['qhl_m'] = np.nan
        full_df[ 'qhlC_B_ma_coef' ] = np.nan
        for lag in range(1, horizon+1):
            full_df[ 'qhl' + str(lag) + '_B_ma_coef' ] = np.nan

    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    outsample = False
    if middate is not None:
        outsample = True
        insample_intra_df = intra_df[ intra_df['date'] <  middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate]

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'qhl0_B_ma', lag, outsample, 'daily')
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "qhl_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    print(df_dates(full_df))
    print(df_dates(intra_df))

    coef0 = fits_df.ix['qhl0_B_ma'].ix[horizon].ix['coef']
    full_df.ix[ outsample_intra_df.index, 'qhlC_B_ma_coef' ] = 0 #coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['qhl0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        full_df.ix[ outsample_intra_df.index, 'qhl'+str(lag)+'_B_ma_coef' ] = coef

    full_df.ix[ outsample_intra_df.index, 'qhl_m'] = full_df['qhlC_B_ma'] * full_df['qhlC_B_ma_coef']
    for lag in range(1,horizon):
        full_df.ix[ outsample_intra_df.index, 'qhl_m'] += full_df['qhl'+str(lag)+'_B_ma'] * full_df['qhl'+str(lag)+'_B_ma_coef']

    return full_df

def calc_qhl_forecast(daily_df, intra_df, horizon, outsample):
    daily_df = calc_qhl_daily(daily_df, horizon) 
    intra_df = calc_qhl_intra(intra_df, daily_df)
    full_df = merge_intra_data(daily_df, intra_df)

    middate = None
    if outsample:
        middate = intra_df.index[0][0] + (intra_df.index[len(intra_df)-1][0] - intra_df.index[0][0]) / 2
        print("Setting fit period before {}".format(middate))

    sector_name = 'Energy'
    print("Running qhl for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] == sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] == sector_name ]
    full_df = qhl_fits(sector_df, sector_intra_df, full_df, horizon, "in", middate)

    print("Running qhl for not sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] != sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] != sector_name ]    
    full_df = qhl_fits(sector_df, sector_intra_df, full_df, horizon, "ex", middate)
    
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
    pname = "./qhl_m" + start + "." + end
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
        intra_df = load_daybars(uni_df, start, end)
        daily_df = merge_barra_data(price_df, barra_df)
        daily_df = merge_intra_eod(daily_df, intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    full_df = calc_qhl_forecast(daily_df, intra_df, horizon, outsample)
    dump_alpha(outsample_df, 'qhl_m')
    dump_all(outsample_df)


