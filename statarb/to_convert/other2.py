#!/usr/bin/env python 

from __future__ import print_function
from alphacalc import *

from dateutil import parser as dateparser

def calc_other_daily(daily_df, horizon):
    print("Caculating daily other...")

    result_df = daily_df.reset_index()
    result_df = filter_expandable(result_df)
    result_df = result_df[ ['log_ret', 'insideness', 'date', 'ind1', 'sid' ]]

    print("Calculating other0...")
    result_df['other0'] = result_df['log_ret'] * result_df['insideness']
    result_df['other0_B'] = winsorize_by_group(result_df[ ['date', 'other0'] ], 'date')

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['other0_B', 'date', 'ind1']].groupby(['date', 'ind1'], sort=False).transform(demean)
    result_df['other0_B_ma'] = indgroups['other0_B']
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    
    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['other'+str(lag)+'_B_ma'] = shift_df['other0_B_ma']
        result_df['other'+str(lag)+'_B'] = shift_df['other0_B']

    daily_df = daily_df.reset_index()
    result_df = result_df.reset_index()
    result_df = pd.merge(daily_df, result_df, how='left', left_on=['date', 'sid'], right_on=['date', 'sid'], sort=True, suffixes=['', '_dead'])
    result_df = remove_dup_cols(result_df)
    result_df.set_index(keys=['date', 'sid'], inplace=True)

    return result_df

def calc_other_intra(intra_df, daily_df):
    print("Calculating other intra...")

    result_df = filter_expandable_intra(intra_df, daily_df)
    result_df = intra_df.reset_index()
    result_df = result_df[ [ 'iclose_ts', 'log_ret', 'insideness', 'open', 'iclose', 'overnight_log_ret', 'date', 'ind1', 'sid' ] ]
    result_df = result_df.dropna(how='any')

    print("Calulating otherC...")
    result_df['otherC'] = (result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['open']))) * result_df['insideness']
    result_df['otherC_B'] = winsorize_by_group(result_df[ ['iclose_ts', 'otherC'] ], 'iclose_ts')

    print("Calulating otherC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['otherC_B', 'iclose_ts', 'ind1']].groupby(['iclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['otherC_B_ma'] = indgroups['otherC_B']

    #important for keeping NaTs out of the following merge
    del result_df['date']

    print("Merging...")
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = pd.merge(intra_df, result_df, how='left', left_index=True, right_index=True, sort=True, suffixes=['_dead', ''])
    result_df = remove_dup_cols(result_df)

    return result_df

def other_fits(daily_df, intra_df, full_df, horizon, name):
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])

    regress_intra_df = intra_df
    regress_daily_df = daily_df
#    middate = intra_df.index[0][0] + (intra_df.index[len(intra_df)-1][0] - intra_df.index[0][0]) / 2
#    print "Setting fit period before {}".format(middate)
#    regress_intra_df = intra_df[ intra_df['date'] <  middate ]

    intra_horizon = 3
    fitresults_df, intraForwardRets_df = regress_alpha_intra(regress_intra_df, 'otherC_B', intra_horizon)
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "other_intra_"+name+"_" + df_dates(regress_intra_df))

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
#    regress_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]

    for lag in range(1,4):
        fitresults_df, dailyForwardRets_df = regress_alpha_daily(regress_daily_df, 'other0_B', lag)
        full_df = merge_intra_data(dailyForwardRets_df, full_df)
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    
    plot_fit(fits_df, "other_daily_"+name+"_" + df_dates(regress_daily_df))

    if name not in full_df.columns:
        print("Creating forecast columns...")
        full_df['other'] = np.nan
        full_df['otherma'] = np.nan
        full_df[ 'otherC_B_ma_coef' ] = np.nan
        full_df[ 'otherC_B_ma_coef' ] = np.nan
        full_df[ 'otherC_B_coef' ] = np.nan
        full_df[ 'otherC_B_coef' ] = np.nan
        for lag in range(0, horizon+1):
            full_df[ 'other' + str(lag) + '_B_ma_coef' ] = np.nan
            full_df[ 'other' + str(lag) + '_B_coef' ] = np.nan

    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['other0_B'].ix[horizon].ix['coef']
    full_df.ix[ intra_df.index, 'otherC_B_coef' ] = coef0
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['other0_B'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        full_df.ix[ intra_df.index, 'other'+str(lag)+'_B_coef' ] = coef

    full_df.ix[ intra_df.index, 'other'] = full_df['otherC_B'] * full_df['otherC_B_coef']
    for lag in range(1,horizon):
        full_df.ix[ intra_df.index, 'other'] += full_df['other'+str(lag)+'_B'] * full_df['other'+str(lag)+'_B_coef']
     
    #erase the forecast during the fit period
#    full_df.ix[ full_df['date'] < middate, 'qhl' ]  = np.nan
    
    return full_df

def calc_other_forecast(daily_df, intra_df, horizon):
    daily_df = calc_other_daily(daily_df, horizon) 
    intra_df = calc_other_intra(intra_df, daily_df)
    full_df = merge_intra_data(daily_df, intra_df)

    full_df = other_fits(daily_df, intra_df, full_df, horizon, "")

    return full_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = 2

    start = dateparser.parse(start)
    end = dateparser.parse(end)

    uni_df = get_uni(start, end, lookback)
    barra_df = load_barra(uni_df, start, end)
    price_df = load_prices(uni_df, start, end)
    intra_df = load_bars(uni_df, start, end)

    daily_df = merge_barra_data(price_df, barra_df)
    daily_df = merge_intra_eod(daily_df, intra_df)
    intra_df = merge_intra_data(daily_df, intra_df)

    full_df = calc_other_forecast(daily_df, intra_df, horizon)

    dump_alpha(full_df, 'other')
    dump_all(full_df)
    sim_alphas(full_df, 'other')

