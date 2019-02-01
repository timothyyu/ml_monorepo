#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser

def calc_bd_intra(intra_df):
    print("Calculating bd1 intra...")

    result_df = intra_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ [ 'iclose', 'iclose_ts', 'bidHitDollars', 'midHitDollars', 'askHitDollars', 'date', 'ind1', 'sid' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating bd1...")
    result_df['bd1'] = (result_df['askHitDollars'].diff() - result_df['bidHitDollars'].diff()) / (result_df['askHitDollars'].diff() + result_df['midHitDollars'].diff() + result_df['bidHitDollars'].diff())
    result_df['bd1_B'] = winsorize(result_df['bdC'])

    print("Calulating bdC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['bdC_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['bdC_B_ma'] = indgroups['bdC_B']

    #important for keeping NaTs out of the following merge
    del result_df['date']

    print("Merging...")
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = pd.merge(intra_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['_dead', ''])
    result_df = remove_dup_cols(result_df)

    return result_df

def bd_fits(daily_df, intra_df, full_df, name):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fits_df = fits_df.append(regress_alpha_intra(intra_df, 'bd1_B_ma', 1), ignore_index=True)
    fits_df = fits_df.append(regress_alpha_intra(intra_df, 'bd1_B', 1), ignore_index=True)

    plot_fit(fits_df[ fits_df['indep'] == 'bd1_B_ma' ], name + "ma_intra_" + df_dates(daily_df))
    plot_fit(fits_df[ fits_df['indep'] == 'bd1_B' ], name + "_intra_" + df_dates(daily_df))

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    coef0 = fits_df.ix['bd1_B_ma'].ix[horizon].ix['coef']
    full_df[ 'bd1_B_ma_coef' ] = coef0
    full_df['bd1ma'] = full_df['bd1_B_ma'] * full_df['bd1_B_ma_coef']

    coef0 = fits_df.ix['bd1_B'].ix[horizon].ix['coef']
    full_df[ 'bd1_B_coef' ] = coef0
    full_df['bd1'] = full_df['bd1_B'] * full_df['bd1_B_coef']

    return full_df

def calc_bd_forecast(intra_df):
    intra_df = calc_bd_intra(intra_df)
    full_df = merge_intra_data(daily_df, intra_df)

    full_df = bd_fits(daily_df, intra_df, full_df, "bd1")

    return full_df

if __name__=="__main__":            
    start = "20120101"
    end = "20120115"
    lookback = 30

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    uni_df = get_uni(start, end, lookback)
    barra_df = load_barra(uni_df, start, end)
    price_df = load_prices(uni_df, start, end)
    daily_df = merge_barra_data(price_df, barra_df)
    ibar_df = load_bars(uni_df, start, end)
    intra_df = merge_intra_data(daily_df, ibar_df)

    full_df = calc_bd_forecast(intra_df)

    dump_alpha(full_df, 'bd1')
    dump_alpha(full_df, 'bdma1')
