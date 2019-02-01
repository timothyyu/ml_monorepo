import pandas as pd
import time
from datetime import datetime
from datetime import timedelta
import numpy as np
import os
import mysql.connector
import pyodbc
from mktcalendar import *


def get_uni(start, end, lookback, uni_size=1400):
    unidate = start - TDay * lookback
    t_low_price = 2.0
    t_high_price = 500.0
    t_min_advp = 1000000.0

    sql = ("SELECT g.gvkey, t.tradingItemId 'tid', t.tickerSymbol symbol,"
           " t.tradingItemStatusId status, ctr.country,"
           " curr.currencyName currency, m.marketCap mkt_cap, p.priceClose 'close'"
           " FROM ciqTradingItem t"
           " INNER JOIN ciqSecurity s ON t.securityId =s.securityId"
           " INNER JOIN ciqCompany co ON s.companyId =co.companyId"
           " INNER JOIN ciqCountryGeo ctr ON ctr.countryId =co.countryId"
           " INNER JOIN ciqCurrency curr ON t.currencyId =curr.currencyId"
           " INNER JOIN ciqMarketCap m ON co.companyId=m.companyId"
           " INNER JOIN ciqGvKeyIID g ON g.objectId=t.tradingItemId"
           " INNER JOIN ciqPriceEquity2 p ON p.tradingItemId=t.tradingItemId"
           " AND p.pricingDate = m.pricingDate"
           " WHERE ctr.country= 'United States'"
           " AND curr.currencyName = 'US Dollar'"
           " AND s.securitySubTypeId = 1"
           " AND m.pricingDate = '%s'"
           % unidate)
    cnxn_s = 'Trusted_Connection=yes;Driver={ODBC Driver 17 for SQL Server};Server=dbDevCapIq;Database=xpressfeed'
    cnxn = pyodbc.connect(cnxn_s)
    uni_df = pd.read_sql(sql, cnxn, index_col=['gvkey', 'tid'])
    cnxn.close()
    print("Universe size (US/USD): %d" % len(uni_df))

    trailingSt = unidate - TDay * 21
    trailingEd = unidate - TDay
    sql = ("SELECT g.gvkey, p.tradingItemId 'tid', p.pricingDate, p.volume"
           " FROM ciqPriceEquity2 p"
           " INNER JOIN ciqGvKeyIID g ON g.objectId = p.tradingItemId"
           " WHERE p.pricingDate BETWEEN '%s' AND '%s'"
           " AND g.gvkey IN %s"
           " AND p.tradingItemId In %s"
           % (trailingSt, trailingEd, tuple(uni_df.index.levels[0]), tuple(uni_df.index.levels[1])))
    cnxn = pyodbc.connect(cnxn_s)
    price_df = pd.read_sql(sql, cnxn, index_col=['gvkey', 'tid'])
    cnxn.close()
    price_df = pd.merge(uni_df, price_df, on=['gvkey', 'tid'])
    uni_df['tradable_med_volume_21'] = price_df['volume'].median(level=['gvkey', 'tid'])
    print("Universe size (prices): %d" % len(uni_df))

    uni_df = uni_df[(uni_df['close'] > t_low_price) & (uni_df['close'] < t_high_price)]
    print("Universe size (price range): %d" % len(uni_df))

    uni_df['mdvp'] = uni_df['tradable_med_volume_21'] * uni_df['close']
    uni_df = uni_df[uni_df['mdvp'] > t_min_advp]
    print("Universe size (mdvp): %d" % len(uni_df))

    uni_df.reset_index(level=1, inplace=True)
    uni_df.sort_values('mdvp', ascending=False, inplace=True)
    uni_df = uni_df[~uni_df.index.duplicated()]
    print("Universe size (duplicates): %d" % len(uni_df))

    sql = ("SELECT gvkey, gics_sector sector, gics_industry_group 'group'"
           " FROM factors.stock_info_v6c"
           " WHERE trade_date = '%s'"
           % unidate)
    cnxn = mysql.connector.connect(host='jv-research', port=3306, user='mek_limited', password='1000FTkanye$')
    secdata_df = pd.read_sql(sql, cnxn)
    cnxn.close()
    secdata_df['gvkey'] = [element[:-3] for element in secdata_df['gvkey']]
    uni_df = pd.merge(uni_df, secdata_df, on='gvkey')
    print("Universe size (secdata): %d" % len(uni_df))

    uni_df = uni_df[uni_df['group'] != 3520]
    print("Universe size (bio): %d" % len(uni_df))

    uni_df['rank'] = uni_df['mkt_cap'].fillna(0).rank(ascending=False)
    uni_df = uni_df[uni_df['rank'] <= uni_size]
    print("Universe size (mktcap): %d" % len(uni_df))

    uni_df.set_index('gvkey', inplace=True)
    end_s = end.strftime("%Y%m%d")
    dir = './%s/' % end_s
    if not os.path.exists(dir):
        os.makedirs(dir)
    uni_df.to_csv(r"%suni_df.csv" % dir, "|")
    return uni_df[['symbol', 'sector', 'tid']]


