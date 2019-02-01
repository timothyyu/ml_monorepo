#!/usr/bin/env python

from __future__ import print_function
import sys
import os
import glob
import re
import math

from dateutil import parser as dateparser
import time
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd
import pandas.io.sql as psql
import sqlite3 as lite

from util import *
from calc import *

UNIV_BASE_DIR = ""
SECDATA_BASE_DIR = ""
PRICE_BASE_DIR = ""
BARRA_BASE_DIR = ""
BAR_BASE_DIR = ""
EARNINGS_BASE_DIR = ""
LOCATES_BASE_DIR = ""
#ESTIMATES_BASE_DIR = ""
ESTIMATES_BASE_DIR = ""

t_low_price = 2.0
t_high_price = 500.0
t_min_advp = 1000000.0

e_low_price = 2.25
e_high_price = 500.0
e_min_advp = 5000000.0

fromtimestamp = lambda x:datetime.fromtimestamp(int(x) / 1000.)

def get_uni(start, end, lookback, uni_size=1400):
    unidate = start - timedelta(days=lookback)
    year = unidate.strftime("%Y")
    unidate = unidate.strftime("%Y%m%d")

    univ_dir = UNIV_BASE_DIR + year
    univ_file = univ_dir + "/" + unidate + ".csv"
    univ_df = pd.read_csv(univ_file, header=0, usecols=['sid', 'ticker_root', 'status', 'country', 'currency'], index_col=['sid'])
    print("Universe size (raw): {}".format(len(univ_df.index)))    
    univ_df = univ_df[ (univ_df['country'] == "USA") & (univ_df['currency'] == "USD") ]
    print("Universe size (US/USD): {}".format(len(univ_df.index)))    

    secdata_dir = SECDATA_BASE_DIR + year
    secdata_file = secdata_dir + "/" + unidate + ".csv.gz"
    secdata_df = pd.read_csv(secdata_file, header=0, compression='gzip', usecols=['sid', 'symbol', 'sector', 'ind', 'group', 'sector_name', 'ind_name', 'estu_inter', 'estu_barra4s'], index_col=['sid'])
    univ_df = pd.merge(univ_df, secdata_df, how='inner', left_index=True, right_index=True, sort=True)
    print("Universe size (secdata): {}".format(len(univ_df.index)))    
    univ_df = univ_df[ (univ_df['estu_barra4s'] == 1) | (univ_df['ind'] == 404020) ]
    del univ_df['estu_inter']
    del univ_df['estu_barra4s']
    print("Universe size (estu_inter): {}".format(len(univ_df.index)))    

    univ_df = univ_df[ univ_df['group'] != 3520 ]
    print("Universe size (bio): {}".format(len(univ_df.index)))    

    price_dir = PRICE_BASE_DIR + year
    price_file = price_dir + "/" + unidate + ".csv"
    price_df = pd.read_csv(price_file, header=0, usecols=['sid', 'ticker', 'close', 'tradable_med_volume_21', 'mkt_cap'], index_col=['sid'])

    univ_df = pd.merge(univ_df, price_df, how='inner', left_index=True, right_index=True, sort=True)    
    print("Universe size (prices): {}".format(len(univ_df.index)))    

    univ_df = univ_df[ (univ_df['close'] > t_low_price) & (univ_df['close'] < t_high_price) ]
    print("Universe size (price range): {}".format(len(univ_df.index)))    

    univ_df['mdvp'] = univ_df['tradable_med_volume_21'] * univ_df['close']
    univ_df = univ_df[ univ_df['mdvp'] > t_min_advp ]
    print("Universe size (adv): {}".format(len(univ_df.index)))

    univ_df['rank'] = univ_df['mkt_cap'].fillna(0).rank(ascending=False)
    univ_df = univ_df[ univ_df['rank'] <= uni_size ]
    print("Universe size (mktcap): {}".format(len(univ_df.index)))
    
    return univ_df[ ['symbol', 'sector_name'] ]
#    univ_df = univ_df[['ticker_root']]

    # date = start
    # result_df = pd.DataFrame()
    # while( date < end ):
    #     dateStr = date.strftime("%Y%m%d")
    #     year = date.strftime("%Y")
    #     secdata_dir = SECDATA_BASE_DIR + year
    #     secdata_file = secdata_dir + "/" + dateStr
    #     try:
    #         secdata_df = pd.read_csv(secdata_file, header=0, compression='gzip', usecols=['sid', 'symbol', 'sector', 'ind', 'sector_name', 'ind_name'])
    #     except IOError:
    #         print "File not found: {}".format(secdata_file)
    #         date += timedelta(days=1)
    #         continue
            
    #     secdata_df.set_index('sid', inplace=True)
    #     secdata_df = pd.merge(univ_df, secdata_df, how='inner', left_index=True, right_index=True, sort=True, suffixes=['', '_dead'])
    #     secdata_df['ticker'] = secdata_df['symbol']
    #     del secdata_df['symbol']
    #     secdata_df['date'] = date
    #     secdata_df.reset_index(inplace=True)
    #     result_df = result_df.append(secdata_df)
    #     date += timedelta(days=1)

    # result_df.set_index(keys=['date', 'sid'], inplace=True)
    # result_df = result_df.unstack().asfreq('D', method='pad').stack()
    # result_df.index.names = ['date', 'sid']
    # return result_df

