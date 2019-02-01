import pymysql
import StockDataManager as sdm
import sqlalchemy as sa
from sqlalchemy import select
import pandas as pd
import datetime
from Data.StockDataManager import Settings
import Quandl
import json
import numpy as np

class TimeSeries :
    def __init__(self, settings):
        self._settings = settings

    '''
    Filtering - filter the dataframe with a given period. The down-sampled value will be the last value in the list
    '''
    def filtering(self, data, f) :
        data1 = data.copy()
        for i in range(len(data1)) :
            if i%f == 0:
                #print i
                continue
            data1.iloc[i, :] = np.NAN
        return data1.dropna()


    def get_stock_series(self, codes, start, end=None, fields=None):
        tl_price = self._settings.get_mysql_table(self._settings._table_price)
        if end is None:
            end = str(datetime.date.today())

        query = select([tl_price]). \
            where(tl_price.c.code.in_(codes)).  \
            where(tl_price.c.date >= start). \
            where(tl_price.c.date <= end)
        data = pd.read_sql(query, self._settings.get_mysql_engine())
        data.set_index('date', inplace=True)



        ### reorder the dataframe
        ### using a dict as a container. Each field will be a separate dataframe stored in the dict.
        ### the key will be the field name
        di_data = dict()
        for field in fields :
            df_field = pd.DataFrame()
            for code in codes:
                df_one = data[data['code'] == code]
                df_two = df_one[[field]]
                df_two.columns = [code]
                df_field = df_field.join(df_two, how='outer')
            di_data[field] = df_field

        return di_data

    def get_equity_market_values(self, field = None, tickers = None, start = None, end = None):
        mongo_coll_eqMkt = self._settings.get_mongo_coll_equity_market()
        df_mkt = pd.DataFrame()
        if tickers is not None:
            for ticker in tickers :
                query = mongo_coll_eqMkt.find({'ticker': ticker})
                df_fields = pd.DataFrame(list(query))


        return df_mkt


    def get_data_from_mongo(self):
        mongo_coll_price = self._settings.get_mongo_coll_price()

        df_prices = pd.DataFrame(list(mongo_coll_price.find()))
        df_prices['date'] = pd.to_datetime(df_prices['date'] * 1000 * 1000)
        df_prices = df_prices.set_index('date')
        df_prices = df_prices.sort_index()
        return df_prices



    def store_ETF_data(self, tickers) :
        settings = Settings()
        db = settings.get_mongo_db('Quandl', local=True)
        coll = db['ETF']

        for t in tickers:
            # find the ticker
            dates = coll.find_one({'name':t}, sort=[('Date', -1)])
            if (dates is None):
                print 'max_date is none'
                mdate = None
            else :
                mdate = pd.to_datetime(dates['Date']*1000*1000).strftime(format='%Y-%m-%d')


            print 'downloadng {t}'.format(t=t)
            df = Quandl.get(t, trim_start=mdate)
            df['name'] = t
            df = df.reset_index()

            if mdate is None :
                df_a = df
            else :
                df_a = df[df['Date'] > mdate]

            if len(df_a) == 0:
                print "data for {ticker} is already updated till {date}".format(ticker=t, date=mdate)
                continue
            records = json.loads(df_a.T.to_json()).values()
            #print records
            print "uploading {t}".format(t=t)
            coll.insert_many(records)

    def store_Stock_data(self, tickers):
        settings = Settings()
        db = settings.get_mongo_db('Quandl', local=True)
        coll = db['Stock']

        for t in tickers:

            # find the ticker
            dates = coll.find_one({'name':t}, sort=[('Date', -1)])
            if (dates is None):
                print 'max_date is none'
                mdate = None
            else :
                mdate = pd.to_datetime(dates['Date']*1000*1000).strftime(format='%Y-%m-%d')
                print 'downloadng {t}'.format(t=t)

            try:
                df = Quandl.get(t, trim_start=mdate)
                df = df.reset_index()
            except:
                print 'cannot download {n}'.format(n=t)
                continue

            if mdate is None :
                df_a = df
            else :
                df_a = df[df['Date'] > mdate]

            if len(df_a) == 0:
                print "data for {ticker} is already updated till {date}".format(ticker=t, date=mdate)
                continue

            df_adj = pd.DataFrame()
            df_adj['Date'] = df_a['Date']
            df_adj['Open'] = df_a['Adj. Open']
            df_adj['High'] = df_a['Adj. High']
            df_adj['Low'] = df_a['Adj. Low']
            df_adj['Close'] = df_a['Adj. Close']
            df_adj['Volume'] = df_a['Adj. Volume']
            df_adj['name'] = t

            records = json.loads(df_adj.T.to_json()).values()
            # #print records
            print "uploading {t}".format(t=t)
            coll.insert_many(records)



    def get_stock_data(self, tickers) :
        data = {}
        settings = Settings()
        coll = settings.get_mongo_coll('Stock', 'Quandl', local=True)

        for t in tickers:
            l = list(coll.find({'name':t}))
            if l == []:
                print 'ticker {t} cannot be found'.format(t=t)
                continue

            df = pd.DataFrame(l)
            df['Date'] = pd.to_datetime(df['Date'] * 1000 * 1000)
            df['price'] = df['Close']
            df['volume'] = df['Volume']
            df = df.set_index('Date')
            df = df.sort_index()
            try :
                df.index = df.index.tz_localize('UTC')
            except :
                df.index = df.index.tz_convert('UTC')

            data[t] = df

        return data

    def get_ETF_data(self, tickers) :
        data = {}
        settings = Settings()
        coll = settings.get_mongo_coll('ETF', 'Quandl', local=True)

        for t in tickers:
            l = list(coll.find({'name':t}))
            if l == []:
                print 'ticker {t} cannot be found'.format(t=t)
                continue

            df = pd.DataFrame(l)
            df['Date'] = pd.to_datetime(df['Date'] * 1000 * 1000)
            df['price'] = df['Close']
            df['volume'] = df['Volume']
            df = df.set_index('Date')
            df = df.sort_index()
            try :
                df.index = df.index.tz_localize('UTC')
            except :
                df.index = df.index.tz_convert('UTC')

            data[t] = df

        return data

    def get_agg_ETF_data(self, tickers) :
        data = self.get_ETF_data(tickers)
        if data == {} :
            print "cannot find all the tickers. Return"
            return None

        df_prices = pd.DataFrame()
        df_volume = pd.DataFrame()

        dp = {}
        for t in data.keys():
            df = pd.DataFrame()
            df['open'] = data[t]['Open']
            df['high'] = data[t]['High']
            df['low'] = data[t]['Low']
            df['close'] = data[t]['Close']
            df['volume'] = data[t]['Volume']
            df['price'] = df['close']


            try :
                df.index = df.index.tz_localize('UTC')
            except :
                df.index = df.index.tz_convert('UTC')

            dp[t] = df
            #df_prices[t] = data[t]['price']
            #df_volume[t] = data[t]['volume']

        #df_prices = df_prices.fillna(method='pad', axis=0)
        #df_prices = df_prices.dropna()
        #df_volume = df_volume.fillna(method='pad', axis=0)
        #df_volume = df_volume.dropna()

        # dp = {}
        # for t in tickers:
        #     df = pd.DataFrame()
        #     df['price'] = df_prices[t]
        #     df['volume'] = df_volume[t]
        #     dp[t] = df
        dp = pd.Panel(dp)

        return dp



    def store_Fred_data(self, tickers):
        settings = Settings()
        db = settings.get_mongo_db(local=True)
        coll = db['Fred']

        for t in tickers:

            # find the ticker
            dates = coll.find_one({'name':t}, sort=[('Date', -1)])
            if (dates is None):
                print 'max_date is none'
                mdate = None
            else :
                mdate = pd.to_datetime(dates['Date']*1000*1000).strftime(format='%Y-%m-%d')

            print 'downloadng {t}'.format(t=t)


            df = Quandl.get(t, trim_start=mdate, authtoken='AuFngLLqDpLf672K9W85')
            df = df.reset_index()


            if mdate is None :
                df_a = df
            else :
                df_a = df[df['Date'] > mdate]

            if len(df_a) == 0:
                print "data for {ticker} is already updated till {date}".format(ticker=t, date=mdate)
                continue

            df_adj = pd.DataFrame()
            df_adj['Date'] = df_a['DATE']
            df_adj['Value'] = df_a['VALUE']
            df_adj['name'] = t

            records = json.loads(df_adj.T.to_json()).values()
            # #print records
            print "uploading {t}".format(t=t)
            coll.insert_many(records)

    def get_Fred_data(self, tickers) :
            data = {}
            settings = Settings()
            coll = settings.get_mongo_coll('Fred', local=True)

            for t in tickers:
                df = pd.DataFrame(list(coll.find({'name': t})))
                df['Date'] = pd.to_datetime(df['Date'] * 1000 * 1000)
                df = df.set_index('Date')
                df = df.sort_index()
                try :
                    df.index = df.index.tz_localize('UTC')
                except :
                    df.index = df.index.tz_convert('UTC')

                data[t] = df

            return data

    def get_agg_Fred_data(self, tickers) :
        data = self.get_Fred_data(tickers)

        dp = {}
        for t in tickers:
            df = pd.DataFrame()
            df['value'] = data[t]['Value']
            dp[t] = df

        dp = pd.Panel(dp)

        return dp

