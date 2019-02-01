#!/usr/bin/env python 

from util import *
from regress import *
from loaddata import *

import openopt

from collections import defaultdict

import argparse

halfdays = ['20111125', '20120703', '20121123', '20121224']
breaks = ['20110705', '20120102', '20120705', '20130103']

parser = argparse.ArgumentParser(description='G')
parser.add_argument("--start", action="store", dest="start", default=None)
parser.add_argument("--end", action="store", dest="end", default=None)
parser.add_argument("--fill", action="store", dest='fill', default='mid')
parser.add_argument("--slipbps", action="store", dest='slipbps', default=0.0001)
parser.add_argument("--fcast", action="store", dest='fcast', default=None)
parser.add_argument("--weights", action="store", dest='weights', default=None)
args = parser.parse_args()

participation = 0.015

cols = ['split', 'div', 'close', 'iclose', 'bvwap_b', 'bvolume', 'tradable_med_volume_21_y', 'close_y']
cache_df = load_cache(dateparser.parse(args.start), dateparser.parse(args.end), cols)
cache_df['bvolume_d'] = cache_df['bvolume'].groupby(level='sid').diff()
cache_df.loc[cache_df['bvolume_d'] < 0, 'bvolume_d'] = cache_df['bvolume']
cache_df = push_data(cache_df, 'bvolume_d')
cache_df['max_trade_size'] = cache_df['bvolume_d_n'] * cache_df['iclose'] * participation
cache_df['min_trade_size'] = -1 * cache_df['max_trade_size']
cache_df = push_data(cache_df, 'bvwap_b')
cache_df = push_data(cache_df, 'iclose')

trades_df = None

forecasts = list()
fcasts = args.fcast.split(",")
for pair in fcasts:
    fdir, fcast = pair.split(":")
    print
    "Loading {} {}".format(fdir, fcast)
    forecasts.append(fcast)
    flist = list()
    for ff in sorted(glob.glob("./" + fdir + "/opt/opt." + fcast + ".*.csv")):
        m = re.match(r".*opt\." + fcast + "\.(\d{8})_\d{6}.csv", str(ff))
        if m is None: continue
        d1 = int(m.group(1))
        if d1 < int(args.start) or d1 > int(args.end): continue
        print
        "Loading {}".format(ff)
        flist.append(pd.read_csv(ff, parse_dates=True))
    fcast_trades_df = pd.concat(flist)
    #    fcast_trades_df = fcast_trades_df[ fcast_trades_df['sid'] == testid]
    fcast_trades_df['iclose_ts'] = pd.to_datetime(fcast_trades_df['iclose_ts'])
    fcast_trades_df = fcast_trades_df.set_index(['iclose_ts', 'sid']).sort()

    if trades_df is None:
        trades_df = fcast_trades_df
        trades_df['traded_' + fcast] = trades_df['traded']
        trades_df['shares_' + fcast] = trades_df['shares']
    else:
        trades_df = pd.merge(trades_df, fcast_trades_df, how='outer', left_index=True, right_index=True,
                             suffixes=['', '_dead'])
        trades_df['traded_' + fcast] = trades_df['traded_dead']
        trades_df['shares_' + fcast] = trades_df['shares_dead'].unstack().fillna(method='ffill').stack().fillna(0)
        #        print trades_df['shares_' + fcast].xs(testid, level=1).head(50)
        trades_df = remove_dup_cols(trades_df)

trades_df = pd.merge(trades_df.reset_index(), cache_df.reset_index(), how='left', left_on=['iclose_ts', 'sid'],
                     right_on=['iclose_ts', 'sid'], suffixes=['', '_dead'])
trades_df = remove_dup_cols(trades_df)
trades_df.set_index(['iclose_ts', 'sid'], inplace=True)
cache_df = None

max_dollars = 1e6
max_adv = 0.02
trades_df['max_notional'] = (trades_df['tradable_med_volume_21_y'] * trades_df['close_y'] * max_adv).clip(0,
                                                                                                          max_dollars)
trades_df['min_notional'] = (-1 * trades_df['tradable_med_volume_21_y'] * trades_df['close_y'] * max_adv).clip(
    -max_dollars, 0)

trades_df['cash'] = 0
# trades_df['cash_last'] = 0
trades_df['traded'] = 0
trades_df['shares'] = 0
trades_df['pnl'] = 0
trades_df['cum_pnl'] = 0
trades_df['day_pnl'] = 0

