#!/usr/bin/env python 

from __future__ import print_function
from regress import *
from load_data_live import *
from loaddata import *
from util import *

from pandas.stats.moments import ewma

def wavg(group):
    b = group['pbeta']
    d = group['log_ret']
    w = group['mkt_cap_y'] / 1e6
    print("Mkt return: {} {}".format(group['gdate'], ((d * w).sum() / w.sum())))
    res = b * ((d * w).sum() / w.sum())
    return res


def calc_eps_daily(daily_df, horizon):
    print("Caculating daily eps...")
    result_df = filter_expandable(daily_df)

    print("Calculating eps0...")    
    #halflife = horizon / 2
#    result_df['dk'] = np.exp( -1.0 * halflife *  (result_df['gdate'] - result_df['last']).astype('timedelta64[D]').astype(int) )

    # result_df['bret'] = result_df[['log_ret', 'pbeta', 'mkt_cap_y', 'gdate']].groupby('gdate').apply(wavg).reset_index(level=0)['pbeta']
    # result_df['badjret'] = result_df['log_ret'] - result_df['bret']
    # result_df['badj0_B'] = winsorize_by_date(result_df[ 'badjret' ])

    # result_df['cum_ret'] = pd.rolling_sum(result_df['log_ret'], horizon)

    result_df['std_diff'] = result_df['EPS_std'].unstack().diff().stack()
    result_df.loc[ (result_df['std_diff'] <= 0) | (result_df['std_diff'].isnull()), 'EPS_diff_mean'] = 0
    result_df['eps0'] = result_df['EPS_diff_mean'] / result_df['EPS_median']

    # print result_df.columns
    # result_df['sum'] = result_df['EPS_median'] 
    # result_df['det_diff'] = (result_df['sum'].diff())
    # result_df['det_diff_sum'] = pd.rolling_sum( result_df['det_diff'], window=2)
    # #result_df['det_diff_dk'] = ewma(result_df['det_diff'], halflife=horizon )   
    # result_df['eps0'] = result_df['det_diff'] 

    # result_df['median'] = -1.0 * (result_df['median'] - 3)
    # result_df['med_diff'] = result_df['median'].unstack().diff().stack()
    # result_df['med_diff_dk'] = pd.rolling_sum( result_df['dk'] * result_df['med_diff'], window=horizon )
    # result_df['eps0'] = (np.sign(result_df['med_diff_dk']) * np.sign(result_df['cum_ret'])).clip(lower=0) * result_df['med_diff_dk']


    # demean = lambda x: (x - x.mean())
    # indgroups = result_df[['eps0', 'gdate', 'ind1']].groupby(['gdate', 'ind1'], sort=True).transform(demean)
    # result_df['eps0_ma'] = indgroups['eps0']

#    result_df['eps0_ma'] = result_df['eps0_ma'] * (np.sign(result_df['eps0_ma']) * np.sign(result_df['cum_ret']))

    result_df['eps0_ma'] = result_df['eps0']

    for lag in range(1,horizon+1):
        shift_df = result_df.unstack().shift(lag).stack()
        result_df['eps'+str(lag)+'_ma'] = shift_df['eps0_ma']

    return result_df

def generate_coefs(daily_df, horizon, name, coeffile=None):
    insample_daily_df = daily_df

    fits_df = pd.DataFrame(columns=['horizon', 'coef', 'indep', 'tstat', 'nobs', 'stderr'])
    for ii in range(1, horizon+1):
        fitresults_df = regress_alpha(insample_daily_df, 'eps0_ma', ii, False, 'daily', False) 
        fits_df = fits_df.append(fitresults_df, ignore_index=True) 
    fits_df.set_index(keys=['indep', 'horizon'], inplace=True)    

    coef0 = fits_df.ix['eps0_ma'].ix[horizon].ix['coef']
    print("Coef{}: {}".format(0, coef0))               
    coef_list = list()
    coef_list.append( { 'name': 'eps0_ma_coef', 'coef': coef0 } )
    for lag in range(1,horizon):
        coef = coef0 - fits_df.ix['eps0_ma'].ix[lag].ix['coef'] 
        print("Coef{}: {}".format(lag, coef))
        coef_list.append( { 'name': 'eps' + str(lag) + '_ma_coef', 'coef': coef } )

    coef_df = pd.DataFrame(coef_list)
    coef_df.to_csv(coeffile)

    return 

def eps_alpha(daily_df, horizon, name, coeffile):
    print("Loading coeffile: {}".format(coeffile))
    coef_df = pd.read_csv(coeffile, header=0, index_col=['name'])
    outsample_daily_df = daily_df
    outsample_daily_df['eps'] = 0.0

    coef0 = coef_df.ix['eps0_ma_coef'].ix['coef']
    print("Coef{}: {}".format(0, coef0))               
    outsample_daily_df[ 'eps0_ma_coef' ] = coef0
    for lag in range(0,horizon):
        coef = coef_df.ix[ 'eps'+str(lag)+'_ma_coef' ].ix['coef']
        outsample_daily_df[ 'eps'+str(lag)+'_ma_coef' ] = coef

    outsample_daily_df[ 'eps' ] = (outsample_daily_df['eps0_ma'].fillna(0) * outsample_daily_df['eps0_ma_coef']).fillna(0)
    print(outsample_daily_df['eps'].describe())
    for lag in range(1,horizon):
        outsample_daily_df[ 'eps'] += (outsample_daily_df['eps'+str(lag)+'_ma'].fillna(0) * outsample_daily_df['eps'+str(lag)+'_ma_coef']).fillna(0)
        print(outsample_daily_df['eps'].describe())
    
    return outsample_daily_df

def calc_eps_forecast(daily_df, horizon, coeffile, fit):
    daily_results_df = calc_eps_daily(daily_df, horizon) 


    if fit:
        forwards_df = calc_forward_returns(daily_df, horizon)
        daily_results_df = pd.concat( [daily_results_df, forwards_df], axis=1)

        generate_coefs( daily_results_df, horizon, "all", coeffile)
        return
    else:
        res = eps_alpha( daily_results_df, horizon, "all", coeffile)
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

    horizon = int(10)
    end = datetime.strptime(args.asof, "%Y%m%d")

    if args.fit:
        print("Fitting...")
        coeffile = args.coeffile + "/" + args.asof + ".eps.csv"
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
    analyst_df = load_estimate_hist(price_df[['ticker']], start, end, "EPS")
    daily_df = merge_daily_calcs(analyst_df, daily_df)

    result_df = calc_eps_forecast(daily_df, horizon, coeffile, args.fit)
    if not args.fit:
        dump_prod_alpha(result_df, 'eps', args.outputfile)