def load_barra(uni_df, start, end, cols=None):
    if cols is not None:
        cols.append('sid')
#    if cols is None:
#        cols = ['hbeta', 'pbeta', 'srisk_pct', 'trisk_pct', 'country', 'growth', 'size', 'sizenl', 'divyild', 'btop', 'earnyild', 'beta', 'resvol', 'betanl', 'momentum', 'leverage', 'liquidty', 'yld_pct', 'indname1', 'ind1', 'sid']
    date = start
    result_dfs = list()
    while ( date < end ):
        dateStr = date.strftime('%Y%m%d')
        year = dateStr[0:4]
        barra_dir = BARRA_BASE_DIR + year
        barra_file = barra_dir + "/" + dateStr 
        print("Loading {}".format(barra_file))
        try:
            if cols is not None:
                barra_df = pd.read_csv(barra_file, usecols=cols)
            else:
                barra_df = pd.read_csv(barra_file)
        except IOError:
            print("File not found: {}".format(barra_file))
            date += timedelta(days=1)
            continue

        barra_df['date'] = date    
        #should be left join, but the nans create an issue downstream with unstacking...
        barra_df = pd.merge(uni_df.reset_index(), barra_df, how='inner', left_on=['sid'], right_on=['sid'], sort=False)
        barra_df.set_index(keys=['date', 'sid'], inplace=True)
        result_dfs.append(barra_df)
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs, verify_integrity=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def load_daybars(uni_df, start, end, cols=None, freq='30Min'):
    if cols is None:
        cols = ['dopen', 'dhigh', 'dlow', 'qhigh', 'qlow', 'dvwap', 'dvolume', 'dtrades']
    cols.extend( ['ticker', 'iclose_ts', 'iclose', 'dvolume', 'dopen' ] )
    date = start
    result_dfs = list()
    uni_df = uni_df[ ['ticker'] ]
    uni_df = uni_df.reset_index()
    while ( date < end ):
        dateStr = date.strftime("%Y%m%d")
        bar_file = BAR_BASE_DIR + dateStr + "/daily.txt.gz"
        print("Loading {}".format(bar_file))
        try:
            bars_df = pd.read_csv(bar_file, compression='gzip', sep="|", header=None, names=['ticker', 'iclose_ts', 'dopen', 'dhigh', 'dlow', 'iclose', 'qhigh', 'qlow', 'dvwap', 'dvolume', 'dtrades', 'open_c', 'open_c_volume', 'close_c', 'close_c_volume'], index_col=['iclose_ts'], converters={'iclose_ts': fromtimestamp}, usecols=cols)
        except IOError:
            print("File not found: {}".format(bar_file))
            date += timedelta(days=1)
            continue

        bars_df = bars_df.between_time('09:30:00', '16:00:01')
        bars_df.set_index('ticker', append=True, inplace=True)
        #change closed to 'left' maybe?
        bars_df = bars_df.unstack(level=-1).resample(freq, how='last', closed='right', label='right').stack()
        bars_df.reset_index(inplace=True)
        bars_df['date'] = date        
        bars_df['giclose_ts'] = bars_df['iclose_ts']
        bars_df = pd.merge(uni_df[ uni_df['date'] == date ], bars_df, how='inner', left_on=['date', 'ticker'], right_on=['date', 'ticker'], sort=True, suffixes=['', '_dead'])
        bars_df['gsid'] = bars_df['sid']
        result_dfs.append(bars_df)        
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs)
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def load_prices(uni_df, start, end, cols):
    if cols is None:
        cols = ['open', 'high', 'low', 'prim_volume', 'comp_volume', 'shares_out', 'ret', 'log_ret', 'prim_med_volume_21', 'prim_med_volume_60', 'comp_med_volume_21', 'comp_med_volume_60', 'tradable_med_volume_60', 'volat_21', 'volat_60', 'cum_log_ret', 'overnight_log_ret', 'today_log_ret', 'overnight_volat_21', 'today_volat_21', 'split', 'div']
    cols.extend( ['sid', 'ticker', 'close', 'tradable_med_volume_21', 'log_ret', 'tradable_volume', 'mkt_cap'] )
    date = start
    result_dfs = list()
    while ( date < end ):
        dateStr = date.strftime('%Y%m%d')
        year = dateStr[0:4]
        price_dir = PRICE_BASE_DIR + year
        price_file = price_dir + "/" + dateStr 
        print("Loading {}".format(price_file))
        try:
            prices_df = pd.read_csv(price_file, header=0, usecols=cols)
        except IOError:
            print("File not found: {}".format(price_file))
            date += timedelta(days=1)
            continue

        prices_df['date'] = prices_df['gdate'] = date