if args.fill == "vwap":
    print
    "Filling at vwap..."
    trades_df['fillprice'] = trades_df['bvwap_b_n']
    print
    "Bad count: {}".format(len(trades_df) - len(trades_df[trades_df['fillprice'] > 0]))
    trades_df.ix[(trades_df['fillprice'] <= 0) | (trades_df['fillprice'].isnull()), 'fillprice'] = trades_df['iclose']
else:
    print
    "Filling at mid..."
    trades_df['fillprice'] = trades_df['iclose']

trades_df.replace([np.inf, -np.inf], np.nan, inplace=True)


def objective(weights):
    ii = 0
    for fcast in forecasts:
        print
        "Weight {}: {}".format(fcast, weights[ii])
        ii += 1

    day_bucket = {
        'not': defaultdict(int),
        'pnl': defaultdict(int),
        'trd': defaultdict(int),
    }

    lastgroup_df = None
    lastday = None
    pnl_last_day_tot = 0
    totslip = 0

    for ts, group_df in trades_df.groupby(level='iclose_ts'):

        dayname = ts.strftime("%Y%m%d")
        if int(dayname) > 20121227: continue
        monthname = ts.strftime("%Y%m")
        weekdayname = ts.weekday()
        timename = ts.strftime("%H%M")

        if dayname in halfdays and int(timename) > 1245:
            continue

        if lastgroup_df is not None:
            #            group_df = pd.merge(group_df.reset_index().set_index('sid'), lastgroup_df.reset_index().set_index('sid'), how='left', left_index=True, right_index=True, suffixes=['', '_last'])
            for col in lastgroup_df.columns:
                if col == "sid": continue
                lastgroup_df[col + "_last"] = lastgroup_df[col]
                del lastgroup_df[col]
            group_df = pd.concat([group_df.reset_index().set_index('sid'), lastgroup_df.reset_index().set_index('sid')],
                                 join='outer', axis=1, verify_integrity=True)
            group_df['iclose_ts'] = ts
            group_df.reset_index().set_index(['iclose_ts', 'sid'], inplace=True)
            if dayname != lastday and lastday is not None:
                group_df['cash_last'] += group_df['shares_last'] * group_df['div'].fillna(0)
                group_df['shares_last'] *= group_df['split'].fillna(1)
        else:
            group_df['shares_last'] = 0
            group_df['cash_last'] = 0

        ii = 0
        for fcast in forecasts:
            #            print fcast
            #            print group_df['shares_' + fcast].xs(testid, level=1)
            group_df['shares'] += group_df['shares_' + fcast].fillna(0) * weights[ii]
            #           print group_df['shares'].xs(testid, level=1)
            ii += 1

        group_df['shares_traded'] = group_df['shares'] - group_df['shares_last'].fillna(0)
        # group_df['shares'] = group_df['traded'] / group_df['fillprice']
        group_df['dollars_traded'] = group_df['shares_traded'] * group_df['fillprice'] * -1.0
        group_df['cash'] = group_df['cash_last'] + group_df['dollars_traded']

        #        fillslip_tot +=  (group_df['pdiff_pct'] * group_df['traded']).sum()
        #        traded_tot +=  np.abs(group_df['traded']).sum()
        #    print "Slip2 {} {}".format(fillslip_tot, traded_tot)

        markPrice = 'iclose_n'
        #    if ts.strftime("%H%M") == "1530" or (dayname in halfdays and timename == "1230"):
        if ts.strftime("%H%M") == "1545" or (dayname in halfdays and timename == "1245"):
            markPrice = 'close'

        group_df['slip'] = np.abs(group_df['dollars_traded']).fillna(0) * float(args.slipbps)
        totslip += group_df['slip'].sum()
        group_df['cash'] = group_df['cash'] - group_df['slip']
        group_df['pnl'] = group_df['shares'] * group_df[markPrice] + group_df['cash'].fillna(0)
        notional = np.abs(group_df['shares'] * group_df[markPrice]).dropna().sum()
        group_df['lsnot'] = group_df['shares'] * group_df[markPrice]
        pnl_tot = group_df['pnl'].dropna().sum()
        #        print group_df[['shares', 'shares_tgt', 'shares_qhl_b', 'cash', 'dollars_traded', 'pnl']]
        # if lastgroup_df is not None:
        #     group_df['pnl_diff'] = (group_df['pnl'] - group_df['pnl_last'])
        #     print group_df['pnl_diff'].order().dropna().head()
        #     print group_df['pnl_diff'].order().dropna().tail()

        #        pnl_incr = pnl_tot - pnl_last_tot
        traded = np.abs(group_df['dollars_traded']).fillna(0).sum()

        day_bucket['trd'][dayname] += traded
        #       month_bucket['trd'][monthname] += traded
        #      dayofweek_bucket['trd'][weekdayname] += traded
        #      time_bucket['trd'][timename] += traded

        # try:
        #     print group_df.xs(testid, level=1)[['target', 'traded', 'cash', 'shares', 'close', 'iclose', 'shares_last', 'cash_last']]
        # except KeyError:
        #     pass

        # print group_df['shares'].describe()
        # print group_df[markPrice].describe()
        if markPrice == 'close' and notional > 0:
            delta = pnl_tot - pnl_last_day_tot
            ret = delta / notional
            daytraded = day_bucket['trd'][dayname]
            notional2 = np.sum(np.abs((group_df['close'] * group_df['position'] / group_df['iclose'])))
            print
            "{}: {} {} {} {:.4f} {:.2f} {}".format(ts, notional, pnl_tot, delta, ret, daytraded / notional, notional2)
            day_bucket['pnl'][dayname] = delta
            #            month_bucket['pnl'][monthname] += delta
            #            dayofweek_bucket['pnl'][weekdayname] += delta
            day_bucket['not'][dayname] = notional
            #            day_bucket['long'][dayname] = group_df[ group_df['lsnot'] > 0 ]['lsnot'].dropna().sum()
            #            day_bucket['short'][dayname] = np.abs(group_df[ group_df['lsnot'] < 0 ]['lsnot'].dropna().sum())
            #            month_bucket['not'][monthname] += notional
            #            dayofweek_bucket['not'][weekdayname] += notional
            #            trades_df.ix[ group_df.index, 'day_pnl'] = group_df['pnl'] - group_df['pnl_last']
            pnl_last_day_tot = pnl_tot
        #            totturnover += daytraded/notional
        #            short_names += len(group_df[ group_df['traded'] < 0 ])
        #            long_names += len(group_df[ group_df['traded'] > 0 ])
        #            cnt += 1

        lastgroup_df = group_df.reset_index()[['shares', 'cash', 'pnl', 'sid', 'target']]

    nots = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['not'].items())], columns=['date', 'notional'])
    nots.set_index(keys=['date'], inplace=True)
    pnl_df = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['pnl'].items())], columns=['date', 'pnl'])
    pnl_df.set_index(['date'], inplace=True)
    rets = pd.merge(pnl_df, nots, left_index=True, right_index=True)
    print
    "Total Pnl: ${:.0f}K".format(rets['pnl'].sum() / 1000.0)

    rets['day_rets'] = rets['pnl'] / rets['notional']
    rets['day_rets'].replace([np.inf, -np.inf], np.nan, inplace=True)
    rets['day_rets'].fillna(0, inplace=True)
    rets['cum_ret'] = (1 + rets['day_rets']).dropna().cumprod()

    mean = rets['day_rets'].mean() * 252
    std = rets['day_rets'].std() * math.sqrt(252)

    sharpe = mean / std
    print
    "Day mean: {:.4f} std: {:.4f} sharpe: {:.4f} avg Notional: ${:.0f}K".format(mean, std, sharpe,
                                                                                rets['notional'].mean() / 1000.0)
    penalty = 0.05 * np.std(weights)
    print
    "penalty: {}".format(penalty)
    print

    return sharpe - penalty


if args.weights is None:
    initial_weights = np.ones(len(forecasts)) * .5
else:
    initial_weights = np.array([float(x) for x in args.weights.split(",")])
lb = np.ones(len(forecasts)) * 0.0
ub = np.ones(len(forecasts))
plotit = False
p = openopt.NSP(goal='max', f=objective, x0=initial_weights, lb=lb, ub=ub, plot=plotit)
p.ftol = 0.001
p.maxFunEvals = 150
r = p.solve('ralg')

if (r.stopcase == -1 or r.isFeasible == False):
    print
    objective_detail(target, *g_params)
    raise Exception("Optimization failed")

print
r.xf
ii = 0
for fcast in forecasts:
    print
    "{}: {}".format(fcast, r.xf[ii])
    ii += 1
