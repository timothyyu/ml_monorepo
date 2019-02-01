import opt
from calc import *
from loaddata import *
import argparse


def pnl_sum(group):
    cum_pnl = ((np.exp(group['cum_log_ret_i_now'] - group['cum_log_ret_i_then']) - 1) * group['position_then']).fillna(
        0).sum()
    return cum_pnl


parser = argparse.ArgumentParser()
parser.add_argument("--start")
parser.add_argument("--end")
parser.add_argument("--fcast", help="alpha signals, formatted as 'name1:mult1:weight1,name2:mult2:weight2,...'")
parser.add_argument("--horizon", default=3)
parser.add_argument("--mult", default=1.0)
parser.add_argument("--vwap", default=False)
parser.add_argument("--maxiter", default=1500)
parser.add_argument("--kappa", default=2.0e-8)
parser.add_argument("--slip_nu", default=.18)
parser.add_argument("--slip_beta", default=.6)
parser.add_argument("--fast", default=False)
parser.add_argument("--exclude")
parser.add_argument("--earnings")
parser.add_argument("--locates",default="True")
parser.add_argument("--maxnot", default=200e6)
parser.add_argument("--maxdollars", default=1e6)
parser.add_argument("--maxforecast", default=0.0050)
parser.add_argument("--nonegutil", default=True)
parser.add_argument("--daily", default=False)
parser.add_argument("--dir", help="the root directory", default='.')
args = parser.parse_args()

print(args)

ALPHA_MULT = float(args.mult)
horizon = int(args.horizon)
start = args.start
end = args.end
data_dir = args.dir + "/data"

factors = ALL_FACTORS
max_forecast = float(args.maxforecast)
max_adv = 0.02
max_dollars = float(args.maxdollars)
participation = 0.015
opt.min_iter = 50
opt.max_iter = int(args.maxiter)
opt.kappa = float(args.kappa)  # 4.3e-7
opt.max_sumnot = float(args.maxnot)
opt.max_expnot = 0.04
opt.max_trdnot = 0.5
opt.slip_alpha = 1.0
opt.slip_delta = 0.25
opt.slip_beta = float(args.slip_beta)  # 0.6
opt.slip_gamma = 0  # 0.3
opt.slip_nu = float(args.slip_nu)  # 0.14
opt.execFee = 0.00015
opt.num_factors = len(factors)

# original cols = ['ticker', 'close', 'tradable_volume', 'bvwap_b', 'tradable_med_volume_21', 'mdvp', 'overnight_log_ret', 'date', 'log_ret', 'volume', 'capitalization', 'cum_log_ret', 'srisk_pct', 'dpvolume_med_21', 'volat_21_y', 'mkt_cap_y', 'cum_log_ret_y', 'open', 'close_y', 'indname1', 'barraResidRet', 'split', 'div', 'gdate', 'rating_mean_z']
cols = ['symbol', 'close', 'volume', 'med_volume_21', 'mdvp', 'overnight_log_ret', 'log_ret', 'volat_21', 'mkt_cap',
        'open', 'ind1', 'split', 'div', 'sedol']
cols.extend(BARRA_FACTORS)
# cols.extend( BARRA_INDS )
# cols.extend( INDUSTRIES )

forecasts = []
forecastargs = args.fcast.split(',')
for fcast in forecastargs:
    name, mult, weight = fcast.split(":")
    forecasts.append(name)

factor_df = load_factor_cache(dateparser.parse(start), dateparser.parse(end), data_dir)
pnl_df = load_cache(dateparser.parse(start), dateparser.parse(end), data_dir, cols)
# print(pnl_df.xs(10027954, level=1)['indname1'])
pnl_df = pnl_df.truncate(before=dateparser.parse(start), after=dateparser.parse(end))
pnl_df.index.names = ['date', 'gvkey']
pnl_df['forecast'] = np.nan
pnl_df['forecast_abs'] = np.nan
for fcast in forecastargs:
    print("Loading {}".format(fcast))
    name, mult, weight = fcast.split(":")
    mu_df = load_mus(data_dir, name, start, end)
    pnl_df = pd.merge(pnl_df, mu_df, how='left', left_index=True, right_index=True)

