#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *
from calc import *

from sklearn.decomposition import PCA

COMPONENTS = 4
CORR_LOOKBACK = 20

def calc_pca_daily(daily_df):
    print("Caculating daily pca...")
    result_df = filter_expandable(daily_df)

    demean = lambda x: (x - x.mean())
    # result_df['log_ret_B'] = winsorize_by_date(result_df['log_ret'])
    # dategroups = result_df[['log_ret_B', 'gdate']].groupby(['gdate'], sort=False).transform(demean)
    # result_df['log_ret_B_ma'] = dategroups['log_ret_B']
    # result_df['log_ret_B_ma_l'] = result_df['log_ret_B_ma'].shift(1)

    result_df['yesterday_log_ret'] = result_df['today_log_ret'].shift(1)
    result_df['log_ret_B'] = winsorize_by_date(result_df['overnight_log_ret'] + result_df['yesterday_log_ret'])
    dategroups = result_df[['log_ret_B', 'gdate']].groupby(['gdate'], sort=False).transform(demean)
    result_df['log_ret_B_ma'] = dategroups['log_ret_B']

    
    # unstacked_df = result_df[['log_ret_B_ma_l']].unstack()
    # unstacked_df.columns = unstacked_df.columns.droplevel(0)
    # unstacked_df = unstacked_df.fillna(0)

    unstacked_overnight_df = result_df[['log_ret_B_ma']].unstack()
    unstacked_overnight_df.columns = unstacked_overnight_df.columns.droplevel(0)
    unstacked_overnight_df = unstacked_overnight_df.fillna(0)

    corr_matrices = rolling_ew_corr_pairwise(unstacked_overnight_df, 5)

    pca = PCA(n_components=COMPONENTS)
    lastpcafit = None
    for dt, grp in result_df.groupby(level='date'):
        df = corr_matrices.xs(dt, axis=0)
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
 #       rets = unstacked_rets_df.xs(dt)
        print("Average correlation: {} {} {}".format(dt, df.unstack().mean(), df.unstack().std()))
        try:
            pcafit =  pca.fit(np.asarray(df))
        except:
            pcafit = lastpcafit
        print("PCA explained variance {}: {}".format(dt, pcafit.explained_variance_ratio_))

#        pcarets = pca.transform(rets)
#        pr = np.dot(pcarets, pcafit.components_)
#        resids = rets - pr.T.reshape(len(df))
#        result_df.ix[ grp.index, 'pca0' ] = resids.values
        lastpcafit = pcafit

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--start",action="store",dest="start",default=None)
    parser.add_argument("--end",action="store",dest="end",default=None)
    parser.add_argument("--freq",action="store",dest="freq",default='5Min')
    args = parser.parse_args()
    
    start = args.start
    end = args.end
    lookback = 30
    freq = args.freq
    start = dateparser.parse(start)
    end = dateparser.parse(end)

    uni_df = get_uni(start, end, lookback, 1200)
    PRICE_COLS = ['close', 'overnight_log_ret', 'today_log_ret']
    price_df = load_prices(uni_df, start, end, PRICE_COLS)
    result_df = calc_pca_daily(price_df)

 
