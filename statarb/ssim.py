from util import *
from regress import *
import gc
from loaddata import *
from collections import defaultdict
import argparse

halfdays = ['20040703', '20050703', '20060703', '20070703', '20080703', '20090703', '20100703', '20111125', '20110703',
            '20120703', '20121123']
# July 3
halfdays.append('20130703')
halfdays.append('20140703')
halfdays.append('20150703')
# day after Thanksgiving
halfdays.append('20041126')
halfdays.append('20051125')
halfdays.append('20061124')
halfdays.append('20071123')
halfdays.append('20081128')
halfdays.append('20091127')
halfdays.append('20101126')
halfdays.append('20111125')
halfdays.append('20121123')
halfdays.append('20131129')
halfdays.append('20141128')
halfdays.append('20151127')
# Christmas Eve
halfdays.append('20041223')
# halfdays.append('20051223') - Christmas was on a Monday
# halfdays.append('20061223') - Christmas was on a Monday
halfdays.append('20071224')
halfdays.append('20081224')
halfdays.append('20091224')
halfdays.append('20121224')
halfdays.append('20131224')
halfdays.append('20141224')
halfdays.append('20151224')

day_bucket = {
    'not': defaultdict(int),
    'pnl': defaultdict(int),
    'trd': defaultdict(int),
    'long': defaultdict(int),
    'short': defaultdict(int),
}
month_bucket = {
    'not': defaultdict(int),
    'pnl': defaultdict(int),
    'trd': defaultdict(int),
}
time_bucket = {
    'not': defaultdict(int),
    'pnl': defaultdict(int),
    'trd': defaultdict(int),
}
dayofweek_bucket = {
    'not': defaultdict(int),
    'pnl': defaultdict(int),
    'trd': defaultdict(int),
}
cond_bucket = {
    'not': defaultdict(int),
    'pnl': defaultdict(int),
    'trd': defaultdict(int),
}
upnames = 0
downnames = 0

parser = argparse.ArgumentParser(description='G')
parser.add_argument("--file", action="store", dest="file", default=None)
parser.add_argument("--start", action="store", dest="start", default=None)
parser.add_argument("--end", action="store", dest="end", default=None)
parser.add_argument("--fill", action="store", dest='fill', default='vwap')
parser.add_argument("--slipbps", action="store", dest='slipbps', default=0.0001)
parser.add_argument("--fcast", action="store", dest='fcast', default=None)
parser.add_argument("--cond", action="store", dest='cond', default='mkt_cap')
parser.add_argument("--data_dir", action="store", dest="data_dir", default='.')
args = parser.parse_args()

fcasts = args.fcast.split(",")
# original cols = ['split', 'div', 'close', 'close', 'bvwap_b', args.cond, 'indname1', 'srisk_pct', 'gdate', 'rating_mean', 'ticker', 'tradable_volume', 'tradable_med_volume_21_y', 'mdvp_y', 'overnight_log_ret', 'date', 'log_ret', 'volume', 'capitalization', 'cum_log_ret', 'dpvolume_med_21', 'volat_21_y', 'close_y']
cols = ['split', 'div', 'close', args.cond, 'ind1', 'symbol', 'volume', 'med_volume_21', 'mdvp', 'overnight_log_ret',
        'log_ret', 'volume', 'volat_21']
# Change bvwap_b to close_b?
cols.extend(BARRA_FACTORS)
cache_df = load_cache(dateparser.parse(args.start), dateparser.parse(args.end), args.data_dir, cols)
# cache_df = push_data(cache_df, 'bvwap_b')
cache_df = push_data(cache_df, 'close')

trades_df = None
if args.file is not None:
    trades_df = pd.read_csv(args.file, parse_dates=True, usecols=['date', 'gvkey', 'vwap_n', 'traded'])
