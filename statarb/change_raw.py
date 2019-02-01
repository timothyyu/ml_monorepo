import pandas as pd
import time
from datetime import datetime
from datetime import timedelta
import numpy as np
import os
import glob
import re
import mysql.connector
import pyodbc
import argparse
from mktcalendar import *


def add_mktcap(uni_df, price_df, start, end, out_dir):
    date = end - TDay
    sql = ("SELECT DISTINCT g.gvkey, t.tradingItemId 'tid', m.pricingDate 'date',"
           " m.marketCap 'mkt_cap'"
           " FROM ciqTradingItem t"
           " INNER JOIN ciqGvKeyIID g ON g.objectId = t.tradingItemId"
           " INNER JOIN ciqSecurity s ON t.securityId = s.securityId"
           " INNER JOIN ciqMarketCap m ON s.companyId = m.companyId"
           " WHERE m.pricingDate BETWEEN '%s' AND '%s'"
           " AND g.gvkey IN %s"
           " AND t.tradingItemId In %s"
           % (start, date, tuple(uni_df.index.values), tuple(uni_df['tid'].values)))
    cnxn_s = 'Trusted_Connection=yes;Driver={ODBC Driver 17 for SQL Server};Server=dbDevCapIq;Database=xpressfeed'
    cnxn = pyodbc.connect(cnxn_s)
    add_df = pd.read_sql(sql, cnxn)
    cnxn.close()
    add_df = pd.merge(uni_df[['tid']], add_df, on=['gvkey', 'tid'])
    price_df = pd.merge(price_df, add_df, on=['date', 'gvkey', 'tid'])
    price_df.set_index(['date', 'gvkey'], inplace=True)

    end_s = end.strftime("%Y%m%d")
    dir = '%s/%s/' % (out_dir, end_s)
    print("price_df added a new column:")
    print(price_df[['mkt_cap']].head())
    price_df.to_csv("%sprice_df.csv" % dir, "|")

def add_sedol(uni_df, start, end, out_dir):
    date = end - TDay
    sql = ("SELECT DISTINCT gvkey, itemvalue 'sedol'"
           " FROM sec_idhist"
           " WHERE efffrom < '%s'"
           " AND effthru >= '%s'"
           " AND iid = '01'"
           " AND item = 'SEDOL'"
           " AND gvkey IN %s"
           % (date, date, tuple(uni_df.index.values)))
    cnxn_s = 'Trusted_Connection=yes;Driver={ODBC Driver 17 for SQL Server};Server=dbDevCapIq;Database=xpressfeed'
    cnxn = pyodbc.connect(cnxn_s)
    add_df = pd.read_sql(sql, cnxn)
    cnxn.close()
    uni_df = pd.merge(uni_df, add_df, on=['gvkey'])
    uni_df.set_index('gvkey', inplace=True)

    end_s = end.strftime("%Y%m%d")
    dir = '%s/%s/' % (out_dir, end_s)
    print("uni_df added a new column: ")
    print(uni_df[['sedol']].head())
    uni_df.to_csv("%suni_df.csv" % dir, "|")

def main(start_s, end_s, data_dir):
    start = datetime.strptime(start_s, "%Y%m%d")
    end = datetime.strptime(end_s, "%Y%m%d")
    pd.set_option('display.max_columns', 100)
    uni_df = pd.read_csv("%s/%s/uni_df.csv" % (data_dir, end_s), header=0, sep='|', dtype={'gvkey': str},
                         parse_dates=[0])
    #price_df = pd.read_csv("%s/%s/price_df.csv" % (data_dir, end_s), header=0, sep='|', dtype={'gvkey': str}, parse_dates=[0])
    uni_df.set_index('gvkey', inplace=True)
    #price_df.set_index(['date', 'gvkey'], inplace=True)
    #if 'mkt_cap' not in price_df.columns:
        #add_mktcap(uni_df, price_df, start, end, data_dir)
    if 'sedol' not in uni_df.columns:
        add_sedol(uni_df, start, end, data_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", help="the directory where raw data folder is stored", type=str, default='.')
    args = parser.parse_args()
    for fd in sorted(glob.glob(args.dir + '/raw/*')):
        m = re.match(r".*\d{8}", str(fd))
        end_s = fd[-8:]
        print("Loading raw data folder %s" % end_s)
        if end_s[-4:] == '0101':
            start_s = str(int(end_s[:4]) - 1) + '0630'
        else:
            start_s = end_s[:4] + '0101'
        main(start_s, end_s, args.dir + '/raw')
