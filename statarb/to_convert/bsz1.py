#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser

def calc_bsz_daily(intra_df, horizon):
    print("Caculating daily bsz...")

    daily_df = intra_df.unstack().at_time('16:00').stack()
    daily_df = daily_df.reset_index()
    result_df = filter_expandable(daily_df)
    daily_df.set_index(keys=['date', 'sid'], inplace=True)
    result_df = result_df[ ['meanSpread', 'meanEffectiveSpread', 'meanBidSize', 'meanAskSize', 'date', 'ind1', 'sid' ]]

    print("Calculating bsz0...")
    result_df['bsz0'] = ((result_df['meanAskSize'] - result_df['meanBidSize']) / (result_df['meanBidSize'] + result_df['meanAskSize'])) / np.sqrt(result_df['meanSpread'])
    result_df['bsz0_B'] = winsorize(result_df['bsz0'])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['bsz0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['bsz0_B_ma'] = indgroups['bsz0_B']
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    
    print("Calulating lags...")
    for lag in range(1,horizon):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['bsz'+str(lag)+'_B_ma'] = shift_df['bsz0_B_ma']
        result_df['bsz'+str(lag)+'_B'] = shift_df['bsz0_B']

    result_df = pd.merge(daily_df, result_df, how='left', left_index=True, right_index=True, sort=False, suffixes=['', '_dead'])
    result_df = remove_dup_cols(result_df)
    return result_df

def calc_bsz_intra(intra_df):
    print("Calculating bsz intra...")

    result_df = intra_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ [ 'iclose_ts', 'meanSpread', 'meanEffectiveSpread', 'meanBidSize', 'meanAskSize', 'date', 'ind1', 'sid' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating bszC...")
    result_df['bszC'] = ((result_df['meanAskSize'] - result_df['meanBidSize']) / (result_df['meanBidSize'] + result_df['meanAskSize'])) / np.sqrt(result_df['meanSpread'])
    result_df['bszC_B'] = winsorize(result_df['bszC'])

    print("Calulating bszC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['bszC_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['bszC_B_ma'] = indgroups['bszC_B']

    #important for keeping NaTs out of the following merge
    del result_df['date']

    print("Merging...")
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = pd.merge(intra_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['_dead', ''])
    result_df = remove_dup_cols(result_df)

    return result_df

def bsz_fits(daily_df, intra_df, full_df, horizon, name):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fits_df = fits_df.append(regress_alpha_intra(intra_df, 'bszC_B_ma', 1), ignore_index=True)
    fits_df = fits_df.append(regress_alpha_intra(intra_df, 'bszC_B', 1), ignore_index=True)

    plot_fit(fits_df[ fits_df['indep'] == 'bszC_B_ma' ], name + "ma_intra_" + df_dates(daily_df))
    plot_fit(fits_df[ fits_df['indep'] == 'bszC_B' ], name + "_intra_" + df_dates(daily_df))

    for lag in range(1,horizon+1):
        fits_df = fits_df.append(regress_alpha_daily(daily_df, 'bsz0_B_ma', lag), ignore_index=True) 
        fits_df = fits_df.append(regress_alpha_daily(daily_df, 'bsz0_B', lag), ignore_index=True) 

    plot_fit(fits_df[ fits_df['indep'] == 'bsz0_B_ma' ], name + "ma_daily_" + df_dates(daily_df))
    plot_fit(fits_df[ fits_df['indep'] == 'bsz0_B' ], name + "_daily_" + df_dates(daily_df))

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    coef0 = fits_df.ix['bsz0_B_ma'].ix[horizon].ix['coef']
    full_df[ 'bszC_B_ma_coef' ] = coef0
    full_df[ 'bsz0_B_ma_coef' ] = coef0
    for lag in range(1,horizon+1):
        full_df[ 'bsz'+str(lag)+'_B_ma_coef' ] = coef0 - fits_df.ix['bsz0_B_ma'].ix[lag].ix['coef'] 

    full_df['bszma'] = full_df['bszC_B_ma'] * full_df['bszC_B_ma_coef']
    for lag in range(0,horizon):
        full_df['bszma'] += full_df['bsz'+str(lag)+'_B_ma'] * full_df['bsz'+str(lag)+'_B_ma_coef']

    coef0 = fits_df.ix['bsz0_B'].ix[horizon].ix['coef']
    full_df[ 'bszC_B_coef' ] = coef0
    full_df[ 'bsz0_B_coef' ] = coef0
    for lag in range(1,horizon+1):
        full_df[ 'bsz'+str(lag)+'_B_coef' ] = coef0 - fits_df.ix['bsz0_B_ma'].ix[lag].ix['coef'] 

    full_df['bsz'] = full_df['bszC_B'] * full_df['bszC_B_coef']
    for lag in range(0,horizon):
        full_df['bsz'] += full_df['bsz'+str(lag)+'_B'] * full_df['bsz'+str(lag)+'_B_coef']

    return full_df

def calc_bsz_forecast(intra_df, horizon):
    daily_df = calc_bsz_daily(intra_df, horizon) 
    intra_df = calc_bsz_intra(intra_df)
    full_df = merge_intra_data(daily_df, intra_df)

    sector_name = 'Energy'
    print("Running bsz for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] == sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] == sector_name ]
    full_df = bsz_fits(sector_df, sector_intra_df, full_df, horizon, "bsz_in")

    print("Running bsz for sector {}".format(sector_name))
    sector_df = daily_df[ daily_df['sector_name'] != sector_name ]
    sector_intra_df = intra_df[ intra_df['sector_name'] != sector_name ]
    full_df = bsz_fits(sector_df, sector_intra_df, full_df, horizon, "bsz_ex")
  
    return full_df

if __name__=="__main__":            
    start = "20130201"
    end = "20130401"
    lookback = 30
    horizon = 5

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    uni_df = get_uni(start, end, lookback)
    barra_df = load_barra(uni_df, start, end)
    price_df = load_prices(uni_df, start, end)
    daily_df = merge_barra_data(price_df, barra_df)
    ibar_df = load_bars(uni_df, start, end)
    intra_df = merge_intra_data(daily_df, ibar_df)

    full_df = calc_bsz_forecast(intra_df, horizon)

    dump_alpha(full_df, 'bsz')
    dump_alpha(full_df, 'bszma')