#        print uni_df.head()
        prices_df = pd.merge(uni_df.reset_index(), prices_df.reset_index(), how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
        prices_df.set_index(keys=['date', 'sid'], inplace=True)
        result_dfs.append(prices_df)        
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs, verify_integrity=True)
    result_df['tradable_med_volume_21'] = result_df['tradable_med_volume_21'].astype(float)
    if 'shares_out' in result_df.columns:
        result_df['shares_out'] = result_df['shares_out'].astype(float)
    result_df['tradable_volume'] = result_df['tradable_volume'].astype(float)
    if 'comp_voume' in result_df.columns:
        result_df['comp_volume'] = result_df['comp_volume'].astype(float)
    result_df['mdvp'] = result_df['close'] * result_df['tradable_med_volume_21']
    result_df = lag_data(result_df)
    result_df['expandable'] = (result_df['close_y'] > e_low_price) & (result_df['close_y'] < e_high_price) & (result_df['mdvp_y'] > e_min_advp)

    for col in ['ind_name_y', 'name_y', 'sector_name_y', 'sector_y', 'ticker_y', 'gdate_y', 'ticker_root_y']:
        if col in result_df.columns:
            del result_df[col]

    return result_df

def load_volume_profile(uni_df, start, end, freq='30Min'):
    date = start
    result_dfs = list()
    while ( date < end ):
        dateStr = date.strftime('%Y%m%d')
        year = dateStr[0:4]
        price_dir = PRICE_BASE_DIR + year
        volume_file = price_dir + "/" + dateStr 
        print("Loading {}".format(volume_file))
        try:
            volume_df = pd.read_csv(volume_file, header=0, index_col=['sid'])
        except IOError:
            print("File not found: {}".format(volume_file))
            date += timedelta(days=1)
            continue

        print("stacking...")
        volume_df = volume_df.stack()
        volume_df = volume_df.reset_index()

        volume_df = volume_df[ (volume_df['level_1'] != 'med_open_volume' ) & (volume_df['level_1'] != 'med_close_volume') & (volume_df['level_1'] != 'med_cum_pre_mkt_volume') & (volume_df['level_1'] != 'med_cum_post_mkt_volume')]
        timemap = dict()   
        print("parsing dates...")     
        for rawtime in volume_df['level_1'].unique():
            val = None
            try:
                val = dateparser.parse(dateStr +  " " + rawtime[:-2] + ":" + rawtime[-2:])
            except:
                pass
            timemap[rawtime] = val
            
        print("mapping dates...")
        volume_df['iclose_ts'] = volume_df['level_1'].apply(lambda x: timemap[x])        
        volume_df['date'] = date
        volume_df.set_index(keys=['date', 'sid'], inplace=True)
        print("merging...")
        volume_df = pd.merge(uni_df, volume_df, how='inner', left_index=True, right_index=True, sort=True, suffixes=['', '_dead'])
        volume_df.reset_index(inplace=True)
        grouped = volume_df.groupby('sid')
        print("accumulating volumes...")
        for name, group in grouped:
            group['med_cum_volume'] = pd.expanding_sum(group[0])
            del group[0]
            group['sid'] = name
            group = group.reset_index()
#            print group.head()
            group.set_index('iclose_ts', inplace=True)
            group_df = group.resample(freq, how='last', closed='right', label='right')
