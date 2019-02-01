#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from loaddata import *
from util import *
from calc import *

from sklearn.decomposition import PCA

COMPONENTS = 4
CORR_LOOKBACK = 20

def calc_pca_intra(intra_df):
    print("Calculating pca intra...")
    result_df = filter_expandable(intra_df)

    result_df['iclose_l'] = result_df['iclose'].shift(1)
    result_df['logret'] = np.log(result_df['iclose']/result_df['iclose_l'])

    unstacked_rets_df = result_df[['logret']].unstack()
    unstacked_rets_df = unstacked_rets_df.replace([np.inf, -np.inf], np.nan)
    unstacked_rets_df = unstacked_rets_df.fillna(0)

    corr_matrices = pd.rolling_corr_pairwise(unstacked_rets_df, 10)

    pca = PCA(n_components=COMPONENTS)
    lastpcafit = None

    for dt, grp in result_df.groupby(level='iclose_ts'):
        df = corr_matrices.xs(dt, axis=0)
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)

        rets = unstacked_rets_df.xs(dt)
        ids = rets.index.droplevel(0)
        df = df[ ids ].ix[ ids ]

        try:
            pcafit =  pca.fit(np.asarray(df))
        except:
            pcafit = lastpcafit
        print("PCA explained variance {}: {}".format(dt, pcafit.explained_variance_ratio_))
#        pcarets = pca.transform(rets)
#        pr = np.dot(pcarets, pcafit.components_)
#        resids = rets - pr.T.reshape(len(df))
#        result_df.ix[ grp.index, 'pcaC' ] = resids.values
        lastpcafit = pcafit

    print("Calulating pcaC_ma...")
    result_df['pcaC_B'] = winsorize_by_ts(result_df['pcaC'])
 #   demean = lambda x: (x - x.mean())
#    dategroups = result_df[['pcaC_B', 'giclose_ts']].groupby(['giclose_ts'], sort=False).transform(demean)
    result_df['pcaC_B_ma'] = result_df['pcaC_B']

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
    PRICE_COLS = ['close', 'overnight_log_ret']
    price_df = load_prices(uni_df, start, end, PRICE_COLS)
    DBAR_COLS = ['close', 'dvolume', 'dopen']
    daybar_df = load_daybars(price_df[ ['ticker'] ], start, end, DBAR_COLS, freq)
    intra_df = merge_intra_data(daily_df, daybar_df)
    intra_df = calc_pca_intra(intra_df)

 
