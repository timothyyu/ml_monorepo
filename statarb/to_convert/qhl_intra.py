#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *

def calc_qhl_intra(intra_df):
    print("Calculating qhl intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating qhlC...")
    result_df['qhlC'] = result_df['iclose'] / np.sqrt(result_df['qhigh'] * result_df['qlow'])
    result_df['qhlC_B'] = winsorize_by_ts(result_df[ 'qhlC' ])

    print("Calulating qhlC_ma...")
    demean = lambda x: (x - x.mean())
    indgroups = result_df[['qhlC_B', 'giclose_ts', 'ind1']].groupby(['giclose_ts', 'ind1'], sort=True).transform(demean)
    result_df['qhlC_B_ma'] = indgroups['qhlC_B']
    
    print("Calculated {} values".format(len(result_df['qhlC_B_ma'].dropna())))
    return result_df

def qhl_fits(daily_df, intra_df, horizon, name, middate=None):
    insample_intra_df = intra_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['qhl_i'] = np.nan
    outsample_intra_df[ 'qhlC_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    fitresults_df = regress_alpha(insample_intra_df, 'qhlC_B_ma', horizon, True, 'intra_eod')
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "qhl_intra_"+name+"_" + df_dates(insample_intra_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    unstacked = outsample_intra_df[ ['ticker'] ].unstack()
    coefs = dict()
    coefs[1] = unstacked.between_time('09:30', '10:31').stack().index
    coefs[2] = unstacked.between_time('10:30', '11:31').stack().index
    coefs[3] = unstacked.between_time('11:30', '12:31').stack().index
    coefs[4] = unstacked.between_time('12:30', '13:31').stack().index
    coefs[5] = unstacked.between_time('13:30', '14:31').stack().index
    coefs[6] = unstacked.between_time('14:30', '15:59').stack().index
    print(fits_df.head())
    for ii in range(1,7):
        outsample_intra_df.ix[ coefs[ii], 'qhlC_B_ma_coef' ] = fits_df.ix['qhlC_B_ma'].ix[ii].ix['coef']
    
    outsample_intra_df[ 'qhl_i'] = outsample_intra_df['qhlC_B_ma'] * outsample_intra_df['qhlC_B_ma_coef']    
    return outsample_intra_df

def calc_qhl_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = daily_df
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)
    intra_results_df = calc_qhl_intra(intra_df)
    intra_results_df = merge_intra_data(daily_results_df, intra_results_df)

    sector_name = 'Energy'
    print("Running qhl for sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    result1_df = qhl_fits(sector_df, sector_intra_results_df, horizon, "in", middate)

    print("Running qhl for not sector {}".format(sector_name))
    sector_df = daily_results_df[ daily_results_df['sector_name'] != sector_name ]
    sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] != sector_name ]    
    result2_df = qhl_fits(sector_df, sector_intra_results_df, horizon, "ex", middate)    

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
    pname = "./qhl_i" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)
    freq = args.freq
    loaded = False
    try:
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Did not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback)
        BARRA_COLS = ['ind1']
        barra_df = load_barra(uni_df, start, end, BARRA_COLS)
        PRICE_COLS = ['close']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        DBAR_COLS = ['close', 'qhigh', 'qlow']
        intra_df = load_daybars(price_df[['ticker']], start, end, DBAR_COLS, freq)

        daily_df = merge_barra_data(price_df, barra_df)
        daily_df = merge_intra_eod(daily_df, intra_df)
        intra_df = merge_intra_data(daily_df, intra_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    result_df = calc_qhl_forecast(daily_df, intra_df, horizon, middate)
    dump_alpha(result_df, 'qhl_i')
