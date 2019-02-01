import sys
import glob
import re
import math
from util import *
import pandas as pd
import time
from datetime import datetime
from datetime import timedelta
import numpy as np
import os
from dateutil import parser as dateparser


def load_mus(mdir, fcast, start, end):
    print("Looking in {}".format(mdir))
    fcast_dfs = []
    for ff in sorted(glob.glob(mdir + "/" + fcast + "/alpha.*")):
        m = re.match(r".*alpha\." + fcast + "\.(\d{8})-(\d{8}).csv", str(ff))
        d1 = m.group(1)
        d2 = m.group(2)
        if start is not None:
            if d2 <= start or d1 >= end: continue
        print("Loading {} from {} to {}".format(ff, d1, d2))
        df = pd.read_csv(ff, header=0, parse_dates=['date'], dtype={'gvkey': str})
        df.set_index(['date', 'gvkey'], inplace=True)
        fcast_dfs.append(df)
    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)
    return fcast_df


def load_cache(start, end, data_dir, cols=None):
    result_df = pd.DataFrame()
    for ff in sorted(glob.glob(data_dir + "/all/all.*")):
        m = re.match(r".*all\.(\d{8})-(\d{8}).h5", str(ff))
        if m is None: continue
        d1 = dateparser.parse(m.group(1))
        d2 = dateparser.parse(m.group(2))
        if d2 <= start or d1 >= end: continue
        print("Loading {}".format(ff))
        df = pd.read_hdf(ff, 'full_df')
        if cols is not None:
            df = df[cols]
        #        df = df.truncate(before=start, after=end)
        result_df = result_df.append(df)
    #    result_df = result_df.truncate(before=start, after=end)
    result_df.index.names = ['date', 'gvkey']
    return result_df


def load_factor_cache(start, end, data_dir):
    dfs = []
    for ff in sorted(glob.glob(data_dir + "/all/all.*")):
        m = re.match(r".*all\.(\d{8})-(\d{8}).h5", str(ff))
        if m is None: continue
        d1 = dateparser.parse(m.group(1))
        d2 = dateparser.parse(m.group(2))
        if d2 <= start or d1 >= end: continue
        print("Loading {}".format(ff))
        df = pd.read_hdf(ff, 'full_df')
        df = df.truncate(before=start - timedelta(days=30), after=end)
        if len(df) > 0:
            dfs.append(df)
    result_df = pd.DataFrame()
    for df in dfs:
        result_df = result_df.append(df)
    result_df.index.names = ['date', 'factor']
    return result_df


def load_locates(uni_df, start, end, locates_dir):
    uni_df = uni_df.reset_index()
    monday_st = start - timedelta(days=start.weekday())
    monday_ed = end - timedelta(days=end.weekday())
    ff = locates_dir + "/locates/borrow.csv"
    print("Loading", ff)
    result_df = pd.read_csv(ff, parse_dates=['date'], usecols=['symbol','sedol', 'date', 'shares', 'fee'], sep='|')
    result_df = result_df.loc[(result_df['date'] >= monday_st) & (result_df['date'] <= monday_ed)]
    # because we have limited borrow data
    borrow_st = result_df['date'].min()
    borrow_ed = result_df['date'].max()
    borrow_ed += timedelta(days=6-borrow_ed.weekday())
    result_df[['borrow_qty','fee']] = -1 * result_df[['shares','fee']]
    del result_df['shares']
    sedol_df = pd.merge(result_df, uni_df[['gvkey', 'sedol']].drop_duplicates(), on=['sedol'])
    symbol_df = pd.merge(result_df, uni_df[['gvkey', 'symbol']].drop_duplicates(), on=['symbol'])
    result_df = pd.merge(symbol_df, sedol_df, on=['date', 'gvkey'], how='outer', suffixes=['', '_dead'])
    result_df[['borrow_qty','fee']].fillna(result_df[['borrow_qty_dead','fee_dead']], inplace=True)
    result_df = result_df[['date','gvkey','borrow_qty','fee']]
    result_df = pd.merge(uni_df, result_df, on=['date', 'gvkey'], how='outer')
    result_df = result_df.sort_values(by=['gvkey', 'date']).groupby(['gvkey'], as_index=False).fillna(method='ffill')
    result_df[['borrow_qty','fee']] = result_df[['borrow_qty','fee']].fillna(0)
    # limited borrow data
    result_df.loc[(result_df['date'] <= borrow_st) & (result_df['date'] >= borrow_ed), ['borrow_qty','fee']] =[-np.inf,-0]
    result_df.set_index(['date', 'gvkey'], inplace=True)
    return result_df