## testing
if __name__ == '__main__' :
    settings = sdm.Settings()
    ts = TimeSeries(settings)

    #data = ts.get_stock_series(['300382', '603008'], start='2015-01-01', fields=['open', 'close'])
    #data1 = ts.get_stock_series(['300382', '603008'], start='2015-01-01')
    #data = ts.get_equity_market_values()

    tickers = ['GOOG/NYSE_SPY', #S&P 500 ETF
            'GOOG/AMEX_EWJ', # iShares MSCI Japan ETF
            'GOOG/NYSE_IEV', # iShares Europe ETF
            'GOOG/NYSE_VWO', # Vanguard Emerging Market Stock ETF

            'GOOG/NYSE_VNQ', # Vanguard MSCI US Reits
            'GOOG/NYSE_IYR', # iShares U.S. Real Estate ETF
            'GOOG/NYSE_RWX', # SPDR DJ Wilshire Intl Real Estate ETF

            'GOOG/NYSEARCA_TLT',  # 20 Years Treasury ETF
            'GOOG/NYSEARCA_TLH',  # 15-20 Years Treasury

            'GOOG/AMEX_GSG', # GSCI Commodity-Indexed Trust Fund
            #'GOOG/NYSEARCA_GLD',  # SPDR Gold ETF

            'GOOG/NYSE_GDX', # gold
            'GOOG/nyse_USO', # oil
            'GOOG/NYSE_XLE',
            'GOOG/NYSE_XLF',
            'GOOG/NYSE_XLK',

            'GOOG/NYSEARCA_VXX',
            'GOOG/NYSEARCA_XIV',

            'GOOG/NYSEARCA_EEM',
            'GOOG/NYSEARCA_EWJ'
            ]

    # dp = ts.get_agg_data(tickers)
    # dp = ts.get_agg_ETF_data(tickers + ['test'])

    stock_tickers = pd.read_csv('../ETF/SP500.csv')

    ts.store_Stock_data(stock_tickers['free_code'].values)
    # ts.store_ETF_data(tickers)