#            print group_df.head()
            result_dfs.append( group_df )

        date += timedelta(days=1)
    
    result_df = pd.concat(result_dfs)
    result_df = result_df.reset_index()
    print(result_df.head())
    result_df['iclose_ts'] = result_df['level_0']
    del result_df['level_0']
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def aggregate_bars(bars_df, freq=30):
    print("Aggregating bars...")
    #ASSUMES SORTED
    start = bars_df['bopen_ts'].min()
    t0 = start
    t1 = t0 + timedelta(minutes=freq)
    end = bars_df.index.max()
    agg_bars_dfs = list()
    while ( t1 <= end ):
        print("Grouping to {}".format(t1))
        sub_df = bars_df.truncate(after=t1)
        grouped = sub_df.groupby('ticker')
         
        df_d = dict()
        df_d['bopen_ts'] = start
        df_d['iclose_ts'] = t1
        df_d['bopen'] = grouped['bopen'].first()
        df_d['bfirst'] = grouped['bfirst'].first()
        df_d['bigh'] = grouped['bhigh'].max()
        df_d['blow'] = grouped['blow'].min()        
        df_d['blast'] = grouped['blast'].last()
        df_d['iclose'] = grouped['iclose'].last()
        df_d['bvwap'] = grouped.apply(lambda x: (x['bvwap'] * x['bvolume'] / x['bvolume'].sum()).sum())
        df_d['bvolume'] = grouped['bvolume'].sum()
        df_d['btrades'] = grouped['btrades'].sum()
        df_d['meanSpread'] = grouped['meanSpread'].mean()
        df_d['meanEffectiveSpread'] = grouped['meanEffectiveSpread'].mean()
        df_d['meanBidSize'] = grouped['meanBidSize'].mean()
        df_d['meanAskSize'] = grouped['meanAskSize'].mean()
        df_d['bidHitTrades'] = grouped['bidHitTrades'].sum()
        df_d['midHitTrades'] = grouped['midHitTrades'].sum()
        df_d['askHitTrades'] = grouped['askHitTrades'].sum()
        df_d['bidHitDollars'] = grouped['bidHitDollars'].sum()
        df_d['midHitDollars'] = grouped['midHitDollars'].sum()
        df_d['askHitDollars'] = grouped['askHitDollars'].sum()
        df_d['outsideTrades'] = grouped['outsideTrades'].sum()
        df_d['outsideDollars'] = grouped['outsideDollars'].sum()

        sub_df = bars_df.truncate(before=t0, after=t1)
        grouped = sub_df.groupby('ticker')
        df_d['bopen_b'] = grouped['bopen'].first()
        df_d['bfirst_b'] = grouped['bfirst'].first()
        df_d['bigh_b'] = grouped['bhigh'].max()
        df_d['blow_b'] = grouped['blow'].min()        
        df_d['blast_b'] = grouped['blast'].last()
        df_d['iclose_b'] = grouped['iclose'].last()
        df_d['bvwap_b'] = grouped.apply(lambda x: (x['bvwap'] * x['bvolume'] / x['bvolume'].sum()).sum())
        df_d['bvolume_b'] = grouped['bvolume'].sum()
        df_d['btrades_b'] = grouped['btrades'].sum()
        df_d['meanSpread_b'] = grouped['meanSpread'].mean()
        df_d['meanEffectiveSpread_b'] = grouped['meanEffectiveSpread'].mean()
        df_d['meanBidSize_b'] = grouped['meanBidSize'].mean()
        df_d['meanAskSize_b'] = grouped['meanAskSize'].mean()
        df_d['bidHitTrades_b'] = grouped['bidHitTrades'].sum()
        df_d['midHitTrades_b'] = grouped['midHitTrades'].sum()
        df_d['askHitTrades_b'] = grouped['askHitTrades'].sum()
        df_d['bidHitDollars_b'] = grouped['bidHitDollars'].sum()
        df_d['midHitDollars_b'] = grouped['midHitDollars'].sum()
        df_d['askHitDollars_b'] = grouped['askHitDollars'].sum()
        df_d['outsideTrades_b'] = grouped['outsideTrades'].sum()
        df_d['outsideDollars_b'] = grouped['outsideDollars'].sum()

        df = pd.DataFrame(df_d)
        df = df.reset_index()
        agg_bars_dfs.append(df)
        t0 = t1
        t1 += timedelta(minutes=freq)

    agg_bars_df = pd.concat(agg_bars_dfs)
    agg_bars_df['insideness'] = np.log(agg_bars_df['meanEffectiveSpread']/agg_bars_df['meanSpread'])
    agg_bars_df['adj_trade_size'] = agg_bars_df['bvolume']/agg_bars_df['btrades'] / agg_bars_df['bvwap']
    agg_bars_df['spread_bps'] = agg_bars_df['meanSpread'] / agg_bars_df['bvwap']

    agg_bars_df['insideness_b'] = np.log(agg_bars_df['meanEffectiveSpread_b']/agg_bars_df['meanSpread_b'])
    agg_bars_df['adj_trade_size_b'] = agg_bars_df['bvolume_b']/agg_bars_df['btrades_b'] / agg_bars_df['bvwap_b']
    agg_bars_df['spread_bps_b'] = agg_bars_df['meanSpread_b'] / agg_bars_df['bvwap_b']

    return agg_bars_df

def load_bars(uni_df, start, end, cols=None, freq=30):
    if cols is not None:
        cols.extend( ['ticker', 'iclose_ts', 'iclose', 'date', 'gdate', 'giclose_ts'] )
    date = start
    result_dfs = list()
    uni_df = uni_df.reset_index()
    while ( date < end ):
        dateStr = date.strftime("%Y%m%d")
        bar_file = BAR_BASE_DIR + dateStr + "/bars.txt.gz"
        print("Loading {}".format(bar_file))
        try:
            bars_df = pd.read_csv(bar_file, compression='gzip', sep="|", header=None, names=['ticker', 'bopen_ts', 'iclose_ts', 'bopen', 'bfirst', 'bhigh', 'blow', 'blast', 'iclose', 'bvwap', 'bvolume', 'btrades', 'meanSpread', 'meanEffectiveSpread', 'meanBidSize', 'meanAskSize', 'bidHitTrades', 'midHitTrades', 'askHitTrades', 'bidHitDollars', 'midHitDollars', 'askHitDollars', 'outsideTrades', 'outsideDollars'], converters={'iclose_ts': fromtimestamp, 'bopen_ts': fromtimestamp}, na_values=['-1'])
        except IOError:
            print("File not found: {}".format(bar_file))
            date += timedelta(days=1)
            continue
        
        bars_df.set_index('iclose_ts', inplace=True)
        bars_df = bars_df.between_time('09:30:00', '16:00:00')
        bars_df = aggregate_bars(bars_df, freq)
        bars_df['giclose_ts'] = bars_df['iclose_ts']
        bars_df['date'] = bars_df['gdate'] = date
        if cols is not None:
            for col in bars_df.columns:
                if col not in cols: del bars_df[col]
        bars_df = pd.merge(uni_df[ uni_df['date'] == date ], bars_df, how='inner', left_on=['ticker'], right_on=['ticker'], sort=True, suffixes=['', '_dead'])
        result_dfs.append(bars_df)        
        date += timedelta(days=1)
    
    result_df = pd.concat(result_dfs)
    result_df.set_index(keys=['iclose_ts', 'sid'], inplace=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def load_earnings_dates(uni_df, start, end):
    date = start
    result_dfs = list()
    uni_df = uni_df.reset_index()
    while ( date < end ):
#        year = date.strftime("%Y")
        dateStr = date.strftime("%Y%m%d")
        earnings_dir = EARNINGS_BASE_DIR
        earnings_file = earnings_dir + "/" + dateStr + ".csv"
        try:
            df = pd.read_csv(earnings_file)
        except IOError:
            print("File not found: {}".format(earnings_file))
            date += timedelta(days=1)
            continue
 
        df['date'] = date
        df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
        result_dfs.append(df)
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs)
    result_df['earndate'] = pd.to_datetime(result_df['earn_rpt_date'].apply(str))
    f = lambda x: len(pd.bdate_range(x['date'], x['earndate']))
    result_df['daysToEarn'] = result_df.apply(f, axis=1)
    result_df.ix[ result_df['earn_rpt_time_norm'] == "AFTMKT", 'daysToEarn' ] = result_df.ix[ result_df['earn_rpt_time_norm'] == "AFTMKT", 'daysToEarn' ] + 1
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def load_past_earnings_dates(uni_df, start, end):
    date = start
    result_dfs = list()
    uni_df = uni_df.reset_index()
    while ( date < end ):
