#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from load_data_live import *
from loaddata import *
from util import *

from pandas.stats.moments import ewma

ESTIMATE = "SAL"

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    print("Mkt return: {} {}".format(group['gdate'], ((d * w).sum() / w.sum())))
    res = b * ((d * w).sum() / w.sum())
    return res


def calc_sal_daily(daily_df, horizon):
    print("Caculating daily sal...")
    result_df = filter_expandable(daily_df)

    print("Calculating sal0...")    
    halflife = horizon / 2
#    result_df['dk'] = np.exp( -1.0 * halflife *  (result_df['gdate'] - result_df['last']).astype('timedelta64[D]').astype(int) )

    result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    result_df['badjret'] = result_df['log_ret'] - result_df['bret']
    result_df['badj0_B'] = winsorize_by_date(result_df[ 'badjret' ])

    result_df['cum_ret'] = pd.rolling_sum(result_df['log_ret'], horizon)

    print(result_df[ESTIMATE + '_diff_mean'].describe())
    result_df['std_diff'] = result_df[ESTIMATE + '_std'].unstack().diff().stack()
    result_df.loc[ result_df['std_diff'] <= 0, ESTIMATE + '_diff_mean'] = 0
    result_df['sal0'] = result_df[ESTIMATE + '_diff_mean'] / result_df[ESTIMATE + '_median']

    # print result_df.columns
    # result_df['sum'] = result_df['SAL_median'] 
    # result_df['det_diff'] = (result_df['sum'].diff())
    # result_df['det_diff_sum'] = pd.rolling_sum( result_df['det_diff'], window=2)
    # #result_df['det_diff_dk'] = ewma(result_df['det_diff'], halflife=horizon )   
    # result_df['sal0'] = result_df['det_diff'] 

    # result_df['median'] = -1.0 * (result_df['median'] - 3)
    # result_df['med_diff'] = result_df['median'].unstack().diff().stack()
    # result_df['med_diff_dk'] = pd.rolling_sum( result_df['dk'] * result_df['med_diff'], window=horizon )
    # result_df['sal0'] = (np.sign(result_df['med_diff_dk']) * np.sign(result_df['cum_ret'])).clip(lower=0) * result_df['med_diff_dk']


    # demean = lambda x: (x - x.mean())
    # indgroups = result_df[['sal0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    # result_df['sal0_ma'] = indgroups['sal0']

#    result_df['sal0_ma'] = result_df['sal0_ma'] - result_df['sal0_ma'].dropna().mean()

#    result_df['sal0_ma'] = result_df['sal0_ma'] * (np.sign(result_df['sal0_ma']) * np.sign(result_df['cum_ret']))

    result_df['sal0_ma'] = result_df['sal0']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['sal'+str(lag)+'_ma'] = shift_df['sal0_ma']

    return result_df

def generate_coefs(daily_df, horizon, name, coeffile=None, intercepts=None):
    insample_daily_df = daily_df

    insample_up_df = insample_daily_df[ insample_daily_df[ESTIMATE + "_diff_mean"] > 0 ]
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr', 'intercept'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_up_df, 'sal0_ma', ii, False, 'daily', True) 
        print("INTERCEPT {} {}".format(ii, intercepts[ii]))
        fitresults_df['intercept'] = fitresults_df['intercept'] - float(intercepts[ii])
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    coef0 = fits_df.ix['sal0_ma'].ix[horizon].ix['coef']
    intercept0 = fits_df.ix['sal0_ma'].ix[horizon].ix['intercept']
    coef_list = list()
    coef_list.append( { 'name': 'tgt0_ma_coef', 'group': "up", 'coef': coef0 } )
    coef_list.append( { 'name': 'tgt0_ma_intercept', 'group': 'up', 'coef': intercept0 } )
    print("Coef{}: {}".format(0, coef0))               
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['sal0_ma'].ix[lag].ix['coef'] 
        intercept = intercept0 - fits_df.ix['sal0_ma'].ix[lag].ix['intercept'] 
        print("Coef{}: {}".format(lag, coef))
        coef_list.append( { 'name': 'sal' + str(lag) + '_ma_coef', 'group': "up", 'coef': coef } )
        coef_list.append( { 'name': 'sal' + str(lag) + '_ma_intercept', 'group': "up", 'coef': intercept } )

    insample_dn_df = insample_daily_df[ insample_daily_df[ESTIMATE + "_diff_mean"] <= 0 ]
    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr', 'intercept'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_dn_df, 'sal0_ma', ii, False, 'daily', True) 
        fitresults_df['intercept'] = fitresults_df['intercept'] - intercepts[ii]
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    
    coef0 = fits_df.ix['sal0_ma'].ix[horizon].ix['coef']
    intercept0 = fits_df.ix['sal0_ma'].ix[horizon].ix['intercept']
    coef_list.append( { 'name': 'tgt0_ma_coef', 'group': "dn", 'coef': coef0 } )
    coef_list.append( { 'name': 'tgt0_ma_intercept', 'group': 'dn', 'coef': intercept0 } )

    print("Coef{}: {}".format(0, coef0))               
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['sal0_ma'].ix[lag].ix['coef'] 
        intercept = intercept0 - fits_df.ix['sal0_ma'].ix[lag].ix['intercept'] 
        print("Coef{}: {}".format(lag, coef))
        coef_list.append( { 'name': 'sal' + str(lag) + '_ma_coef', 'group': "dn", 'coef': coef } )
        coef_list.append( { 'name': 'sal' + str(lag) + '_ma_intercept', 'group': "dn", 'coef': intercept } )


    coef_df = pd.DataFrame(coef_list)
    coef_df.to_csv(coeffile)

    return