# daily_df = pnl_df.unstack().between_time('15:30', '15:30').stack()
# daily_df = pnl_df.unstack().between_time('15:45', '15:45').stack()
# daily_df = daily_df.dropna(subset=['date']).reset_index().set_index(['date', 'gvkey'])

# daily_df = create_z_score(daily_df, 'srisk_pct')

daily_df = pnl_df

if args.locates != "None":
    locates_df = load_locates(daily_df[['sedol','symbol']], dateparser.parse(start), dateparser.parse(end), data_dir)
    daily_df = pd.merge(daily_df, locates_df, on=['date', 'gvkey'], suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)
    locates_df = None
    '''
    test_df = daily_df.sort_values(['date','mkt_cap'],ascending=False).groupby(level='date',group_keys=False).head(1500)
    test_df = test_df[test_df['borrow_qty']==0]
    missed = test_df.xs('2013-01-03',level=0,drop_level=False)
    missed[['symbol','sedol']].to_csv(r"%smissing_borrow.csv" % "./", "|")
    '''

if args.earnings is not None:
    earnings_df = load_earnings_dates(daily_df[['symbol']], dateparser.parse(start), dateparser.parse(end))
    daily_df = pd.merge(daily_df, earnings_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)
    earnings_df = load_past_earnings_dates(daily_df[['symbol']], dateparser.parse(start), dateparser.parse(end))
    daily_df = pd.merge(daily_df, earnings_df, how='left', left_index=True, right_index=True, suffixes=['', '_dead'])
    daily_df = remove_dup_cols(daily_df)
    earnings_df = None

# daily_df = transform_barra(daily_df)
pnl_df = pd.merge(pnl_df.reset_index(), daily_df.reset_index(), how='left', on=['date', 'gvkey'],
                  suffixes=['', '_dead'])
pnl_df = remove_dup_cols(pnl_df)
pnl_df.set_index(['date', 'gvkey'], inplace=True)

resid_df, factor_df = calc_factors(daily_df)
# daily_df['residVol'] = horizon * (calc_resid_vol(pnl_df) / 100.0) / np.sqrt(252.0) we dont have barraResidRet

factor_df = calc_factor_vol(factor_df)
pnl_df = pd.merge(pnl_df, daily_df, how='left', on=['date', 'gvkey'], suffixes=['', '_dead'])
pnl_df = remove_dup_cols(pnl_df)

pnl_df['residVol'] = resid_df['barraResidRet'].groupby(level='gvkey').apply(
    lambda x: x.rolling(20).std())
# pnl_df['residVol'] = horizon * (pnl_df['srisk_pct'] / 100.0) / np.sqrt(252.0)

pnl_df['volume_d'] = pnl_df['volume'].groupby(level='gvkey').diff()
pnl_df.loc[pnl_df['volume_d'] < 0, 'volume_d'] = pnl_df['volume']
pnl_df = push_data(pnl_df, 'volume_d')
# pnl_df = push_data(pnl_df, 'bvwap_b')

# MIX FORECASTS
pnl_df['forecast'] = 0
for fcast in forecastargs:
    name, mult, weight = fcast.split(":")
    pnl_df[name + '_adj'] = pnl_df[name] * float(mult) * float(weight)
    pnl_df['forecast'] += pnl_df[name + '_adj'].fillna(0)

pnl_df['forecast'] = (ALPHA_MULT * pnl_df['forecast']).clip(-max_forecast, max_forecast)
pnl_df['forecast_abs'] = np.abs(pnl_df['forecast'])
pnl_df['max_trade_shares'] = pnl_df['volume_d_n'] * participation

pnl_df['position'] = 0
pnl_df['traded'] = 0
pnl_df['target'] = 0
pnl_df['dutil'] = 0
pnl_df['dsrisk'] = 0
pnl_df['dfrisk'] = 0
pnl_df['dmu'] = 0
pnl_df['eslip'] = 0
pnl_df['cum_pnl'] = 0

pnl_df['max_notional'] = (pnl_df['med_volume_21'] * pnl_df['close'] * max_adv).clip(0, max_dollars)
pnl_df['min_notional'] = (-1 * pnl_df['med_volume_21'] * pnl_df['close'] * max_adv).clip(-max_dollars, 0)

