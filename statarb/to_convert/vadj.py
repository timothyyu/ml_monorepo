#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    print("Mkt return: {} {}".format(group['gdate'], ((d * w).sum() / w.sum())))
    res = b * ((d * w).sum() / w.sum())
    return res

def wavg2(group):
    b = group['pbeta']
    d = group['cur_log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res

def wavg_ind(group):
    d = group['vadj0_B']
    w = group['mkt_cap_y'] / 1e6
    res = ((d * w).sum() / w.sum())
    return res

def volmult_i(group):
    d = group['dpvolume']
    m = group['dpvolume_med_21']
    adj = d.sum()/m.sum()
    res = group['dpvolume'] / adj
    return res

def volmult2(group):
    d = group['tradable_volume']
    m = group['tradable_med_volume_21']
    adj = d.sum()/m.sum()
    res = group['tradable_volume'] / adj
    return res

def calc_vadj_daily(daily_df, horizon):
    print("Caculating daily vadj...")
    result_df = filter_expandable(daily_df)

    print("Calculating vadj0...")
    result_df['tradable_volume_adj'] = result_df[['tradable_med_volume_21', 'tradable_volume', 'gdate']].groupby('gdate').apply(volmult2).reset_index(level=0)['tradable_volume']
    result_df['rv'] = result_df['tradable_volume_adj'].astype(float) / result_df['tradable_med_volume_21_y']
    # result_df['dpvolume'] = result_df['dvolume'].astype(float) * result_df['dvwap']
    # result_df['dpvolume_adj'] = result_df[['dpvolume_med_21', 'dpvolume', 'gdate']].groupby('gdate').apply(volmult).reset_index(level=0)['dpvolume']
    # result_df['rv'] = (result_df['dpvolume_adj'] - result_df['dpvolume_med_21']) / result_df['dpvolume_std_21']

    print(result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].head())
    result_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    result_df = result_df.dropna(subset=['log_ret', 'pbeta', 'mkt_cap_y', 'gdate'])
    result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['log_ret'] - result_df['bret']
    result_df['vadj0'] = result_df['rv'] * np.sign(result_df['badjret']).fillna(0)

#    result_df = result_df.dropna(subset=['vadj0'])
    result_df['vadj0_B'] = winsorize_by_date(result_df['vadj0'])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['vadj0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=False).transform(demean)
    result_df['vadj0_B_ma'] = indgroups['vadj0_B']

    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['vadj' + str(lag) + '_B_ma'] = shift_df['vadj0_B_ma']

    print("Calculated {} values".format(len(result_df['vadj0_B_ma'].dropna())))
    return result_df

def calc_vadj_intra(intra_df):
    print("Calculating vadj intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating vadjC...")
    result_df['cur_log_ret'] = result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))
    result_df['bret_i'] = result_df[['cur_log_ret', 'pbeta', 'mkt_cap_y', 'giclose_ts']].groupby(['giclose_ts'], sort=False).apply(wavg2).reset_index(level=0)['pbeta']
    result_df['badjret_i'] = result_df['cur_log_ret'] - result_df['bret_i']

    result_df['dpvolume'] = result_df['dvolume'].astype(float) * result_df['dvwap']
    result_df['dpvolume_adj'] = result_df[['dpvolume_med_21', 'dpvolume', 'giclose_ts']].groupby('giclose_ts').apply(volmult_i).reset_index(level=0)['dpvolume']
    result_df['rv_i'] = result_df['dpvolume_adj'].astype(float) / result_df['dpvolume_med_21']

    # result_df['rv_i'] = (result_df['dpvolume_adj'] - result_df['dpvolume_med_21']) / result_df['dpvolume_std_21']

    result_df['vadjC'] = result_df['rv_i'] * np.sign(result_df['badjret_i'])
    result_df['vadjC_B'] = winsorize_by_ts(result_df['vadjC'])

    print("Calulating vadjC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['vadjC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['vadjC_B_ma'] = indgroups['vadjC_B']

    print("Calculated {} values".format(len(result_df['vadjC_B_ma'].dropna())))
    return result_df

def vadj_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['vadj_b'] = np.nan
    outsample_intra_df[ 'vadjC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'vadj' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df = regress_alpha(insample_intra_df, 'vadjC_B_ma', horizon, False, 'intra')
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "vadj_intra_"+name+"_" + df_dates(insample_intra_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    unstacked = outsample_intra_df[ ['ticker'] ].unstack()
    coefs = dict()
    coefs[1] = unstacked.between_time('09:30', '10:31').stack().index
    coefs[2] = unstacked.between_time('10:30', '11:31').stack().index
    coefs[3] = unstacked.between_time('11:30', '12:31').stack().index
    coefs[4] = unstacked.between_time('12:30', '13:31').stack().index
    coefs[5] = unstacked.between_time('13:30', '14:31').stack().index
    coefs[6] = unstacked.between_time('14:30', '15:59').stack().index
    print(fits_df.head(10))
    for ii in range(1,7):
        outsample_intra_df.ix[ coefs[ii], 'vadjC_B_ma_coef' ] = fits_df.ix['vadjC_B_ma'].ix[ii].ix['coef']
    
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'vadj0_B_ma', lag, False, 'daily') 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "vadj_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['vadj0_B_ma'].ix[horizon].ix['coef']
    print("Coef0: {}".format(coef0))
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['vadj0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'vadj'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df[ 'vadj_b'] = outsample_intra_df['vadjC_B_ma'] * outsample_intra_df['vadjC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'vadj_b'] += outsample_intra_df['vadj'+str(lag)+'_B_ma'] * outsample_intra_df['vadj'+str(lag)+'_B_ma_coef']
    
    return outsample_intra_df

def calc_vadj_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = calc_vadj_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_vadj_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    sector_name = "Energy"
    results = list()
    print("Running vadj for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    result_df = vadj_fits(sector_df, sector_intra_results_df, horizon, "in", middate)
    results.append(result_df)

    print("Running vadj excluding sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]
    result_df = vadj_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)
    results.append(result_df)

    result_df = pd.concat(results, verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='15Min')
    parser.add_argument("--horizon",action="store",dest="horizon",default=2)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.horizon)
    freq = args.freq
    pname = "./vadj_b" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)

    loaded = False
    try:        
        print("Looking " + pname+"_daily.h5")
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Could not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)    
        BARRA_COLS = ['ind1', 'pbeta']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close', 'overnight_log_ret', 'tradable_volume', 'tradable_med_volume_21', 'volat_21']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['close', 'dopen', 'dvolume', 'dvwap']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)
        daily_df = merge_barra_data(price_df, barra_df)
        intra_df = merge_intra_data(daily_df, intra_df)
        intra_df = calc_vol_profiles(intra_df)
        print("one")
        print(intra_df.columns)
        daily_df = merge_intra_eod(daily_df, intra_df)
        print("two")
        print(daily_df.columns)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    outsample_df = calc_vadj_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(outsample_df, 'vadj_b')
#    dump_all(outsample_df)