def load_barra(uni_df, start, end):
    date = end - TDay

    print("Loading barra...")
    sql1 = ("SELECT trade_date 'date', gvkey, MO1_4 momentum, BP btop, DYLD divyild,"
            " SIZE 'size', EP growth"
            " FROM factors.loadings_v6c_xmkt "
            " WHERE trade_date BETWEEN '%s' AND '%s'"
            % (start, date))

    sql2 = ("SELECT trade_date 'date', gvkey, gics_industry_group ind1"
            " FROM factors.stock_info_v6c i"
            " WHERE trade_date BETWEEN '%s' AND '%s'"
            % (start, date))

    cnxn = mysql.connector.connect(host='jv-research', port=3306, user='mek_limited', password='1000FTkanye$')
    barra_df1 = pd.read_sql(sql1, cnxn)
    barra_df2 = pd.read_sql(sql2, cnxn)
    cnxn.close()
    barra_df = pd.merge(barra_df1, barra_df2, on=['date', 'gvkey'])
    barra_df['gvkey'] = [element[:-3] for element in barra_df['gvkey']]
    barra_df = pd.merge(barra_df, uni_df, on='gvkey')
    barra_df.set_index(['date', 'gvkey'], inplace=True)

    end_s = end.strftime("%Y%m%d")
    dir = './%s/' % end_s
    if not os.path.exists(dir):
        os.makedirs(dir)
    barra_df.to_csv(r"%sbarra_df.csv" % dir, "|")
    return barra_df


