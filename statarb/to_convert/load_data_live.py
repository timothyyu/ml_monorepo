#!/usr/bin/env python

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

fromtimestamp = lambda x:datetime.fromtimestamp(int(x) / 1000.)

UNBIAS = 3

def load_live_file(ifile):
    df = pd.read_csv(ifile, header=0, index_col=['sid'])
    df['close_i'] = (df['bid'] + df['ask']) / 2.0
    return df

# def load_secdata(uni_df, start, end):
#     year = end.strftime("%Y")

#     secdata_dir = SECDATA_BASE_DIR + year
#     secdata_file = secdata_dir + "/" + unidate + ".estu.csv.gz"
#     secdata_df = pd.read_csv(secdata_file, header=0, compression='gzip', usecols=['sid', 'sector_name'], index_col=['sid'])
#     univ_df = pd.merge(uni_df, secdata_df, how='inner', left_index=True, right_index=True, sort=True)
#     print "Universe size (secdata): {}".format(len(univ_df.index))    
    
#     return univ_df

# def load_ratings_prod_hist(uni_df, start, end_ts):
#     window = timedelta(days=252)
#     con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
#     date = start
#     df_list = list()
#     uni_df = uni_df.reset_index()
#     while (date <= end_ts):
#         endDateStr = date.strftime('%Y%m%d')
#         startDateStr = (date - window).strftime('%Y%m%d')

#         if date == end_ts:
#             time = end_ts.strftime("%H:%M")
#         else:
#             time = '16:00'

#         timeAdjusted = str(int(time.split(":")[0]) - UNBIAS) + ":" + time.split(":")[1] 
#         sql = "select * from t_ibes_hist_rec_snapshot where timestamp between '{} {}' and '{} {}' group by sid, ibes_ticker, estimator having timestamp = max(timestamp)".format(startDateStr, time, endDateStr, timeAdjusted)
#         print sql
#         df = psql.frame_query(sql, con)
#         df = df[ df['ibes_rec_code'] != '' ]
#         #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
#         df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
#         df['ibes_rec_code'] = df['ibes_rec_code'].astype(int)
#         df['timestamp'] = pd.to_datetime(df['timestamp'])
#         print df.columns
#         df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
#         df = df.set_index(['date', 'sid'])
#         df_list.append(df)
#         date += timedelta(days=1)

#     df = pd.concat(df_list)
#     tstype = 'date'

#     #consensus
#     result_df = df.groupby(level=[tstype, 'sid']).agg({'ibes_rec_code' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
#     result_df.columns = result_df.columns.droplevel(0)
#     for column in result_df.columns:
#         result_df.rename(columns={column: 'rating_' + column}, inplace=True)

#     df = df.set_index('estimator', append=True)
#     df2 = df['ibes_rec_code'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
#     #should drop first date here
#     df2 = df2[ df2 != 0 ]
#     df2 = df2.reset_index('estimator').groupby(level=[tstype, 'sid']).agg(np.mean)
#     df2.columns = ['rating_diff_mean']

#     result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

#     return result_df


# def load_target_prod_hist(uni_df, start, end_ts):
#     window = timedelta(days=252)
#     con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
#     date = start
#     df_list = list()
#     uni_df = uni_df.reset_index()
#     while (date < end_ts):
#         endDateStr = date.strftime('%Y%m%d')
#         startDateStr = (date - window).strftime('%Y%m%d')

#         if date == end_ts:
#             time = end_ts.strftime("%H:%M")
#         else:
#             time = '16:00'

#         timeAdjusted = str(int(time.split(":")[0]) - UNBIAS) + ":" + time.split(":")[1] 
#         sql = "select * from t_ibes_hist_ptg_snapshot where timestamp between '{} {}' and '{} {}' and horizon in ('', 12) and value > 0 group by sid, ibes_ticker, estimator having timestamp = max(timestamp)".format(startDateStr, time, endDateStr, timeAdjusted)
#         print sql
#         df = psql.frame_query(sql, con)
#         df['value'] = df['value'].astype(str)
#         df = df[ df['value'] != '' ]
#         #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
#         df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
#         df['value'] = df['value'].astype(float)
#         df['timestamp'] = pd.to_datetime(df['timestamp'])
#         del df['horizon']
#         print df.columns
#         df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
#         df = df.set_index(['date', 'sid'])
#         df_list.append(df)
#         date += timedelta(days=1)

