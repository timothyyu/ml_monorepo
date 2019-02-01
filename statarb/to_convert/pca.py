#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *
from calc import *

from sklearn.decomposition import PCA

COMPONENTS = 5
WINDOW = 30

cache = dict()

def calc_pca_daily(daily_df, horizon):

    print("Caculating daily pca...")
    result_df = filter_expandable(daily_df)

    print("Calculating pca0...")
    result_df['log_ret_B'] = winsorize_by_date(result_df['log_ret'])

    unstacked_rets_df = result_df[['log_ret']].unstack()
    unstacked_rets_df.columns = unstacked_rets_df.columns.droplevel(0)
    unstacked_rets_df = unstacked_rets_df.fillna(0)

    result_df['pca0'] = 0
    pca = PCA(n_components=COMPONENTS)
    last_sigma = 99999.0
    for ii in xrange(WINDOW, len(unstacked_rets_df)):
        window_df = unstacked_rets_df[ii-WINDOW:ii]
        dt = window_df.index.max()
        sids = result_df.xs(dt, level=0).index

        window_df = window_df.replace([np.inf, -np.inf], np.nan)
        window_df = window_df.fillna(0)
        cache[dt] = window_df

        std_df = window_df.copy()
        for col in std_df.columns:
            if col in sids:
                rets = winsorize(std_df[col])
                std_df[col] = (rets - rets.mean()) 
            else:
                del std_df[col]
                del window_df[col]

        std_df = std_df.replace([np.inf, -np.inf], np.nan)
        std_df = std_df.fillna(0)

        window_df = window_df.T
    
        pcafit =  pca.fit(np.asarray(std_df.T))


        actual = window_df.ix[:,WINDOW-1]        
        pcarets = pca.transform(window_df)
        pr = np.dot(pcarets, pcafit.components_)
        pr = pr[:,[WINDOW-1]].reshape(-1)
        predicted =  pd.Series(pr, index=actual.index)
        
        predicted_sigma = predicted.std()
        resids = actual - predicted
    
        # if predicted_sigma > .01:
        #     resids = resids * 0.0

        print("PCA explained variance {}: {} {}".format(dt, predicted_sigma, pcafit.explained_variance_ratio_))

        resids.index = result_df[ result_df['gdate'] == dt].index
        result_df.ix[ result_df[ result_df['gdate'] == dt].index , 'pca0'] = resids 

        last_sigma = predicted_sigma

    print(result_df['pca0'].describe())
    result_df['pca0_B'] = winsorize_by_date(result_df['pca0'])
#    dategroups = result_df[['pca0_B', 'gdate']].groupby(['gdate'], sort=False).transform(demean)
#    result_df['pca0_B_ma'] = dategroups['pca0_B']
    result_df['pca0_B_ma'] = result_df['pca0_B']
    print("Calculated {} values".format(len(result_df)))

    print("Calulating lags...")
    for lag in range(1,horizon):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['pca'+str(lag)+'_B_ma'] = shift_df['pca0_B_ma']

    return result_df

def calc_pca_intra(intra_df):
    print("Calculating pca intra...")
    result_df = filter_expandable(intra_df)

    print("Calulating pcaC...")
    result_df['dret'] = result_df['overnight_log_ret'] + (np.log(result_df['iclose']/result_df['dopen']))

    unstacked_rets_df = result_df[['dret']].unstack()
    unstacked_rets_df = unstacked_rets_df.replace([np.inf, -np.inf], np.nan)
    unstacked_rets_df = unstacked_rets_df.fillna(0)
    result_df['pcaC'] = 0

    pca = PCA(n_components=COMPONENTS)
    last_sigma = 99999.0
    for dt in cache.keys():
        window_df = cache[dt].T

        for ts in result_df[ result_df['gdate'] == dt ]['giclose_ts'].unique():
            today = unstacked_rets_df.ix[ts]
            today.index = today.index.droplevel(0)

            orig = result_df[ result_df['giclose_ts'] == ts ]
            today = today.ix[ orig.index.droplevel(0) ]            

            del window_df[window_df.columns.max()]
            window_df.index.name = 'sid'
            window_df = window_df.join(today, how='right')
            window_df = window_df.fillna(0)

            std_df = window_df.copy()
            for col in std_df.columns:
                rets = winsorize(std_df[col])
                std_df[col] = (rets - rets.mean()) 

            pcafit =  pca.fit(np.asarray(std_df))
#            print "PCA explained variance {}: {}".format(ts, pcafit.explained_variance_ratio_)
        
            actual = window_df.ix[:,WINDOW-1]        
            pcarets = pca.transform(window_df)
            pr = np.dot(pcarets, pcafit.components_)
            pr = pr[:,[WINDOW-1]].reshape(-1)
            predicted =  pd.Series(pr, index=actual.index)

            predicted_sigma = predicted.std()
            resids = actual - predicted

            # if predicted_sigma > .01:
            #     resids = resids * 0.0

            resids.index = result_df[ result_df['giclose_ts'] == ts].index
            result_df.ix[ result_df[ result_df['giclose_ts'] == ts].index , 'pcaC'] = resids 
            last_sigma = predicted_sigma

    print("Calulating pcaC_ma...")
    result_df['pcaC_B'] = winsorize_by_ts(result_df['pcaC'])
 #   demean = lambda x: (x - x.mean())