else:
    for pair in fcasts:
        fdir, fcast, weight = pair.split(":")
        print(fdir, fcast, weight)
        fcast_dfs = []
        for ff in sorted(glob.glob(fdir + "/" + fcast + "/alpha.*.csv")):
            m = re.match(r".*alpha\." + fcast + "\.(\d{8})-(\d{8}).csv", str(ff))
            d1 = m.group(1)
            d2 = m.group(2)
            if args.start is not None:
                if d2 <= args.start or d1 >= args.end: continue
            print("Loading {} from {} to {}".format(ff, d1, d2))
            df = pd.read_csv(ff, header=0, parse_dates=['date'], dtype={'gvkey': str})
            df.set_index(['date', 'gvkey'], inplace=True)
            fcast_dfs.append(df)
        fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
        fcast_trades_df = fcast_df.sort_index()

        print(fcast)
        print(fcast_trades_df.columns)
        print(fcast_trades_df.xs(testid, level=1)[['traded', 'shares']])

        if trades_df is None:
            trades_df = fcast_trades_df
            #            trades_df['traded'] = trades_df['traded'].fillna(0) * float(weight)
            trades_df['shares'] = trades_df['shares'].fillna(0) * float(weight)
        #            print(trades_df['shares'].xs(testid, level=1).head(50))
        else:
            trades_df = pd.merge(trades_df, fcast_trades_df, how='outer', left_index=True, right_index=True,
                                 suffixes=['', '_dead'])
            #            trades_df['traded'] = trades_df['traded'].fillna(0) + trades_df['traded_dead'].fillna(0) * float(weight)
            trades_df['shares'] = trades_df['shares'].fillna(method='ffill').fillna(0) + trades_df[
                'shares_dead'].fillna(method='ffill').fillna(0) * float(weight)
            #            print(trades_df['traded'].xs(testid, level=1).head())
            trades_df = remove_dup_cols(trades_df)

trades_df = pd.merge(trades_df.reset_index(), cache_df.reset_index(), how='left', left_on=['date', 'gvkey'],
                     right_on=['date', 'gvkey'], suffixes=['', '_dead'])
trades_df = remove_dup_cols(trades_df)
trades_df.set_index(['date', 'gvkey'], inplace=True)
cache_df = None

trades_df['forecast_abs'] = np.abs(trades_df['forecast'])
trades_df['cash'] = 0
# trades_df['shares'] = 0
trades_df['pnl'] = 0
trades_df['cum_pnl'] = 0
trades_df['day_pnl'] = 0

lastgroup_df = None
lastday = None
last_ts = None
pnl_last_tot = 0
pnl_last_day_tot = 0
fillslip_tot = 0
traded_tot = 0
totslip = 0
totturnover = 0
cnt = 0
long_names = 0
short_names = 0

if args.fill == "vwap":
    print("Filling at vwap...")
    trades_df['fillprice'] = trades_df['bvwap_b_n']
    print("Bad count: {}".format(len(trades_df) - len(trades_df[trades_df['fillprice'] > 0])))
    trades_df.ix[(trades_df['fillprice'] <= 0) | (trades_df['fillprice'].isnull()), 'fillprice'] = trades_df['close']
else:
    print("Filling at mid...")
    trades_df['fillprice'] = trades_df['close']

trades_df['pdiff'] = trades_df['fillprice'] - trades_df['close']
trades_df['pdiff_pct'] = trades_df['pdiff'] / trades_df['close']
trades_df['unfilled'] = trades_df['target'] - trades_df['traded']
trades_df['slip2close'] = (trades_df['close'] - trades_df['fillprice']) / trades_df['fillprice']

####
max_dollars = 4e6
max_adv = 0.02
participation = 0.015
#  Might need to change inputs ^^^
trades_df['max_notional'] = (trades_df['tradable_med_volume_21_y'] * trades_df['close_y'] * max_adv).clip(0,
                                                                                                          max_dollars)
trades_df['min_notional'] = (-1 * trades_df['tradable_med_volume_21_y'] * trades_df['close_y'] * max_adv).clip(
    -max_dollars, 0)
trades_df['bvolume_d'] = trades_df['volume'].groupby(level='gvkey').diff()
trades_df.loc[trades_df['bvolume_d'] < 0, 'bvolume_d'] = trades_df['volume']
trades_df = push_data(trades_df, 'bvolume_d')
trades_df['max_trade_shares'] = trades_df['bvolume_d_n'] * participation
trades_df['min_trade_shares'] = -1 * trades_df['max_trade_shares']
###

