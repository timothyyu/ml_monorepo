#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser

def calc_hl_daily(full_df, horizon):
    print("Caculating daily hl...")
    result_df = full_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['close', 'high', 'low', 'date', 'ind1', 'sid' ]]

    print("Calculating hl0...")
    result_df['hl0'] = result_df['close'] / np.sqrt(result_df['high'] * result_df['low'])
    result_df['hl0_B'] = winsorize(result_df['hl0'])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['hl0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['hl0_B_ma'] = indgroups['hl0_B']
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    
    print("Calulating lags...")
    for lag in range(1,horizon):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['hl'+str(lag)+'_B_ma'] = shift_df['hl0_B_ma']

    result_df = pd.merge(full_df, result_df, how='left', left_index=True, right_index=True, sort=False, suffixes=['', '_dead'])
    result_df = remove_dup_cols(result_df)
    return result_df

def calc_hl_intra(full_df):
    print("Calculating hl intra...")
    result_df = full_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['iclose_ts', 'iclose', 'dhigh', 'dlow', 'date', 'ind1', 'sid' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating hlC...")
    result_df['hlC'] = result_df['iclose'] / np.sqrt(result_df['dhigh'] * result_df['dlow'])
    result_df['hlC_B'] = winsorize(result_df['hlC'])

    print("Calulating hlC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['hlC_B', 'iclose_ts', 'ind1']].groupby(['iclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['hlC_B_ma'] = indgroups['hlC_B']

    #important for keeping NaTs out of the following merge
    del result_df['date']

    print("Merging...")
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = pd.merge(full_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['_dead', ''])
    result_df = remove_dup_cols(result_df)

    return result_df

def hl_fits(daily_df, intra_df, full_df, horizon, name):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fits_df = fits_df.append(regress_alpha_intra(intra_df, 'hlC_B_ma', 1), ignore_index=True)
    plot_fit(fits_df, "hl_intra_"+name+"_" + df_dates(intra_df))
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])

    for lag in range(1,horizon+1):
        fits_df = fits_df.append(regress_alpha_daily(daily_df, 'hl0_B_ma', lag), ignore_index=True) 
    plot_fit(fits_df, "hl_daily_" +name+"_"+ df_dates(daily_df))
    
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    coef0 = fits_df.ix['hl0_B_ma'].ix[horizon].ix['coef']

    if 'hl' not in full_df.columns:
        print("Creating forecast columns...")
        full_df['hl'] = np.nan
        full_df[ 'hlC_B_ma_coef' ] = np.nan
        for lag in range(0, horizon+1):
            full_df[ 'hl' + str(lag) + '_B_ma_coef' ] = np.nan
        
    full_df.ix[ intra_df.index, 'hlC_B_ma_coef' ] = coef0
    full_df.ix[ intra_df.index, 'hl0_B_ma_coef' ] = coef0
    for lag in range(1,horizon+1):
        full_df.ix[ intra_df.index, 'hl'+str(lag)+'_B_ma_coef' ] = coef0 - fits_df.ix['hl0_B_ma'].ix[lag].ix['coef'] 

    full_df.ix[ intra_df.index, 'hl'] = full_df['hlC_B_ma'] * full_df['hlC_B_ma_coef']
    for lag in range(0,horizon):
        full_df.ix[ intra_df.index, 'hl'] += full_df['hl'+str(lag)+'_B_ma'] * full_df['hl'+str(lag)+'_B_ma_coef']
    
    full_df.ix[ intra_df.index, 'hl'] = 4.0

    return full_df

def calc_hl_forecast(daily_df, intra_df, horizon):
    daily_df = calc_hl_daily(daily_df, horizon) 
    intra_df = calc_hl_intra(intra_df)
    full_df = merge_intra_data(daily_df, intra_df)

    sector_name = 'Energy'
    print("Running hl for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] == sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] == sector_name ]
    full_df = hl_fits(sector_df, sector_intra_df, full_df, horizon, "in")

    print("Running hl for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] != sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] != sector_name ]
    full_df = hl_fits(sector_df, sector_intra_df, full_df, horizon, "ex")

    dump_alpha(full_df, 'hl')
  
    return full_df

if __name__=="__main__":            
    start = "20120601"
    end = "20130101"
    lookback = 30
    horizon = 3

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    uni_df = get_uni(start, end, lookback)
    barra_df = load_barra(uni_df, start, end)
    price_df = load_prices(uni_df, start, end)
    daily_df = merge_barra_data(price_df, barra_df)
    daybar_df = load_daybars(uni_df, start, end)
    intra_df = merge_intra_data(daily_df, daybar_df)

    full_df = calc_hl_forecast(daily_df, intra_df, horizon)