#        year = date.strftime("%Y")
        dateStr = date.strftime("%Y%m%d")
        earnings_dir = EARNINGS_BASE_DIR
        earnings_file = earnings_dir + "/" + dateStr 
        print(earnings_file)
        try:
            df = pd.read_csv(earnings_file)
        except IOError:
            print("File not found: {}".format(earnings_file))
            date += timedelta(days=1)
            continue
 
        df['date'] = date
        df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
        result_dfs.append(df)
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs)
    result_df = result_df.dropna(subset=['latest_earnings_date'])
    #ugh...
    result_df['latest_earnings_date'] = result_df['latest_earnings_date'].apply(str).str.replace("\.0", "")
    result_df['latest_earnings_date'] = pd.to_datetime(result_df['latest_earnings_date'])
    f = lambda x: len(pd.bdate_range(x['date'], x['latest_earnings_date']))
    result_df['daysFromEarn'] = result_df.apply(f, axis=1)
    result_df.set_index(keys=['date', 'sid'], inplace=True)
    result_df = remove_dup_cols(result_df)
    return result_df

def load_locates(uni_df, start, end):
    date = start
    result_dfs = list()
    uni_df = uni_df.reset_index()
    while ( date < end ):
#        year = date.strftime("%Y")
        dateStr = date.strftime("%Y%m%d")
        locates_dir = LOCATES_BASE_DIR
        locates_file = locates_dir + dateStr + ".csv"
        try:
            df = pd.read_csv(locates_file, usecols=['sid', 'qty', 'fee_rate'])
        except IOError:
            print("File not found: {}".format(locates_file))
            date += timedelta(days=1)
            continue
 
        df['date'] = date
        df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
        result_dfs.append(df)
        date += timedelta(days=1)

    result_df = pd.concat(result_dfs)
    result_df.set_index(['date', 'sid'], inplace=True)
    result_df['borrow_qty'] = -1 * result_df['qty']
    del result_df['qty']
    result_df = remove_dup_cols(result_df)
    return result_df
    
def load_merged_results(fdirs, start, end, cols=None):
    merged_df = None
    for fdir in fdirs:
        df = load_all_results(fdir, start, end, cols)

        if merged_df is None: 
            merged_df = df
        else:
            merged_df = pd.merge(merged_df, df, left_index=True, right_index=True, suffixes=['', '_dead'])
            merged_df = remove_dup_cols(merged_df)
    return merged_df

def load_mus(mdir, fcast, start, end):
    print("Looking in {}".format(mdir))
    fcast_dfs = list()
    for ff in sorted(glob.glob(mdir + "/"+ fcast + "/alpha.*")):
        m = re.match(r".*alpha\." + fcast + "\.(\d{8})_(\d{4}).*", str(ff))
        fdate = m.group(1)
        ftime = m.group(2)
        if int(ftime) <= 930 or int(ftime) >= 1600: continue
        if start is not None:
            if int(fdate) < int(start) or int(fdate) > int(end): continue
        print("Loading {} for {}".format(ff, fdate))            
        ts = dateparser.parse(fdate + " " + ftime)
        df = pd.read_csv(ff, header=0, parse_dates=True, sep=",")
        df['iclose_ts'] = ts
        df.set_index(['iclose_ts', 'sid'], inplace=True)
        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
    return fcast_df

def load_qb_implied_orders(mdir, start, end):
    print("Looking in {}".format(mdir))
    fcast_dfs = list()
    files = sorted(glob.glob(mdir + "/*.PORTFOLIO.csv"))
    for ff in files:
        m = re.match(r".*(\d{8}).PORTFOLIO.csv", str(ff))
        fdate = m.group(1)
        if start is not None:
            if int(fdate) < int(start) or int(fdate) > int(end): continue
        print("Loading {} for {}".format(ff, fdate))            
        df = pd.read_csv(ff, header=0, parse_dates=True, sep=",", usecols=['time', 'sid', 'ref_price', 'net_qty', 'open_long_amt', 'open_short_amt'], index=['time', 'sid'])

        df['open_order'] = (df['open_long_amt'] - df['open_short_amt']) / df['ref_price']
        result_l = list()
        for timeslice in ['10:02', '10:32', '11:02', '11:32', '12:02', '12:32', '13:02', '13:32', '14:02', '14:32', '15:02', '15:32' ]:
            timeslice_df = df.unstack().between_time(timeslice, timeslice).stack()
            result_l.append(timeslice_df)
        df = pd.concat(result_l)        

        df['iclose_ts'] = pd.to_datetime(fdate + " " + df['time'])
        df['iclose_ts'] = df['iclose_ts'] - timedelta(minutes=2)
        df = df.reset_index().set_index(['iclose_ts', 'sid'])
        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
    return fcast_df

