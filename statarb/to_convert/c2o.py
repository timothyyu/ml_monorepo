#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def wavg(group):
    b = group['pbeta']
    d = group['overnight_log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res

def wavg2(group):
    b = group['pbeta']
    d = group['overnight_log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res

def wavg3(group):
    b = group['pbeta']
    d = group['cur_log_ret']
    w = group['mkt_cap_y'] / 1e6
    res = b * ((d * w).sum() / w.sum())
    return res


def calc_c2o_daily(daily_df, horizon):
    print("Caculating daily c2o...")
    result_df = filter_expandable(daily_df)

    print("Calculating c2o0...")
#    result_df['c2o0'] = result_df['overnight_log_ret'] / result_df['pbeta']
    result_df['bret'] = result_df[['overnight_log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['overnight_log_ret'] - result_df['bret']

   # result_df['c2o0_B'] = result_df['log_ret'] * (1 + np.abs(result_df['badjret'])) ** 3
    result_df['c2o0'] = result_df['badjret']
    result_df.ix[ np.abs(result_df['c2o0']) < .02 , 'c2o0'] = 0
    result_df['c2o0_B'] = winsorize_by_date(result_df['c2o0'])

    result_df = result_df.dropna(subset=['c2o0_B'])

    demean = lambda x: (x - x.mean())
    indgroups = result_df[['c2o0_B', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=False).transform(demean)
    result_df['c2o0_B_ma'] = indgroups['c2o0_B']
    
    print("Calulating lags...")
    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['c2o' + str(lag) + '_B_ma'] = shift_df['c2o0_B_ma']
    
    return result_df

def calc_c2o_intra(intra_df):
    print("Calculating c2o intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating c2oC...")
    result_df['cur_log_ret'] = np.log(result_df['iclose']/result_df['dopen'])
    result_df['bretC'] = result_df[['cur_log_ret', 'pbeta', 'mkt_cap_y', 'giclose_ts']].groupby(['giclose_ts'], sort=False).apply(wavg3).reset_index(level=0)['pbeta']
    result_df['badjretC'] = result_df['cur_log_ret'] - result_df['bretC']

    result_df['bret'] = result_df[['overnight_log_ret', 'pbeta', 'mkt_cap_y', 'giclose_ts']].groupby(['giclose_ts'], sort=False).apply(wavg2).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['overnight_log_ret'] - result_df['bret']

#    result_df['c2oC_B'] = result_df['badjretC'] * (1 + np.abs(result_df['badjret'])) ** 3 
    result_df['c2oC'] = result_df['badjret']
    result_df.ix[ np.abs(result_df['c2oC']) < .02 , 'c2oC'] = 0
    result_df['c2oC_B'] = winsorize_by_ts(result_df['c2oC'])
    result_df = result_df.dropna(subset=['c2oC_B'])

    print("Calulating c2oC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['c2oC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=False).transform(demean)
    result_df['c2oC_B_ma'] = indgroups['c2oC_B']

    return result_df

def c2o_fits(daily_df, intra_df, horizon, name, middate):
    # daily_df['dow'] = daily_df['gdate'].apply(lambda x: x.weekday())
    # daily_df['dow'] = daily_df['dow'].clip(0,1)
    # intra_df['dow'] = intra_df['date'].apply(lambda x: x.weekday())
    # intra_df['dow'] = intra_df['dow'].clip(0,1)
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['c2o'] = 0
    outsample_intra_df[ 'c2oC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'c2o' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])

    fitresults_df = regress_alpha(insample_intra_df, 'c2oC_B_ma', horizon, True, 'intra_eod')
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "c2o_intra_"+name+"_" + df_dates(insample_intra_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    
    unstacked = outsample_intra_df[ ['ticker'] ].unstack()
    coefs = dict()
    coefs[1] = unstacked.between_time('09:30', '10:31').stack().index
    coefs[2] = unstacked.between_time('10:30', '11:31').stack().index
    coefs[3] = unstacked.between_time('11:30', '12:31').stack().index
    coefs[4] = unstacked.between_time('12:30', '13:31').stack().index
    coefs[5] = unstacked.between_time('13:30', '14:31').stack().index
    coefs[6] = unstacked.between_time('14:30', '16:01').stack().index
    unstacked = None

    for ii in range(1,7):
        outsample_intra_df.ix[ coefs[ii], 'c2oC_B_ma_coef' ] = fits_df.ix['c2oC_B_ma'].ix[ii].ix['coef']

    #DAILY...
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for lag in range(1,horizon+1):
        print(insample_daily_df.head())
        fitresults_df = regress_alpha(insample_daily_df, 'c2o0_B_ma', lag, True, 'daily') 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "c2o_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    # for dow in range(0,2):       
    #     coef0 = fits_df.ix['c2o0_B_ma'].ix[horizon * 10 + dow].ix['coef']
    #     for lag in range(1,horizon):
    #         coef = coef0 - fits_df.ix['c2o0_B_ma'].ix[lag * 10 + dow].ix['coef'] 
    #         print "Coef{}: {}".format(lag, coef)
    #         dowidx = outsample_intra_df[ outsample_intra_df['dow'] == dow ].index
    #         outsample_intra_df.ix[ dowidx, 'c2o'+str(lag)+'_B_ma_coef' ] = coef

    coef0 = fits_df.ix['c2o0_B_ma'].ix[horizon].ix['coef']
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['c2o0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'c2o'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df[ 'c2o'] = outsample_intra_df['c2oC_B_ma'] * outsample_intra_df['c2oC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'c2o'] += outsample_intra_df['c2o'+str(lag)+'_B_ma'] * outsample_intra_df['c2o'+str(lag)+'_B_ma_coef']

    return outsample_intra_df

def calc_c2o_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = calc_c2o_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)    
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_c2o_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    #    sector_name = 'Energy'
    #    print "Running c2o for sector {}".format(sector_name)
    #    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]

    results = list()
    for sector_name in daily_results_df['sector_name'].dropna().unique():
        print("Running c2o for sector {}".format(sector_name))
        sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
        sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
        result_df = c2o_fits(sector_df, sector_intra_results_df, horizon, sector_name, middate)
        results.append(result_df)

    # sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    # sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]
    # result2_df = c2o_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)
  
    result_df = pd.concat(results, verify_integrity=True)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--horizon",action="store",dest="horizon",default=1)
    parser.add_argument("--freq",action="store",dest="freq",default='15Min')
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    freq = args.freq
    horizon = int(args.horizon)
    pname = "./c2o" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)

    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1', 'pbeta']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close', 'overnight_log_ret', 'tradable_volume', 'tradable_med_volume_21']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        daily_df = merge_barra_data(price_df, barra_df)
        DBAR_COLS = ['close', 'dopen', 'dvolume']
        daybar_df = load_daybars(price_df[ ['ticker'] ], start, end, DBAR_COLS, freq)
        intra_df = merge_intra_data(daily_df, daybar_df)
        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    outsample_df = calc_c2o_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(outsample_df, 'c2o')
#    dump_all(outsample_df)
