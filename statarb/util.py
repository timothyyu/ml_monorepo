import sys
import os
import glob
import argparse
import re
import math
from collections import defaultdict
from dateutil import parser as dateparser

import time
from datetime import datetime
from datetime import timedelta

import numpy as np
import pandas as pd

import os, errno

testid = '001075'  # new #previous is 001045
testid2 = '143356'  # new

def merge_barra_data(price_df, barra_df):
    barra_df = barra_df.unstack(level=-1).shift(1).stack()
    full_df = pd.merge(price_df, barra_df, left_index=True, right_index=True, sort=True, suffixes=['', '_dead'])
    full_df = remove_dup_cols(full_df)
    return full_df


def remove_dup_cols(result_df):
    for col in result_df.columns:
        if col.endswith("_dead"):
            del result_df[col]
    return result_df


def merge_intra_eod(daily_df, intra_df):
    print("Merging EOD bar data...")
    eod_df = intra_df.unstack().at_time('16:00').stack()
    merged_df = pd.merge(daily_df.reset_index(), eod_df.reset_index(), left_on=['date', 'gvkey'],
                         right_on=['date', 'gvkey'], sort=True, suffixes=['', '_eod'])
    merged_df = remove_dup_cols(merged_df)
    del merged_df['ticker_eod']
    merged_df.set_index(['date', 'gvkey'], inplace=True)
    return merged_df


def merge_intra_data(daily_df, intra_df):
    print("Merging intra data...")
    merged_df = pd.merge(intra_df.reset_index(), daily_df.reset_index(), how='left', left_on=['date', 'gvkey'],
                         right_on=['date', 'gvkey'], sort=False, suffixes=['', '_dead'])
    merged_df = remove_dup_cols(merged_df)
    merged_df.set_index(['iclose_ts', 'gvkey'], inplace=True)
    return merged_df


def filter_expandable(df):
    origsize = len(df)
    result_df = df.dropna(subset=['expandable'])
    result_df = result_df[result_df['expandable']]
    newsize = len(result_df)
    print("Restricting forecast to expandables: {} -> {}".format(origsize, newsize))
    return result_df


def filter_pca(df):
    origsize = len(df)
    result_df = df[df['mkt_cap'] > 1e10]
    newsize = len(result_df)
    print("Restricting forecast to expandables: {} -> {}".format(origsize, newsize))
    return result_df


def dump_hd5(result_df, name):
    result_df.to_hdf(name + "." + df_dates(result_df) + ".h5", 'table', complib='zlib')


def dump_all(results_df):
    print("Dumping alpha files...")
    results_df = results_df.reset_index()
    groups = results_df['iclose_ts'].unique()
    for group in groups:
        if str(group) == 'NaT': continue
        print("Dumping group: {}".format(str(group)))
        date_df = results_df[results_df['iclose_ts'] == group]
        if not len(date_df) > 0:
            print("No data found at ts: {}".format(str(group)))
            continue
        try:
            os.mkdir("all")
        except:
            pass
        filename = "./all/alpha.all." + pd.to_datetime(group).strftime('%Y%m%d_%H%M') + ".csv"
        date_df.to_csv(filename, index=False);


def dump_alpha(results_df, name):
    print("Dumping alpha files...")
    results_df = results_df.reset_index()
    groups = results_df['iclose_ts'].unique()

    results_df = results_df[['gvkey', 'iclose_ts', name]]
    for group in groups:
        if str(group) == 'NaT': continue

        print("Dumping group: {}".format(str(group)))
        date_df = results_df[results_df['iclose_ts'] == group]
        if not len(date_df) > 0:
            print("No data found at ts: {}".format(str(group)))
            continue
        try:
            os.mkdir(name)
        except:
            pass
        filename = "./" + name + "/alpha." + name + "." + pd.to_datetime(group).strftime('%Y%m%d_%H%M') + ".csv"
        date_df.to_csv(filename, index=False, cols=['gvkey', name], float_format="%.6f")