def load_qb_positions(mdir, start, end):
    print("Looking in {}".format(mdir))
    fcast_dfs = list()
    files = sorted(glob.glob(mdir + "/*.csv"))
    for ff in files:
        m = re.match(r".*(\d{8}).PORTFOLIO.csv", str(ff))
        fdate = m.group(1)
        if start is not None:
            if int(fdate) < int(start) or int(fdate) > int(end): continue
        print("Loading {} for {}".format(ff, fdate))            
        df = pd.read_csv(ff, header=0, parse_dates=True, sep=",", usecols=['time', 'sid', 'ref_price', 'net_qty', 'open_long_amt', 'open_short_amt'])

        df['iclose_ts'] = pd.to_datetime(fdate + " " + df['time'])
        df.set_index(['iclose_ts', 'sid'], inplace=True)
        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
    return fcast_df

def load_qb_eods(mdir, start, end):
    print("Looking in {}".format(mdir))
    fcast_dfs = list()
    files = sorted(glob.glob(mdir + "/.csv"))
    for ff in files:
        m = re.match(r".*(\d{8}).EOD.csv", str(ff))
        fdate = m.group(1)
        if start is not None:
            if int(fdate) < int(start) or int(fdate) > int(end): continue
        print("Loading {} for {}".format(ff, fdate))            
        df = pd.read_csv(ff, header=0, parse_dates=True, sep=",", usecols=['time', 'sid', 'ref_price', 'today_long', 'today_short'])
        df['iclose_ts'] = pd.to_datetime(fdate + " 16:00:00")
        df.set_index(['iclose_ts', 'sid'], inplace=True)
        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
    fcast_df['dtradenot'] = fcast_df['today_long'] - fcast_df['today_short']
    return fcast_df

def load_qb_orders(ofile, date):
    df = pd.read_csv(ofile, usecols=['time', 'symbol', 'sid', 'id', 'side', 'qty', 'px', 'state'])
    df = df[ df['state'] == "NEW" ]
    df['ts'] = pd.to_datetime( date + " " + df['time'])
    df['ts'] = df['ts'] - timedelta(minutes=1, seconds=1)
    df.set_index(['ts', 'sid'], inplace=True)
    del df['time']
    del df['state']
    df.ix[ df['side'] == "Short", 'qty' ] = -1 * df['qty'] 
    df.ix[ df['side'] == "SellShort", 'qty' ] = -1 * df['qty'] 
    del df['side']
    return df

def load_qb_exec(efile, date):
    df = pd.read_csv(efile, usecols=['time', 'symbol', 'sid', 'order_id', 'side', 'qty', 'px'])
    df['ts'] = pd.to_datetime( date + " " + df['time'])
    del df['time']
    df.ix[ df['side'] == "Short", 'qty' ] = -1 * df['qty'] 
    df.ix[ df['side'] == "SellShort", 'qty' ] = -1 * df['qty'] 
    del df['side']
    return df


def load_factor_cache(start, end):
    dfs = list()
    for ff in sorted(glob.glob(os.environ['CACHE_DIR'] + "/all.factors.*")):
        m = re.match(r".*all\.factors\.(\d{8})-(\d{8}).h5", str(ff))
        if m is None: continue
        d1 = dateparser.parse(m.group(1))
        d2 = dateparser.parse(m.group(2))
        if d2 < start or d1 > end: continue
        print("Loading {}".format(ff))
        df = pd.read_hdf(ff, 'table')
        df = df.truncate(before=start - timedelta(days=30), after=end)
        if len(df) > 0:
            dfs.append(df)
           
    result_df = pd.DataFrame()
    for df in dfs:
        result_df = result_df.combine_first(df)

    result_df.index.names = ['date', 'factor']
    print(result_df.columns)
    return result_df

def load_cache(start, end, cols=None):
    dfs = list()
    for ff in sorted(glob.glob(os.environ['CACHE_DIR'] + "/all.2*")):
        m = re.match(r".*all\.(\d{8})-(\d{8}).h5", str(ff))
        if m is None: continue
        d1 = dateparser.parse(m.group(1))
        d2 = dateparser.parse(m.group(2))
        if d2 < start or d1 > end: continue
        print("Loading {}".format(ff))
        df = pd.read_hdf(ff, 'table')
        if cols is not None:
            df = df[cols]
#        df = df.truncate(before=start, after=end)
        if len(df) > 0:
            dfs.append(df)
           
    result_df = pd.DataFrame()
    for df in dfs:
        result_df = result_df.combine_first(df)

#    result_df = result_df.truncate(before=start, after=end)
    result_df.index.names = ['iclose_ts', 'sid']
    return result_df