def sal_alpha(daily_df, horizon, name, coeffile):
    coef_df = pd.read_csv(coeffile, header=0, index_col=['name', 'group'])
    outsample_daily_df = daily_df
    outsample_daily_df['sal'] = 0.0

    coef0 = coef_df.ix['sal0_ma_coef'].ix["up"].ix['coef']
    intercept0 = coef_df.ix['sal0_ma_intercept'].ix["up"].ix['coef']
    print("Coef{}: {}".format(0, coef0))               
    outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] > 0, 'sal0_ma_coef' ] = coef0
    outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] > 0, 'sal0_ma_intercept' ] =  intercept0
    for lag in range(1,horizon):
        coef = coef_df.ix['sal' + str(lag) + '0_ma_coef'].ix["up"].ix['coef']
        intercept = coef_df.ix['sal' + str(lag) + '_ma_intercept'].ix["up"].ix['coef']
        outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] > 0, 'sal'+str(lag)+'_ma_coef' ] = coef
        outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] > 0, 'sal'+str(lag)+'_ma_intercept' ] = intercept

    coef0 = coef_df.ix['sal0_ma_coef'].ix["dn"].ix['coef']
    intercept0 = coef_df.ix['sal0_ma_intercept'].ix["dn"].ix['coef']
    print("Coef{}: {}".format(0, coef0))               
    outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] <= 0, 'sal0_ma_coef' ] = coef0
    outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] <= 0, 'sal0_ma_intercept' ] =  intercept0
    for lag in range(1,horizon):
        coef = coef_df.ix['sal' + str(lag) + '0_ma_coef'].ix["dn"].ix['coef']
        intercept = coef_df.ix['sal' + str(lag) + '_ma_intercept'].ix["dn"].ix['coef']
        print("Coef{}: {}".format(lag, coef))
        outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] <= 0, 'sal'+str(lag)+'_ma_coef' ] = coef
        outsample_daily_df.loc[ outsample_daily_df[ESTIMATE + '_diff_mean'] <= 0, 'sal'+str(lag)+'_ma_intercept' ] = intercept


    outsample_daily_df[ 'sal' ] = (outsample_daily_df['sal0_ma'].fillna(0) * outsample_daily_df['sal0_ma_coef'] + outsample_daily_df['sal0_ma_intercept']).fillna(0)
    for lag in range(1,horizon):
        outsample_daily_df[ 'sal'] += (outsample_daily_df['sal'+str(lag)+'_ma'].fillna(0) * outsample_daily_df['sal'+str(lag)+'_ma_coef'] + outsample_daily_df['sal'+str(lag)+'_ma_intercept']).fillna(0)
    
    return outsample_daily_df

def calc_sal_forecast(daily_df, horizon, coeffile, fit):
    daily_results_df = calc_sal_daily(daily_df, horizon) 

    if fit:
        forwards_df = calc_forward_returns(daily_df, horizon)
        daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

        intercept_d = get_intercept(daily_results_df, horizon, 'sal0_ma')
        generate_coefs( daily_results_df, horizon, "all", coeffile, intercept_d)
        return
    else:
        res = sal_alpha( daily_results_df, horizon, "all", coeffile)
        result_df = pd.concat([res], verify_integrity=True)

    return result_df

if __name__=="__main__":            
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--asof",action="store",dest="asof",default=None)
    parser.add_argument("--inputfile",action="store",dest="inputfile",default=None)
    parser.add_argument("--outputfile",action="store",dest="outputfile",default=None)
    parser.add_argument("--logfile",action="store",dest="logfile",default=None)
    parser.add_argument("--coeffile",action="store",dest="coeffile",default=None)
    parser.add_argument("--fit",action="store",dest="fit",default=False)
    args = parser.parse_args()

    horizon = int(20)
    end = datetime.strptime(args.asof, "%Y%m%d")

    if args.fit:
        print("Fitting...")
        coeffile = args.coeffile + "/" + args.asof + ".sal.csv"
        lookback = timedelta(days=720)    
        start = end - lookback
        uni_df = get_uni(start, end, 30)
    else:
        print("Not fitting...")
        coeffile = args.coeffile
        lookback = timedelta(days=horizon+5)    
        start = end - lookback
        uni_df = load_live_file(args.inputfile)
        end = datetime.strptime(args.asof + '_' + uni_df['time'].min(), '%Y%m%d_%H:%M:%S')
    
    print("Running between {} and {}".format(start, end))

    BARRA_COLS = ['ind1', 'pbeta']
    barra_df = load_barra(uni_df, start, end, BARRA_COLS)
    PRICE_COLS = ['close']
    price_df = load_prices(uni_df, start, end, PRICE_COLS)

    daily_df = merge_barra_data(price_df, barra_df)
    analyst_df = load_estimate_hist(price_df[['ticker']], start, end, "SAL")
    daily_df = merge_daily_calcs(analyst_df, daily_df)

    
    result_df = calc_sal_forecast(daily_df, horizon, coeffile, args.fit)
    if not args.fit:
        dump_prod_alpha(result_df, 'sal', args.outputfile)