#     df = pd.concat(df_list)

#     #consensus
#     result_df = df.groupby(level=['date', 'sid']).agg({'value' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
#     result_df.columns = result_df.columns.droplevel(0)
#     for column in result_df.columns:
#         result_df.rename(columns={column: 'target_' + column}, inplace=True)

#     #detailed
#     df = df.set_index('estimator', append=True)
#     df2 = df['value'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
#     df2 = df2[ df2 != 0 ]
#     df2 = df2.reset_index('estimator').groupby(level=['date', 'sid']).agg(np.mean)
#     df2.columns = ['target_diff_mean']

#     result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

#     return result_df


# def load_estimate_prod_hist(uni_df, start, end_ts, estimate):
#     window = timedelta(days=252)
#     con = lite.connect(ESTIMATES_BASE_DIR + "ibes.db")    
#     date = start
#     df_list = list()
#     uni_df = uni_df.reset_index()
#     while (date < end_ts):
#         endDateStr = date.strftime('%Y%m%d')
#         startDateStr = (date - window).strftime('%Y%m%d')

#         if date == end_ts:
#             time = end_ts.strftime("%H:%M")
#         else:
#             time = '16:00'

#         timeAdjusted = str(int(time.split(":")[0]) - UNBIAS) + ":" + time.split(":")[1] 
#         minPeriod = str(int(endDateStr[2:4])) + endDateStr[4:6]
#         maxPeriod = str(int(endDateStr[2:4]) + 2) + "00"
#         sql = "select * from t_ibes_det_snapshot where timestamp between '{} {}' and '{} {}' and measure = '{}' and forecast_period_ind = 1 and forecast_period_end_date > {} and forecast_period_end_date < {} group by sid, ibes_ticker, estimator, forecast_period_ind, forecast_period_end_date having timestamp = max(timestamp) order by sid, forecast_period_end_date;".format(startDateStr, time, endDateStr, timeAdjusted, estimate, minPeriod, maxPeriod)
#         print sql
#         df = psql.frame_query(sql, con)
#         df['value'] = df['value'].astype(str)
#         df = df[ df['value'] != '' ]
#         #            df['ts'] = pd.to_datetime( date.strftime("%Y%m%d") + " " + time )
#         df['date'] = pd.to_datetime( date.strftime("%Y%m%d") )
#         df['value'] = df['value'].astype(float)
#         df['timestamp'] = pd.to_datetime(df['timestamp'])
#         print df.columns
#         df = pd.merge(uni_df[ uni_df['date'] == date ], df, how='inner', left_on=['sid'], right_on=['sid'], sort=True, suffixes=['', '_dead'])
#         df = df[ ~df.duplicated(cols=['date', 'sid', 'estimator']) ]
#         df = df.set_index(['date', 'sid'])
#         df_list.append(df)
#         date += timedelta(days=1)

#     df = pd.concat(df_list)
#     #consensus
#     result_df = df.groupby(level=['date', 'sid']).agg({'value' : [np.mean, np.median, np.std, 'count', np.max, np.min], 'timestamp' : 'last'})
#     result_df.columns = result_df.columns.droplevel(0)
#     for column in result_df.columns:
#         result_df.rename(columns={column: estimate + '_' + column}, inplace=True)

#     #detailed
#     df = df.set_index('estimator', append=True)
#     df2 = df['value'].unstack(['estimator', 'sid']).fillna(0).diff().iloc[1:].stack(['sid', 'estimator'])
#     df2 = df2[ df2 != 0 ]
#     df2 = df2.reset_index('estimator').groupby(level=['date', 'sid']).agg(np.mean)
#     del df2['estimator']
#     df2.columns = [estimate + '_diff_mean']

#     result_df = pd.merge(result_df, df2, left_index=True, right_index=True, how='left')

#     return result_df