def load_all_results(fdir, start, end, cols=None):
    fdir += "/all/"    
    print("Looking in {}".format(fdir))
    fcast_dfs = list()
    for ff in sorted(glob.glob(fdir + "/alpha.*")):
        m = re.match(r".*alpha\.all\.(\d{8})_(\d{4}).*", str(ff))
        fdate = int(m.group(1))
        ftime = int(m.group(2))
        if ftime < 1000 or ftime > 1530: continue
        if fdate < int(start) or fdate > int(end): continue
        print("Loading {} for {}".format(ff, fdate))    
        
        if cols is not None:
            df = pd.read_csv(ff, index_col=['iclose_ts', 'sid'], header=0, parse_dates=True, sep=",", usecols=cols)
        else:
            df = pd.read_csv(ff, index_col=['iclose_ts', 'sid'], header=0, parse_dates=True, sep=",")

        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)

    return fcast_df

BARRA_INDS = ['indname1', 'wgt1', 'indname2', 'wgt2', 'indname3', 'wgt3', 'indname4', 'wgt4', 'indname5', 'wgt5']

def transform_barra(barra_df):
    print("Transforming barra data...")
    barra1_df = barra_df[ ['indname1', 'wgt1'] ].dropna()
    barra2_df = barra_df[ ['indname2', 'wgt2'] ].dropna()
    barra3_df = barra_df[ ['indname3', 'wgt3'] ].dropna()
    barra4_df = barra_df[ ['indname4', 'wgt4'] ].dropna()
    barra5_df = barra_df[ ['indname5', 'wgt5'] ].dropna()

    barra1_df.set_index('indname1', append=True, inplace=True)
    barra2_df.set_index('indname2', append=True, inplace=True)
    barra3_df.set_index('indname3', append=True, inplace=True)
    barra4_df.set_index('indname4', append=True, inplace=True)
    barra5_df.set_index('indname5', append=True, inplace=True)

    pivot1_df = barra1_df['wgt1'].unstack('indname1').fillna(0)
    pivot2_df = barra2_df['wgt2'].unstack('indname2').fillna(0)
    pivot3_df = barra3_df['wgt3'].unstack('indname3').fillna(0)
    pivot4_df = barra4_df['wgt4'].unstack('indname4').fillna(0)
    pivot5_df = barra5_df['wgt5'].unstack('indname5').fillna(0)

    #    pivot_df = barra_df.pivot( index=['date', 'sid'], columns='indname1', values='wgt1')
    
    pivot_df = pivot1_df.add(pivot2_df, fill_value=0)
    pivot_df = pivot_df.add(pivot3_df, fill_value=0)
    pivot_df = pivot_df.add(pivot4_df, fill_value=0)
    pivot_df = pivot_df.add(pivot5_df, fill_value=0)

    barra_df = pd.merge( barra_df, pivot_df, how='left', left_index=True, right_index=True)
    del barra_df['indname2']
    del barra_df['indname3']
    del barra_df['indname4']
    del barra_df['indname5']
    del barra_df['wgt1']
    del barra_df['wgt2']
    del barra_df['wgt3']
    del barra_df['wgt4']
    del barra_df['wgt5']

    return barra_df

def load_ratings_hist(uni_df, start, end, intra=False):
    if intra:
        times = ['09:45', '10:00', '10:15', '10:30', '10:45', '11:00', '11:15', '11:30', '11:45', '12:00', '12:15', '12:30', '12:45', '13:00', '13:15', '13:30', '13:45', '14:00', '14:15', '14:30', '14:45', '15:00', '15:15', '15:30', '15:45', '16:00' ]
    else:
        if end.hour > 0:
            times = [ str(end.hour) + ":" + str(end.minute) ]
        else:
            times = ['16:00']

    window = timedelta(days=252)
    con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
    date = start
    df_list = list()
    uni_df = uni_df.reset_index()
    while (date < end):
        
        if date.day == end.day:
            times = [ str(end.hour-3) + ":" + str(end.minute) ]
        else:
            times = ['16:00']

        endDateStr = date.strftime('%Y%m%d')
        startDateStr = (date - window).strftime('%Y%m%d')
        for time in times:            