trades_df = create_z_score(trades_df, 'srisk_pct')
trades_df = create_z_score(trades_df, 'rating_mean')
trades_df.replace([np.inf, -np.inf], np.nan, inplace=True)
# print(trades_df)
gc.collect()

for ts, group_df in trades_df.groupby(level='date'):
    #    print("Looking at {}".format(ts))
    dayname = ts.strftime("%Y%m%d")
    monthname = ts.strftime("%Y%m")
    weekdayname = ts.weekday()
    timename = ts.strftime("%H%M")

    if dayname in halfdays and int(timename) > 1245:
        continue

    if lastgroup_df is not None:
        group_df = pd.merge(group_df.reset_index(), lastgroup_df.reset_index(), how='left', left_on=['gvkey'],
                            right_on=['gvkey'], suffixes=['', '_last'])
        group_df['date'] = ts
        group_df.set_index(['date', 'gvkey'], inplace=True)
        if dayname != lastday:
            group_df['cash_last'] += group_df['shares_last'] * group_df['div'].fillna(0)
            group_df['shares_last'] *= group_df['split'].fillna(1)
    else:
        group_df['shares_last'] = 0
        group_df['cash_last'] = 0

    group_df['shares1'] = group_df['shares']
    group_df['shares_traded'] = group_df['shares'] - group_df['shares_last'].fillna(0)
    group_df['shares_traded'] = group_df[['shares_traded', 'max_trade_shares']].min(axis=1)
    group_df['shares_traded'] = group_df[['shares_traded', 'min_trade_shares']].max(axis=1)
    group_df['shares'] = group_df['shares_last'] + group_df['shares_traded']

    group_df['traded2'] = group_df['shares_traded'] * group_df['fillprice']
    #    print(group_df.xs(testid, level=1)[['traded', 'traded2', 'shares1', 'shares', 'shares_last', 'fillprice']])
    group_df['traded'] = group_df['traded2']
    group_df['cash'] = -1.0 * group_df['traded2'] + group_df['cash_last'].fillna(0)

    fillslip_tot += (group_df['pdiff_pct'] * group_df['traded']).sum()
    traded_tot += np.abs(group_df['traded']).sum()
    #    print("Slip2 {} {}".format(fillslip_tot, traded_tot))

    markPrice = 'iclose_n'
    #    if ts.strftime("%H%M") == "1530" or (dayname in halfdays and timename == "1230"):
    if ts.strftime("%H%M") == "1545" or (dayname in halfdays and timename == "1245"):
        markPrice = 'close'

    group_df['slip'] = np.abs(group_df['traded']).fillna(0) * float(args.slipbps)
    totslip += group_df['slip'].sum()
    group_df['cash'] = group_df['cash'] - group_df['slip']
    group_df['pnl'] = trades_df.ix[group_df.index, 'cum_pnl'] = group_df['shares'] * group_df[markPrice] + group_df[
        'cash']
    notional = np.abs(group_df['shares'] * group_df[markPrice]).dropna().sum()
    group_df['lsnot'] = group_df['shares'] * group_df[markPrice]
    pnl_tot = group_df['pnl'].dropna().sum()

    # if lastgroup_df is not None:
    #     group_df['pnl_diff'] = (group_df['pnl'] - group_df['pnl_last'])
    #     print(group_df['pnl_diff'].order().dropna().head())
    #     print(group_df['pnl_diff'].order().dropna().tail())

    pnl_incr = pnl_tot - pnl_last_tot
    traded = np.abs(group_df['traded']).fillna(0).sum()

    day_bucket['trd'][dayname] += traded
    month_bucket['trd'][monthname] += traded
    dayofweek_bucket['trd'][weekdayname] += traded
    time_bucket['trd'][timename] += traded

    # try:
    #     print(group_df.xs(testid, level=1)[['target', 'traded', 'cash', 'shares', 'close', 'close', 'shares_last', 'cash_last']])
    # except KeyError:
    #     pass

    # print(group_df['shares'].describe())
    # print(group_df[markPrice].describe())
    if markPrice == 'close' and notional > 0:
        delta = pnl_tot - pnl_last_day_tot
        ret = delta / notional
        daytraded = day_bucket['trd'][dayname]
        notional2 = np.sum(np.abs((group_df['close'] * group_df['position'] / group_df['close'])))
        print(
            "{}: {} {} {} {:.4f} {:.2f} {}".format(ts, notional, pnl_tot, delta, ret, daytraded / notional, notional2))
        day_bucket['pnl'][dayname] = delta
        month_bucket['pnl'][monthname] += delta
        dayofweek_bucket['pnl'][weekdayname] += delta
        day_bucket['not'][dayname] = notional
        day_bucket['long'][dayname] = group_df[group_df['lsnot'] > 0]['lsnot'].dropna().sum()
        day_bucket['short'][dayname] = np.abs(group_df[group_df['lsnot'] < 0]['lsnot'].dropna().sum())
        month_bucket['not'][monthname] += notional
        dayofweek_bucket['not'][weekdayname] += notional
        trades_df.ix[group_df.index, 'day_pnl'] = group_df['pnl'] - group_df['pnl_last']
        pnl_last_day_tot = pnl_tot
        totturnover += daytraded / notional
        short_names += len(group_df[group_df['traded'] < 0])
        long_names += len(group_df[group_df['traded'] > 0])
        cnt += 1

    time_bucket['pnl'][timename] += pnl_incr
    time_bucket['not'][timename] = notional

    upnames += len(group_df[group_df['pnl'] > 0])
    downnames += len(group_df[group_df['pnl'] < 0])

    lastgroup_df = group_df.reset_index()[['shares', 'cash', 'pnl', 'gvkey', 'target']]
    lastday = dayname
    pnl_last_tot = pnl_tot
    last_ts = ts