if args.locates != "None":
    pnl_df['borrow_notional'] = pnl_df['borrow_qty'] * pnl_df['close']
    pnl_df['min_notional'] = pnl_df[['borrow_notional', 'min_notional']].max(axis=1)
    pnl_df.ix[pnl_df['fee'] > 0, 'min_notional'] = 0

last_pos = pd.DataFrame(pnl_df.reset_index()['gvkey'].unique(), columns=['gvkey'])
last_pos['shares_last'] = 0
last_pos = last_pos.set_index(['gvkey']).sort_index()

lastday = None

it = 0
groups = pnl_df.groupby(level='date')
pnl_df = None
daily_df = None
new_pnl_df = None
gc.collect()
b_index = pd.MultiIndex(levels=[[], []], labels=[[], []], names=['date', 'gvkey'])
blotter_df = pd.DataFrame(columns=['position', 'traded_shares', 'close'], index=b_index)
last_pnl = 0
daily_returns = []
for name, date_group in groups:
    dayname = name.strftime("%Y%m%d")
    if (int(dayname) < int(start)) or (int(dayname) > int(end)): continue

    hour = int(name.strftime("%H"))
    minute = int(name.strftime("%M"))
    if args.daily:
        if hour < 15 or minute < 30: continue

    if args.fast:
        minutes = int(name.strftime("%M"))
        if minutes != 30: continue

    if hour >= 16: continue

    print("\nLooking at {}".format(name))
    monthname = name.strftime("%Y%m")
    timename = name.strftime("%H%M%S")
    weekdayname = name.weekday()
    date_group = date_group[
        (date_group['close'] > 0) & (date_group['volume_d'] > 0) & (date_group['mdvp'] > 0)].sort_index()
    if len(date_group) == 0:
        print("No data for {}".format(name))
        continue

    date_group = pd.merge(date_group.reset_index(), last_pos.reset_index(), how='outer', left_on=['gvkey'],
                          right_on=['gvkey'], suffixes=['', '_last'])
    date_group['date'] = name
    date_group = date_group.dropna(subset=['gvkey'])
    date_group.set_index(['date', 'gvkey'], inplace=True)
    if lastday is not None and lastday != dayname:
        date_group['shares_last'] = date_group['shares_last'] * (date_group['split'].fillna(1))
    date_group['position_last'] = (date_group['shares_last'] * date_group['close']).fillna(0)
    # date_group.ix[ date_group['close'].isnull() | date_group['mdvp'].isnull() | (date_group['mdvp'] == 0) | date_group['volume_d'].isnull() | (date_group['volume_d'] == 0) | date_group['residVol'].isnull(), 'max_notional' ] = 0
    # date_group.ix[ date_group['close'].isnull() | date_group['mdvp'].isnull() | (date_group['mdvp'] == 0) | date_group['volume_d'].isnull() | (date_group['volume_d'] == 0) | date_group['residVol'].isnull(), 'min_notional' ] = 0

    # if args.exclude is not None:
    #     attr, val = args.exclude.split(":")
    #     val = float(val)
    #     date_group.ix[ date_group[attr] < val, 'forecast' ] = 0
    #     date_group.ix[ date_group[attr] < val, 'max_notional' ] = 0
    #     date_group.ix[ date_group[attr] < val, 'min_notional' ] = 0

    date_group.ix[(date_group['mkt_cap'] < 1.6e3) | (date_group['close'] > 500.0) | (
            date_group['ind1'] == 3520), 'forecast'] = 0  # indname1 == 'PHARMA'
    date_group.ix[(date_group['mkt_cap'] < 1.6e3) | (date_group['close'] > 500.0) | (
            date_group['ind1'] == 3520), 'max_notional'] = 0
    date_group.ix[(date_group['mkt_cap'] < 1.6e3) | (date_group['close'] > 500.0) | (
            date_group['ind1'] == 3520), 'min_notional'] = 0

    if args.earnings is not None:
        days = int(args.earnings)
        date_group.ix[date_group['daysToEarn'] == 3, 'residVol'] = date_group.ix[
                                                                       date_group['daysToEarn'] == 3, 'residVol'] * 1.5
        date_group.ix[date_group['daysToEarn'] == 2, 'residVol'] = date_group.ix[
                                                                       date_group['daysToEarn'] == 2, 'residVol'] * 2
        date_group.ix[date_group['daysToEarn'] == 1, 'residVol'] = date_group.ix[
                                                                       date_group['daysToEarn'] == 1, 'residVol'] * 3

        date_group.ix[((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                date_group['position_last'] >= 0), 'max_notional'] = date_group.ix[
            ((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                    date_group['position_last'] >= 0), 'position_last']
        date_group.ix[((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                date_group['position_last'] >= 0), 'min_notional'] = 0
        date_group.ix[((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                date_group['position_last'] <= 0), 'max_notional'] = 0
        date_group.ix[((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                date_group['position_last'] <= 0), 'min_notional'] = date_group.ix[
            ((date_group['daysToEarn'] <= days) | (date_group['daysFromEarn'] < days)) & (
                    date_group['position_last'] >= 0), 'position_last']

    # OPTIMIZATION
    opt.num_secs = len(date_group)
    opt.init()
    opt.sec_ind = date_group.reset_index().index.copy().values
    opt.sec_ind_rev = date_group.reset_index()['gvkey'].copy().values
    opt.g_positions = date_group['position_last'].copy().values
    opt.g_lbound = date_group['min_notional'].fillna(0).values
    opt.g_ubound = date_group['max_notional'].fillna(0).values
    opt.g_mu = date_group['forecast'].copy().fillna(0).values
    opt.g_rvar = date_group['residVol'].copy().fillna(0).values
    opt.g_advp = date_group['mdvp'].copy().fillna(0).values
    opt.g_price = date_group['close'].copy().fillna(0).values
    opt.g_advpt = (date_group['volume_d'] * date_group['close']).fillna(0).values
    opt.g_vol = date_group['volat_21'].copy().fillna(0).values * horizon
    opt.g_mktcap = date_group['mkt_cap'].copy().fillna(0).values

    print(date_group.xs(testid, level=1)[['forecast', 'min_notional', 'max_notional', 'position_last']])

    find = 0
    for factor in factors:
        opt.g_factors[find, opt.sec_ind] = date_group[factor].fillna(0).values
        find += 1

    find1 = 0
    for factor1 in factors:
        find2 = 0
        for factor2 in factors:
            try:
                factor_cov = factor_df[(factor1, factor2)].fillna(0).ix[pd.to_datetime(dayname)]
                #                factor1_sig = np.sqrt(factor_df[(factor1, factor1)].fillna(0).ix[pd.to_datetime(dayname)])
                #               factor2_sig = np.sqrt(factor_df[(factor2, factor2)].fillna(0).ix[pd.to_datetime(dayname)])
                #                print("Factor Correlation {}, {}: {}".format(factor1, factor2, factor_cov/(factor1_sig*factor2_sig)))
            except:
                #                print("No cov found for {} {}".format(factor1, factor2))
                factor_cov = 0

            opt.g_fcov[find1, find2] = factor_cov * horizon
            opt.g_fcov[find2, find1] = factor_cov * horizon

            find2 += 1
        find1 += 1
    try:
        (target, dutil, eslip, dmu, dsrisk, dfrisk, costs, dutil2, vol, price) = opt.optimize()
    except:
        date_group.to_csv("problem.csv")
        raise

    optresults_df = pd.DataFrame(index=date_group.index,
                                 columns=['target', 'dutil', 'eslip', 'dmu', 'dsrisk', 'dfrisk', 'costs', 'dutil2',
                                          'traded'])
    optresults_df['target'] = target
    optresults_df['dutil'] = dutil
    optresults_df['eslip'] = eslip
    optresults_df['dmu'] = dmu
    optresults_df['dsrisk'] = dsrisk
    optresults_df['dfrisk'] = dfrisk
    optresults_df['costs'] = costs
    optresults_df['dutil2'] = dutil2

    # pnl_df.ix[ date_group.index, 'target'] = optresults_df['target']
    # pnl_df.ix[ date_group.index, 'eslip'] = optresults_df['eslip']
    # pnl_df.ix[ date_group.index, 'dutil'] = optresults_df['dutil']
    # pnl_df.ix[ date_group.index, 'dsrisk'] = optresults_df['dsrisk']
    # pnl_df.ix[ date_group.index, 'dfrisk'] = optresults_df['dfrisk']
    # pnl_df.ix[ date_group.index, 'dmu'] = optresults_df['dmu']

    date_group['target'] = optresults_df['target']
    date_group['dutil'] = optresults_df['dutil']
    #    tmp = pd.merge(last_pos.reset_index(), date_group['forecast'].reset_index(), how='inner', left_on=['gvkey'], right_on=['gvkey'])
    #    date_group['last_position'] = tmp.set_index(['date', 'gvkey'])['position']

    if args.nonegutil:
        date_group.ix[date_group['dutil'] <= 0, 'target'] = date_group.ix[date_group['dutil'] <= 0, 'position_last']

    date_group['max_move'] = date_group['position_last'] + date_group['max_trade_shares'] * date_group['close']
    date_group['min_move'] = date_group['position_last'] - date_group['max_trade_shares'] * date_group['close']
    date_group['position'] = date_group['target']
    date_group['position'] = date_group[['position', 'max_move']].min(axis=1)
    date_group['position'] = date_group[['position', 'min_move']].max(axis=1)

    # df = date_group[ date_group['target'] > date_group['max_move']]
    # print(df[['max_move', 'min_move', 'target', 'position', 'max_trade_shares', 'position_last', 'volume_d_n']].head())
    # print(date_group.xs(10000108, level=1)[['max_move', 'min_move', 'target', 'position', 'max_trade_shares', 'position_last', 'volume_d_n']])

    date_group['traded'] = date_group['position'] - date_group['position_last']
    date_group['shares'] = date_group['position'] / date_group['close']

    # pnl_df.ix[ date_group.index, 'traded'] = date_group['traded']

    postmp = pd.merge(last_pos.reset_index(), date_group[['shares', 'close', 'position_last']].reset_index(),
                      how='outer', left_on=['gvkey'],
                      right_on=['gvkey']).set_index('gvkey')
    last_pos['shares_last'] = postmp['shares'].fillna(0)
    #    pnl_df.ix[ date_group.index, 'position'] = date_group['position']

    optresults_df['forecast'] = date_group['forecast']
    optresults_df['traded'] = date_group['traded']
    optresults_df['shares'] = date_group['shares']
    optresults_df['position'] = date_group['position']
    optresults_df['close'] = date_group['close']
    optresults_df.to_csv(data_dir + "/opt/opt." + "-".join(forecasts) + "." + dayname + "_" + timename + ".csv")

    date_group['traded_shares'] = date_group['shares'] - date_group['shares_last']
    blotter_df = blotter_df.append(date_group[['traded', 'traded_shares', 'close']])
    blotter_df['diff'] = blotter_df[['close']].groupby(level='date').apply(lambda x: postmp[['close']] - x)
    total_pnl = (blotter_df['diff'] * blotter_df['traded_shares']).fillna(0).sum()
    daily_pnl = total_pnl - last_pnl
    last_pnl = total_pnl
    daily_return = daily_pnl / postmp['position_last'].abs().sum()
    if lastday is not None:
        daily_returns.append(daily_return)
    print("date: %s" % name)
    print("daily_pnl: %.2f" % daily_pnl)
    print("daily_return: %.2f%%" % (daily_return*100))
    lastday = dayname
    it += 1
    #    groups.remove(name)
    date_group = None
    gc.collect()
annualized_days = len(daily_returns) / 252
annualized_return = (total_pnl / postmp['position_last'].abs().sum() + 1) ** (1 / annualized_days) - 1
annualized_volat = np.std(np.array(daily_returns)) * (1 / annualized_days) ** .5
# Sharpe is calculated assuming risk free rate of return is negligible
sharpe = annualized_return / annualized_volat
print("total_pnl: %.2f" % total_pnl)
print("annualized_return: %.2f%%" % (annualized_return * 100))
print("annualized_volat: %.2f%%" % (annualized_volat * 100))
print("sharpe: %.2f" % (sharpe))

print("Saving blotter fields...")
blotter_df = blotter_df[['traded']]
blotter_df['exec amount'] = blotter_df['traded'].abs()
blotter_df['action'] = np.where(blotter_df['traded'] > 0, 'BUY', 'SELL')
blotter_df[['exec amount','action']].to_csv(r"%s/blotter/blotter.csv" % (data_dir))

print("bsim done", args.fcast)

# pnl_df.to_csv("debug." + "-".join(forecasts) + "." + str(start) + "." + str(end) + ".csv")
# pnl_df.xs(testid, level=1).to_csv("debug.csv")
