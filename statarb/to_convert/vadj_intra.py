#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
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

def calc_vadj_intra(intra_df):
    print("Calculating vadj intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating vadjC...")
    result_df['cur_log_ret'] = result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))
#    result_df['c2c_badj'] = result_df['cur_log_ret'] / result_df['pbeta']
    result_df['bret'] = result_df[['cur_log_ret', 'pbeta', 'mkt_cap_y', 'giclose_ts']].groupby(['giclose_ts'], sort=False).apply(wavg2).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['cur_log_ret'] - result_df['bret']
    result_df['rv_i'] = (result_df['dvolume'].astype(float) * result_df['dvwap']) / result_df['dpvolume_med_21']
    result_df['vadjC'] = result_df['rv_i'] * np.sign(result_df['badjret'])
    result_df['vadjC_B'] = winsorize_by_ts(result_df['vadjC'])

    print("Calulating vadjC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['vadjC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['vadjC_B_ma'] = indgroups['vadjC_B']

    print("Calculated {} values".format(len(result_df['vadjC_B_ma'].dropna())))
    return result_df

def vadj_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['vadj_i'] = np.nan
    outsample_intra_df[ 'vadjC_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df = regress_alpha(insample_intra_df, 'vadjC_B_ma', horizon, True, 'intra_eod')
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
    
    outsample_intra_df[ 'vadj_i'] = outsample_intra_df['vadjC_B_ma'] * outsample_intra_df['vadjC_B_ma_coef']
    
    return outsample_intra_df

def calc_vadj_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = daily_df
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_vadj_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    sector_name = 'Energy'
    print("Running vadj for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    result1_df = vadj_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)

    print("Running vadj for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]
    result2_df = vadj_fits(sector_df, sector_intra_results_df, horizon, "in", middate)

    result_df = pd.concat([result1_df, result2_df], verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='15Min')
    parser.add_argument("--horizon",action="store",dest="horizon",default=0)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    horizon = int(args.horizon)
    freq = args.freq
    pname = "./vadj_i" + start + "." + end
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
        PRICE_COLS = ['close', 'overnight_log_ret', 'tradable_volume', 'tradable_med_volume_21']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['dclose', 'dopen', 'dvolume', 'dvwap', 'dpvolume_med_21']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)
        daily_df = merge_barra_data(price_df, barra_df)
        intra_df = merge_intra_data(daily_df, intra_df)
        intra_df = calc_vol_profiles(intra_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    outsample_df = calc_vadj_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(outsample_df, 'vadj_i')
#    dump_all(outsample_df)