#            timeAdjusted = str(int(time.split(":")[0]) - 3) + ":" + time.split(":")[1] 
            sql = "select * from t_ibes_hist_rec_snapshot where timestamp between '{} {}' and '{} {}' group by sid, ibes_ticker, estimator having timestamp = max(timestamp)".format(startDateStr, time, endDateStr, time)
            print(sql)
            df = psql.frame_query(sql, con)
            df = df[ df['ibes_rec_code'] != '' ]
            #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
            df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
            df['ibes_rec_code'] = df['ibes_rec_code'].astype(int)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(df.columns)
            df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
            if intra:
                df['iclose_ts'] = pd.to_datetime(endDateStr + " " + time)
                df = df.set_index(['iclose_ts', 'sid'])
            else:
                df = df.set_index(['date', 'sid'])
            df_list.append(df)
            date += timedelta(days=1)

    df = pd.concat(df_list)
    if intra: 
        tstype = 'iclose_ts'
    else:
        tstype = 'date'

    #consensus
    result_df = df.groupby(level=[tstype, 'sid']).agg({'ibes_rec_code' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
    result_df.columns = result_df.columns.droplevel(0)
    for column in result_df.columns:
        result_df.rename(columns={column: 'rating_' + column}, inplace=True)

    df = df.set_index('estimator', append=True)
    df2 = df['ibes_rec_code'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
    #should drop first date here
    df2 = df2[ df2 != 0 ]
    df2 = df2.reset_index('estimator').groupby(level=[tstype, 'sid']).agg(np.mean)
    df2.columns = ['rating_diff_mean']

    result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

    return result_df

def load_target_hist(uni_df, start, end, intra=False):
    window = timedelta(days=252)
    con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
    date = start

    df_list = list()
    uni_df = uni_df.reset_index()
    while (date < end):

        if date.day == end.day:
            times = [ str(end.hour - 3) + ":" + str(end.minute) ]
        else:
            times = ['16:00']

        endDateStr = date.strftime('%Y%m%d')
        startDateStr = (date - window).strftime('%Y%m%d')
        for time in times:            
            #timeAdjusted = str(int(time.split(":")[0]) - 3) + ":" + time.split(":")[1] 
            sql = "select * from t_ibes_hist_ptg_snapshot where timestamp between '{} {}' and '{} {}' and horizon in ('', 12) and value > 0 group by sid, ibes_ticker, estimator having timestamp = max(timestamp)".format(startDateStr, time, endDateStr, time)
            print(sql)
            df = psql.frame_query(sql, con)
            df['value'] = df['value'].astype(str)
            df = df[ df['value'] != '' ]
            #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
            df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
            df['value'] = df['value'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            del df['horizon']
            print(df.columns)
            df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
            df = df.set_index(['date', 'sid'])
            df_list.append(df)
            date += timedelta(days=1)

    df = pd.concat(df_list)

    #consensus
    result_df = df.groupby(level=['date', 'sid']).agg({'value' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
    result_df.columns = result_df.columns.droplevel(0)
    for column in result_df.columns:
        result_df.rename(columns={column: 'target_' + column}, inplace=True)

    #detailed
    df = df.set_index('estimator', append=True)
    df2 = df['value'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
    df2 = df2[ df2 != 0 ]
    df2 = df2.reset_index('estimator').groupby(level=['date', 'sid']).agg(np.mean)
    df2.columns = ['target_diff_mean']

    result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

    return result_df

def load_estimate_hist(uni_df, start, end, estimate):
    window = timedelta(days=252)
    con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
    date = start

    df_list = list()
    uni_df = uni_df.reset_index()
    while (date < end):
        if date.day == end.day:
            times = [ str(end.hour - 3) + ":" + str(end.minute) ]
        else:
            times = ['16:00']
        endDateStr = date.strftime('%Y%m%d')
        startDateStr = (date - window).strftime('%Y%m%d')
        for time in times:            
            minPeriod = str(int(endDateStr[2:4])) + endDateStr[4:6]
            maxPeriod = str(int(endDateStr[2:4]) + 2) + "00"
            sql = "select * from t_ibes_det_snapshot where timestamp between '{} {}' and '{} {}' and measure = '{}' and forecast_period_ind = 1 and forecast_period_end_date > {} and forecast_period_end_date < {} group by sid, ibes_ticker, estimator, forecast_period_ind, forecast_period_end_date having timestamp = max(timestamp) order by sid, forecast_period_end_date;".format(startDateStr, time, endDateStr, time, estimate, minPeriod, maxPeriod)
            print(sql)
            df = psql.frame_query(sql, con)
            df['value'] = df['value'].astype(str)
            df = df[ df['value'] != '' ]
            #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
            df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
            df['value'] = df['value'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(df.columns)
            df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
            df = df[ ~df.duplicated(cols=['date', 'sid', 'estimator']) ]
            df = df.set_index(['date', 'sid'])
            df_list.append(df)
            date += timedelta(days=1)

    df = pd.concat(df_list)
    print("DFEPS")
    print(df)
    #consensus
    result_df = df.groupby(level=['date', 'sid']).agg({'value' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
    result_df.columns = result_df.columns.droplevel(0)
    for column in result_df.columns:
        result_df.rename(columns={column: estimate + '_' + column}, inplace=True)

    #detailed
    df = df.set_index('estimator', append=True)
    print("SEAN2")
    print(df.head())
    df2 = df['value'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
    df2 = df2[ df2 != 0 ]
    df2 = df2.reset_index('estimator').groupby(level=['date', 'sid']).agg(np.mean)
    del df2['estimator']
    df2.columns = [estimate + '_diff_mean']

    result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

    return result_df

    
def load_consensus(dtype, uni_df, start, end, freq='30Min'):
    date = start
    df_list = list()
    while (date < end ):
        dateStr = date.strftime('%Y%m%d')
        year = dateStr[0:4]
        est_dir = ESTIMATES_BASE_DIR + year
        est_files = est_dir + "/" + dateStr
        for rfile in sorted(glob.glob(est_files)):
            df = pd.read_csv(rfile)
            #        df['ts'] = pd.to_datetime( df['received_time'] )
            df['ts'] = pd.to_datetime( df['vendor_time'] )
            df = df.set_index(['sid', 'ts'])
            df_list.append(df)

    df = pd.concat(df_list)
    sid_groups = df.groupby(level=0)
    sid_dfs = list()
    for name, group in sid_groups:
        resampled_df = group.reset_index(level=0).resample(freq, how='last', fill_method='pad', closed='left', label='right')
        sid_dfs.append(resampled_df)

    rtg_df = pd.concat(sid_dfs)
    return rtg_df