period = "{}.{}".format(args.start, args.end)

print()
print()
print("Fill Slip: {}".format(fillslip_tot / traded_tot))
oppslip = (trades_df['unfilled'] * trades_df['slip2close']).sum()
print("Opp slip: {}".format(oppslip))
print("Totslip: {}".format(totslip))
print("Avg turnover: {}".format(totturnover / cnt))
print("Longs: {}".format(long_names / cnt))
print("Shorts: {}".format(short_names / cnt))
print()

print("Conditional breakdown")
lastslice = trades_df.xs(last_ts, level='date')
condname = args.cond

for ind in INDUSTRIES:
    decile = lastslice[lastslice['indname1'] == ind]
    print("{}: {}".format(ind, decile['cum_pnl'].sum()))

lastslice['decile'] = lastslice[condname].rank() / float(len(lastslice)) * 10
lastslice['decile'] = lastslice['decile'].fillna(-1)
lastslice['decile'] = lastslice['decile'].astype(int)
for ii in range(-1, 10):
    decile = lastslice[lastslice['decile'] == ii]
    print("{}: {} {}".format(ii, decile[condname].mean(), decile['cum_pnl'].sum()))

firstslice = trades_df.xs(min(trades_df.index)[0], level='date')
pnlbystock = lastslice['cum_pnl'].fillna(0)
plt.figure()
pnlbystock.hist(bins=1800)
plt.savefig("stocks.png")
maxpnlid = pnlbystock.idxmax()
minpnlid = pnlbystock.idxmin()

print("Max pnl stock pnl distribution: {} {}".format(maxpnlid, pnlbystock.ix[maxpnlid]))
print("Min pnl stock pnl distribution: {} {}".format(minpnlid, pnlbystock.ix[minpnlid]))
plt.figure()
maxstock_df = trades_df.xs(maxpnlid, level=1)
maxstock_df['day_pnl'].hist(bins=100)
plt.savefig("maxstock.png")
# maxpnlid = maxstock_df['day_pnl'].idxmax()
# print(maxstock_df.xs(maxpnlid))
print()

# timeslice = trades_df.xs( "2011-11-25 10:00:00", level='date' )
# plt.figure()
# timeslice['day_pnl'].hist()
# plt.savefig("badtimes.png")

print("Factor Pnl")
firstslice = create_z_score(firstslice, 'srisk_pct')
firstslice = create_z_score(firstslice, 'rating_mean')
merge = pd.merge(firstslice.reset_index(), lastslice.reset_index(), left_on=['gvkey'], right_on=['gvkey'],
                 suffixes=['_first', '_last'])