def load_price(uni_df, start, end):
    print("Loading daily info...")
    date = end - TDay
    sql = ("SELECT DISTINCT g.gvkey, p.tradingItemId 'tid', p.priceOpen 'open',"
           " p.priceClose 'close', p.priceHigh 'high', p.priceLow 'low', p.volume,"
           " sp.latestSplitFactor 'split', d.divAmount 'div', p.pricingDate 'date',"
           " m.marketCap 'mkt_cap'"
           " FROM ciqPriceEquity2 p"
           " INNER JOIN ciqGvKeyIID g ON g.objectId=p.tradingItemId"
           " INNER JOIN ciqTradingItem t ON t.tradingItemId=p.tradingItemId"
           " INNER JOIN ciqSecurity s ON t.securityId =s.securityId"
           " INNER JOIN ciqMarketCap m ON s.companyId=m.companyId"
           " AND m.pricingDate = p.pricingDate"
           " LEFT JOIN ciqSplitCache sp ON sp.tradingItemId = p.tradingItemId"
           " AND sp.SplitDate = p.pricingDate"
           " LEFT JOIN ciqDividendCache d ON d.tradingItemId = p.tradingItemId"
           " AND d.dividendDate = p.pricingDate"
           " WHERE p.pricingDate BETWEEN '%s' AND '%s'"
           " AND g.gvkey IN %s"
           " AND p.tradingItemId In %s"
           % (start, date, tuple(uni_df.index.values), tuple(uni_df['tid'].values)))
    cnxn_s = 'Trusted_Connection=yes;Driver={ODBC Driver 17 for SQL Server};Server=dbDevCapIq;Database=xpressfeed'
    cnxn = pyodbc.connect(cnxn_s)
    price_df = pd.read_sql(sql, cnxn)
    cnxn.close()
    price_df = pd.merge(uni_df, price_df, on=['gvkey', 'tid'])
    price_df.set_index(['date', 'gvkey'], inplace=True)

    print("Loading past info...")
    prev = start - TDay
    tra60Pr = prev - TDay * 60
    sql = ("SELECT DISTINCT g.gvkey, p.tradingItemId 'tid', p.pricingDate 'date',"
           " p.priceOpen 'open', p.priceClose 'close', p.volume"
           " FROM ciqPriceEquity2 p"
           " INNER JOIN ciqGvKeyIID g ON g.objectId=p.tradingItemId"
           " WHERE pricingDate BETWEEN '%s' AND '%s'"
           " AND g.gvkey IN %s"
           " AND p.tradingItemId In %s"
           % (tra60Pr, date, tuple(uni_df.index.values), tuple(uni_df['tid'].values)))
    cnxn = pyodbc.connect(cnxn_s)
    past = pd.read_sql(sql, cnxn)
    cnxn.close()
    past = pd.merge(uni_df, past, on=['gvkey', 'tid'])
    past.set_index(['date', 'gvkey'], inplace=True)
    past.sort_index(inplace=True)
    idx = pd.IndexSlice

    print("Calculating daily ret...")
    daily = past.loc[idx[prev:, :], :]
    price_df['ret'] = ret(daily)
    price_df['log_ret'] = log_ret(daily)
    price_df['overnight_log_ret'] = overnight_log_ret(daily)
    price_df['today_log_ret'] = today_log_ret(daily)

    print("Calculating trailing 21...")
    tra21Pr = prev - TDay * 21
    tra21 = past.loc[idx[tra21Pr:, :], :]
    tra21 = tra21.groupby(level="gvkey").shift(1)
    price_df['med_volume_21'] = med_volume(tra21, 21)
    price_df['volat_21'] = volat(tra21, 21)
    price_df['overnight_volat_21'] = overnight_volat(tra21, 21)
    price_df['today_volat_21'] = today_volat(tra21, 21)
    price_df['mdvp'] = price_df['med_volume_21'] * price_df['close']

    print("Calculating trailing 60...")
    tra60 = past.loc[idx[tra60Pr:, :], :]
    tra60 = tra60.groupby(level="gvkey").shift(1)
    price_df['med_volume_60'] = med_volume(tra60, 60)
    price_df['volat_60'] = volat(tra60, 60)

    end_s = end.strftime("%Y%m%d")
    dir = './%s/' % end_s
    if not os.path.exists(dir):
        os.makedirs(dir)
    price_df.to_csv(r"%sprice_df.csv" % dir, "|")
    return price_df


def ret(df):
    return df['close'] / df['close'].groupby(level="gvkey").shift(1) - 1


def overnight_ret(df):
    return df['open'] / df['close'].groupby(level="gvkey").shift(1) - 1


def today_ret(df):
    return df['close'] / df['open'] - 1


def log_ret(df):
    return np.log(df['close'] / df['close'].groupby(level="gvkey").shift(1))


def overnight_log_ret(df):
    return np.log(df['open'] / df['close'].groupby(level="gvkey").shift(1))


def today_log_ret(df):
    return np.log(df['close'] / df['open'])


def med_volume(df, days):
    return df['volume'].groupby(level="gvkey").apply(lambda x: x.rolling(days).median())


def volat(df, days):
    return ret(df).groupby(level="gvkey").apply(lambda x: x.rolling(days).std())


def overnight_volat(df, days):
    return overnight_ret(df).groupby(level="gvkey").apply(lambda x: x.rolling(days).std())


def today_volat(df, days):
    return today_ret(df).groupby(level="gvkey").apply(lambda x: x.rolling(days).std())