def dump_alpha(results_df, name):
    print("Dumping alpha files...")
    results_df = results_df.reset_index()
    groups = results_df['iclose_ts'].unique()

    results_df = results_df[['gvkey', 'iclose_ts', name]]
    for group in groups:
        if str(group) == 'NaT': continue

        print("Dumping group: {}".format(str(group)))
        date_df = results_df[results_df['iclose_ts'] == group]
        if not len(date_df) > 0:
            print("No data found at ts: {}".format(str(group)))
            continue
        try:
            os.mkdir(name)
        except:
            pass
        filename = "./" + name + "/alpha." + name + "." + pd.to_datetime(group).strftime('%Y%m%d_%H%M') + ".csv"
        date_df.to_csv(filename, index=False, cols=['gvkey', name], float_format="%.6f")


def dump_prod_alpha(results_df, name, outputfile):
    print("Dumping alpha files...")
    results_df = results_df.reset_index()
    group = results_df['date'].unique().max()
    results_df = results_df[['gvkey', 'date', name]]
    date_df = results_df[results_df['date'] == group]
    date_df.to_csv(outputfile, index=False, cols=['gvkey', name], float_format="%.6f")


def dump_daily_alpha(results_df, name):
    print("Dumping daily alpha files...")
    results_df = results_df.reset_index()
    groups = results_df['date'].unique()

    results_df = results_df[['gvkey', 'date', name]]
    for group in groups:
        if str(group) == 'NaT': continue

        print("Dumping group: {}".format(str(group)))
        date_df = results_df[results_df['date'] == group]
        if not len(date_df) > 0:
            print("No data found at ts: {}".format(str(group)))
            continue
        try:
            os.mkdir(name)
        except:
            pass

        for stime in ['0930', '0945', '1000', '1015', '1030', '1045', '1100', '1115', '1130', '1145', '1200', '1215',
                      '1230', '1245', '1300', '1315', '1330', '1345', '1400', '1415', '1430', '1445', '1500', '1515',
                      '1530', '1545']:
            filename = "./" + name + "/alpha." + name + "." + pd.to_datetime(group).strftime(
                '%Y%m%d_' + str(stime)) + ".csv"
            date_df.to_csv(filename, index=False, cols=['gvkey', name], float_format="%.6f")


def df_dates(df):
    return df.index[0][0].strftime("%Y%m%d") + "-" + df.index[-1][0].strftime("%Y%m%d")
    # new: if hl.py runs on raw data, no strftime


def merge_daily_calcs(full_df, result_df):
    rcols = set(result_df.columns)
    cols = list(rcols - set(full_df.columns))
    result_df = result_df.reset_index()
    full_df = full_df.reset_index()
    cols.extend(['date', 'gvkey'])
    print("Merging daily results: " + str(cols))
    result_df = pd.merge(full_df, result_df[cols], how='left', left_on=['date', 'gvkey'], right_on=['date', 'gvkey'],
                         sort=False, suffixes=['_dead', ''])
    result_df.set_index(['date', 'gvkey'], inplace=True)
    return result_df


def merge_intra_calcs(full_df, result_df):
    # important for keeping NaTs out of the following merge
    del result_df['date']
    rcols = set(result_df.columns)
    cols = list(rcols - set(full_df.columns))
    print("Merging intra results: " + str(cols))
    result_df = pd.merge(full_df, result_df[cols], how='left', left_index=True, right_index=True, sort=False,
                         suffixes=['_dead', ''])
    return result_df


def get_overlapping_cols(df1, df2):
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    res = cols1 - cols1.intersection(cols2)
    return list(res)


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
            df = pd.read_csv(ff, index_col=['iclose_ts', 'gvkey'], header=0, parse_dates=True, sep=",", usecols=cols)
        else:
            df = pd.read_csv(ff, index_col=['iclose_ts', 'gvkey'], header=0, parse_dates=True, sep=",")

        fcast_dfs.append(df)

    fcast_df = pd.concat(fcast_dfs, verify_integrity=True)

    return fcast_df