print(merge.columns)
# merge['srisk_pct_z_first'] = merge['srisk_pct_z']
lastnotional = np.abs(lastslice['position']).sum()
for factor in BARRA_FACTORS + PROP_FACTORS:
    #    pnl = (merge['position_last'] * merge[factor + '_first']).sum()
    exposure = (merge['cum_pnl_last'] * merge[factor + '_first']).sum() / lastnotional
    pnl = (trades_df['day_pnl'] * trades_df[factor]).sum()
    #    exposure = (trades_df['position'] * trades_df[factor]).groupby(level='date')
    print("{}: exposure: {:.2f}, pnl: {}".format(factor, exposure, pnl))
print()

print("Forecast-trade corr:")
print(trades_df[['forecast', 'traded', 'target']].corr())
plt.figure()
plt.scatter(trades_df['forecast'], trades_df['traded'])
plt.savefig("forecast_trade_corr." + period + ".png")
print()

longs = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['long'].items())], columns=['date', 'long'])
longs.set_index(keys=['date'], inplace=True)
shorts = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['short'].items())], columns=['date', 'short'])
shorts.set_index(keys=['date'], inplace=True)
longshorts = pd.merge(longs, shorts, how='inner', left_index=True, right_index=True)
plt.figure()
longshorts[['long', 'short']].plot()
plt.savefig("longshorts." + period + ".png")

nots = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['not'].items())], columns=['date', 'notional'])
nots.set_index(keys=['date'], inplace=True)
plt.figure()
nots['notional'].plot()
plt.savefig("notional." + period + ".png")

trds = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['trd'].items())], columns=['date', 'traded'])
trds.set_index(keys=['date'], inplace=True)
plt.figure()
trds['traded'].plot()
plt.savefig("traded." + period + ".png")

pnl_df = pd.DataFrame([[d, v] for d, v in sorted(day_bucket['pnl'].items())], columns=['date', 'pnl'])
pnl_df.set_index(['date'], inplace=True)
rets = pd.merge(pnl_df, nots, left_index=True, right_index=True)
rets = pd.merge(rets, trds, left_index=True, right_index=True)
print("Total Pnl: ${:.0f}K".format(rets['pnl'].sum() / 1000.0))

rets['day_rets'] = rets['pnl'] / rets['notional'].shift(1)
rets['day_rets'].replace([np.inf, -np.inf], np.nan, inplace=True)
rets['day_rets'].fillna(0, inplace=True)
rets['cum_ret'] = (1 + rets['day_rets']).dropna().cumprod()

plt.figure()
rets['cum_ret'].plot()
plt.draw()
plt.savefig("rets." + period + ".png")

mean = rets['day_rets'].mean() * 252
std = rets['day_rets'].std() * math.sqrt(252)

sharpe = mean / std
print("Day mean: {:.4f} std: {:.4f} sharpe: {:.4f} avg Notional: ${:.0f}K".format(mean, std, sharpe,
                                                                                  rets['notional'].mean() / 1000.0))
print()

print("Month breakdown Bps")
for month in sorted(month_bucket['not'].keys()):
    notional = month_bucket['not'][month]
    traded = month_bucket['trd'][month]
    if notional > 0:
        print("Month {}: {:.4f} {:.4f}".format(month, 10000 * month_bucket['pnl'][month] / notional, traded / notional))
print()

print("Time breakdown Bps")
for time in sorted(time_bucket['not'].keys()):
    notional = time_bucket['not'][time]
    traded = time_bucket['trd'][time]
    if notional > 0:
        print("Time {}: {:.4f} {:.4f}".format(time, 10000 * time_bucket['pnl'][time] / notional, traded / notional))
print()

print("Dayofweek breakdown Bps")
for dayofweek in sorted(dayofweek_bucket['not'].keys()):
    notional = dayofweek_bucket['not'][dayofweek]
    traded = dayofweek_bucket['trd'][dayofweek]
    if notional > 0:
        print("Dayofweek {}: {:.4f} {:.4f}".format(dayofweek, 10000 * dayofweek_bucket['pnl'][dayofweek] / notional,
                                                   traded / notional))
print()

print("Up %: {:.4f}".format(float(upnames) / (upnames + downnames)))