#    dategroups = result_df[['pcaC_B', 'giclose_ts']].groupby(['giclose_ts'], sort=False).transform(demean)
    result_df['pcaC_B_ma'] = result_df['pcaC_B']

    return result_df


def pca_fits(daily_df, intra_df, horizon, name, middate):
    insample_intra_df = intra_df
    insample_daily_df = daily_df
    outsample_intra_df = intra_df
    if middate is not None:
        insample_intra_df = intra_df[ intra_df['date'] < middate ]
        insample_daily_df = daily_df[ daily_df.index.get_level_values('date') < middate ]
        outsample_intra_df = intra_df[ intra_df['date'] >= middate ]

    outsample_intra_df['pca'] = np.nan
    outsample_intra_df[ 'pcaC_B_ma_coef' ] = np.nan
    for lag in range(1, horizon+1):
        outsample_intra_df[ 'pca' + str(lag) + '_B_ma_coef' ] = np.nan

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'], dtype=float)
    fitresults_df = regress_alpha(insample_intra_df, 'pcaC_B_ma', horizon, True, 'intra')
    fits_df = fits_df.append(fitresults_df, ignore_index=True)
    plot_fit(fits_df, "pca_intra_"+name+"_" + df_dates(insample_intra_df))
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
        outsample_intra_df.ix[ coefs[ii], 'pcaC_B_ma_coef' ] = fits_df.ix['pcaC_B_ma'].ix[ii].ix['coef']
    
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'], dtype=float)
    for lag in range(1,horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'pca0_B_ma', lag, True, 'daily') 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    plot_fit(fits_df, "pca_daily_"+name+"_" + df_dates(insample_daily_df))
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['pca0_B_ma'].ix[horizon].ix['coef']
#    outsample_intra_df[ 'pcaC_B_ma_coef' ] = coef0
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['pca0_B_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        outsample_intra_df[ 'pca'+str(lag)+'_B_ma_coef' ] = coef

    outsample_intra_df[ 'pca'] = outsample_intra_df['pcaC_B_ma'] * outsample_intra_df['pcaC_B_ma_coef']
    for lag in range(1,horizon):
        outsample_intra_df[ 'pca'] += outsample_intra_df['pca'+str(lag)+'_B_ma'] * outsample_intra_df['pca'+str(lag)+'_B_ma_coef']
    
    return outsample_intra_df

def calc_pca_forecast(daily_df, intra_df, horizon, middate):
    daily_results_df = daily_df
    intra_results_df = intra_df

    # results = list()
    # for sector_name in daily_results_df['sector_name'].unique():
    #     print "Running pca for sector {}".format(sector_name)
    #     sector_df = daily_results_df[ daily_results_df['sector_name'] == sector_name ]
    #     sector_intra_results_df = intra_results_df[ intra_results_df['sector_name'] == sector_name ]
    #     result_df = pca_fits(sector_df, sector_intra_results_df, horizon, sector_name, middate)
    #     results.append(result_df)

#    result_df = pd.concat(results)

    result_df = pca_fits(daily_results_df, intra_results_df, horizon, "", middate)
    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--mid",action="store",dest="mid",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='30Min')
    parser.add_argument("--horizon",action="store",dest="horizon",default=3)
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    freq = args.freq
    horizon = int(args.horizon)
    pname = "./pca" + start + "." + end
    start = dateparser.parse(start)
    end = dateparser.parse(end)
    middate = dateparser.parse(args.mid)

    loaded = False
    try:        
        daily_df = pd.read_hdf(pname+"_daily.h5", 'table')
        intra_df = pd.read_hdf(pname+"_intra.h5", 'table')
        loaded = True
    except:
        print("Could not load cached data...")

    if not loaded:
        uni_df = get_uni(start, end, lookback, 1200)
        barra_df = load_barra(uni_df, start, end)    
        barra_df = transform_barra(barra_df)
        PRICE_COLS = ['close', 'overnight_log_ret']
        price_df = load_prices(uni_df, start, end, PRICE_COLS)
        daily_df = merge_barra_data(price_df, barra_df)
        DBAR_COLS = ['close', 'dvolume', 'dopen']
        daybar_df = load_daybars(price_df[ ['ticker'] ], start, end, DBAR_COLS, freq)
        intra_df = merge_intra_data(daily_df, daybar_df)

        daily_df.to_hdf(pname+"_daily.h5", 'table', complib='zlib')
        intra_df.to_hdf(pname+"_intra.h5", 'table', complib='zlib')

    daily_df = calc_pca_daily(daily_df, horizon) 
    forwards_df = calc_forward_returns(daily_df, horizon)
    daily_df = pd.concat( [daily_df, forwards_df], axis=1)
    intra_df = calc_pca_intra(intra_df)
    intra_df = merge_intra_data(daily_df, intra_df)
    full_df = calc_pca_forecast(daily_df, intra_df, horizon, middate)

    dump_alpha(full_df, 'pca')
