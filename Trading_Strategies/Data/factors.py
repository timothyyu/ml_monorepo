import httplib
import urllib
import json
import traceback
import pandas as pd
from sqlalchemy import *

class Client:
    HTTP_OK = 200
    HTTP_AUTHORIZATION_ERROR = 401

    domain = 'api.wmcloud.com'
    port = 443
    token = ''
    httpClient = None

    def __init__(self):
        self.httpClient = httplib.HTTPSConnection(self.domain, self.port)

    def __del__(self):
        if self.httpClient is not None:
            self.httpClient.close()

    def encodepath(self, path):
        start = 0
        n = len(path)
        re = ''
        i = path.find('=', start)
        while i != -1:
            re += path[start:i + 1]
            start = i + 1
            i = path.find('&', start)
            if (i >= 0):
                for j in range(start, i):
                    if (path[j] > '~'):
                        re += urllib.quote(path[j])
                    else:
                        re += path[j]
                re += '&'
                start = i + 1
            else:
                for j in range(start, n):
                    if (path[j] > '~'):
                        re += urllib.quote(path[j])
                    else:
                        re += path[j]
                start = n
            i = path.find('=', start)
        return re

    def init(self, token):
        self.token = token

    def getData(self, path):
        result = None
        path = '/data/v1' + path
        path = self.encodepath(path)
        try:
            # set http header here
            self.httpClient.request('GET', path, headers={"Authorization": "Bearer " + self.token})
            # make request
            response = self.httpClient.getresponse()
            # read result
            if response.status == self.HTTP_OK:
                # parse json into python primitive object
                result = response.read()
            else:
                result = response.read()
            if (path.find('.csv?') != -1):
                result = result.decode('GB2312').encode('utf-8')
            return response.status, result
        except Exception, e:
            # traceback.print_exc()
            raise e
        return -1, result


import StockDataManager as sdm


class FactorFactory:
    TOKEN = '20353207bd1bb251c0512ffa4a4fc28de0f6bf16bbdb41c89cb2b4ab8c458551'

    form_funda_cf = '/api/fundamental/getFdmtCF.json'
    form_funda_is = '/api/fundamental/getFdmtIS.json'
    form_mkt_eq = '/api/market/getMktEqud.json'
    form_mkt_factor_oneday = '/api/market/getStockFactorsOneDay.json'
    form_mkt_index = '/api/market/getMktIdxd.json'
    form_master_cal = '/api/master/getTradeCal.json'
    form_index_info = '/api/idx/getIdx.json'
    form_index_components = '/api/idx/getIdxCons.json'

    client = None
    settings = None

    def __init__(self, token=None):
        if token is not None:
            self.TOKEN = token
        if self.client is None:
            self.client = Client()
            self.client.init(self.TOKEN)
        if self.settings is None:
            self.settings = sdm.Settings()

    def getData(self, form, params):
        try:
            ticker = params.get('ticker')
            if ticker is None:
                ticker = ''

            field = params.get('field')
            if field is None:
                field = ''

            secID = params.get('secID')
            if secID is None:
                secID = ''

            beginDate = params.get('beginDate')
            endDate = params.get('endDate')
            if (beginDate is None) or (endDate is None):
                beginDate_str = ''
                endDate_str = ''
            else:
                beginDate_str = beginDate.strftime('%Y%m%d')
                endDate_str = endDate.strftime('%Y%m%d')

            url1 = '{form}?field={field}&secID={secID}&ticker={ticker}&beginDate={beginDate}&endDate={endDate}' \
                .format(form=form, field=field, secID=secID, ticker=ticker, \
                        beginDate=beginDate_str, endDate=endDate_str)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                df = pd.DataFrame(result['data'])
                # df['publishDate'] = pd.to_datetime(df['publishDate'])
                # df.rename(columns={'publishDate':'date'}, inplace=True)
                # df.set_index('date', inplace=True)
                return df
            else:
                print code
                print result

                return None

        except Exception, e:
            # traceback.print_exc()
            raise e

    def getTradingDays(self, start, end=None):
        try:
            form = self.form_master_cal
            beginDate_str = start
            if end is None:
                endDate_str = datetime.today().strftime('%Y%m%d')
            else:
                endDate_str = end

            exchangeCD = 'XSHG'  # by default XSHG/XSHE are shanghai and shenzhen exchanges
            field = 'calendarDate,isOpen'

            ### downloading data
            url1 = '{form}?field={field}&exchangeCD={exchangeCD}&beginDate={beginDate}&endDate={endDate}' \
                .format(form=form, field=field, exchangeCD=exchangeCD, beginDate=beginDate_str, endDate=endDate_str)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                days = pd.DataFrame(result['data'])
                days = days[days['isOpen'] == 1]
                # days = days.sort('calendarDate', ascending=1)
                return days[['calendarDate']]
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    def getIndexInfo(self, params):
        try:
            form = self.form_index_info
            field = params.get('field')
            field = '' if field is None else field
            ticker = params.get('ticker')
            ticker = '' if ticker is None else ticker
            secID = params.get('secID')
            secID = '' if secID is None else secID

            ### downloand data
            url1 = '{form}?field={field}&ticker={ticker}&secID={secID}' \
                .format(form=form, field=field, ticker=ticker, secID=secID)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                output = pd.DataFrame(result['data'])
                return output
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    def getIndexComponents(self, params):
        try:
            form = self.form_index_components
            field = params.get('field')
            field = '' if field is None else field
            ticker = params.get('ticker')
            ticker = '' if ticker is None else ticker
            secID = params.get('secID')
            secID = '' if secID is None else secID
            intoDate = params.get('intoDate')
            intoDate = '' if intoDate is None else intoDate
            isNew = params.get('isNew')
            isNew = '' if isNew is None else isNew

            ### downloand data
            url1 = '{form}?field={field}&ticker={ticker}&secID={secID}&intoDate={intoDate}&isNew={isNew}' \
                .format(form=form, field=field, ticker=ticker, secID=secID, intoDate=intoDate, isNew=isNew)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                output = pd.DataFrame(result['data'])
                return output
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    '''
    Historical market data from DataYes for chinese stockm market
    '''
    def getMarketEquity(self, params):
        try:
            form = self.form_mkt_eq
            beginDate = params.get('beginDate')
            beginDate = '' if beginDate is None else beginDate
            endDate = params.get('endDate')
            endDate = '' if endDate is None else endDate
            field = params.get('field')
            field = '' if field is None else field
            secID = params.get('secID')
            secID = '' if secID is None else secID
            ticker = params.get('ticker')
            ticker = '' if ticker is None else ticker
            tradeDate = params.get('tradeDate')
            tradeDate = '' if tradeDate is None else tradeDate

            ### downloading data
            url1 = '{form}?field={field}&beginDate={beginDate}&endDate={endDate}&secID={secID}&ticker={ticker}&tradeDate={tradeDate}' \
                .format(form=form, field=field, beginDate=beginDate, endDate=endDate, secID=secID, ticker=ticker,
                        tradeDate=tradeDate)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                output = pd.DataFrame(result['data'])
                return output
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    def getMarketIndex(self, params):
        try:
            form = self.form_mkt_index
            beginDate = params.get('beginDate')
            beginDate = '' if beginDate is None else beginDate
            endDate = params.get('endDate')
            endDate = '' if endDate is None else endDate
            field = params.get('field')
            field = '' if field is None else field
            secID = params.get('secID')
            secID = '' if secID is None else secID
            ticker = params.get('ticker')
            ticker = '' if ticker is None else ticker
            tradeDate = params.get('tradeDate')
            tradeDate = '' if tradeDate is None else tradeDate

            ### downloading data
            url1 = '{form}?field={field}&beginDate={beginDate}&endDate={endDate}&secID={secID}&ticker={ticker}&tradeDate={tradeDate}' \
                .format(form=form, field=field, beginDate=beginDate, endDate=endDate, secID=secID, ticker=ticker,
                        tradeDate=tradeDate)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                output = pd.DataFrame(result['data'])
                return output
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    def getStockFactors(self, params):
        try:
            form = self.form_mkt_factor_oneday
            field = params.get('field')
            field = '' if field is None else field
            secID = params.get('secID')
            secID = '' if secID is None else secID
            ticker = params.get('ticker')
            ticker = '' if ticker is None else ticker
            tradeDate = params.get('tradeDate')
            tradeDate = '' if tradeDate is None else tradeDate

            ### downloading data
            url1 = '{form}?field={field}&secID={secID}&ticker={ticker}&tradeDate={tradeDate}' \
                .format(form=form, field=field, secID=secID, ticker=ticker, tradeDate=tradeDate)
            print url1

            code, result = self.client.getData(url1)
            if code == 200:
                result = json.loads(result)
                output = pd.DataFrame(result['data'])
                return output
            else:
                print code
                print result
                return None
        except Exception, e:
            raise e

    ## calc Returns
    def update_returns(self):
        try:
            coll_eq_mkt = self.settings.get_mongo_coll_equity_market()

            # get mysql connection
            db_engine = self.settings.get_mysql_engine()
            metadata = MetaData(bind=db_engine)
            tl_prices = Table('Stock_Price', metadata,
                              Column('date', String(10), nullable=False),
                              Column('ticker', String(10), nullable=False),
                              Column('id', String(20), nullable=False),
                              Column('open', Float),
                              Column('high', Float),
                              Column('low', Float),
                              Column('close', Float),
                              Column('turnoverValue', BigInteger),
                              Column('ret_cc', Float),
                              Column('ret_cc_2', Float),
                              Column('ret_cc_5', Float),
                              Column('ret_cc_10', Float),
                              Column('ret_cc_20', Float),
                              Column('ret_cc_60', Float),
                              Column('ma_2', Float),
                              Column('ma_5', Float),
                              Column('ma_10', Float),
                              Column('ma_20', Float),
                              Column('ma_60', Float),
                              Column('ma_100', Float)
                              )
            metadata.create_all(db_engine)
            # get all the stock
            ids = coll_eq_mkt.distinct('ticker')
            for ticker in ids :
                print('downloading {ticker}'.format(ticker=ticker))
                query_prices = coll_eq_mkt.find({'ticker': ticker}).sort('tradeDate', 1)

                df_prices = pd.DataFrame(list(query_prices))

                df_returns = pd.DataFrame()
                df_returns['date'] = df_prices['tradeDate']
                df_returns['ticker'] = ticker
                df_returns['id'] = df_returns['ticker'] + '_' +  df_returns['date']


                # price information
                df_returns['open'] = df_prices['openPrice'] * df_prices['accumAdjFactor']
                df_returns['high'] = df_prices['highestPrice'] * df_prices['accumAdjFactor']
                df_returns['low'] = df_prices['lowestPrice'] * df_prices['accumAdjFactor']
                df_returns['close'] = df_prices['closePrice'] * df_prices['accumAdjFactor']
                df_returns['turnoverValue'] = df_prices['turnoverValue']
                #df_returns.set_index('date', inplace=True)

                # return information
                df_returns['ret_cc'] = df_returns['close'] / df_returns['close'].shift(1) - 1
                df_returns['ret_cc_2'] = df_returns['close'] / df_returns['close'].shift(2) - 1
                df_returns['ret_cc_5'] = df_returns['close'] / df_returns['close'].shift(5) - 1
                df_returns['ret_cc_10'] = df_returns['close'] / df_returns['close'].shift(10) - 1
                df_returns['ret_cc_20'] = df_returns['close'] / df_returns['close'].shift(20) - 1
                df_returns['ret_cc_60'] = df_returns['close'] / df_returns['close'].shift(60) - 1


                df_returns.set_index('date', inplace=True)
                df_returns = df_returns.dropna()

                try :
                    print ("--- loading to db")
                    df_returns.to_sql('Stock_Price', db_engine, index=True, if_exists='append')
                    #import odo
                    #odo.odo(df_returns, tl_prices )
                    print ("---Success")
                except Exception, a:
                    print a
                    print "--- Failed"
                    continue


        except Exception, e:
            raise e


    def calcFactor_EP(self, params):
        # 1. download the related data
        f_is = self.getData(self.form_funda_is, params)  # from Income Statement
        f_is = f_is.sort(['publishDate', 'reportType'])
        f_is.drop_duplicates('publishDate', inplace=True)
        f_is = f_is.set_index('publishDate').sort()

        # 2. cleaning earning data.
        f_earning = f_is[['reportType', 'NIncome']]
        f_earning.loc[:, 'Earning_Q'] = f_earning.loc[:, 'NIncome'] - f_earning.loc[:, 'NIncome'].shift(1)
        f_earning.head()
        index_q1 = f_earning.loc[:, 'reportType'] == 'Q1'
        index_a = f_earning.loc[:, 'reportType'] == 'A'
        f_earning.loc[index_q1, 'Q'] = f_earning.loc[index_q1, 'NIncome']
        f_earning.loc[:, 'Earning_TTM'] = pd.rolling_sum(f_earning['Earning_Q'], 4)
        f_earning.loc[:, 'Earning_FY0'] = f_earning.loc[:, 'Earning_Q'] * 4
        f_earning.loc[:, 'Earning_LY'] = f_earning.loc[index_a, 'NIncome']

        # 3. download price and other information
        f_price = self.getData(self.form_mkt_eq, params)
        f_price = f_price.set_index('tradeDate').sort()

        # 4. create EP data
        f_ep = f_price[['marketValue']]
        f_ep = f_ep.join(f_earning[['Earning_Q', 'Earning_TTM', 'Earning_FY0', 'Earning_LY']], how='outer')
        f_ep = f_ep.ffill().dropna()

        f_ep.rename(columns={'marketValue': 'MV'}, inplace=True)

        f_ep['EP_TTM'] = f_ep['Earning_TTM'] / f_ep['MV']
        f_ep['EP_FY0'] = f_ep['Earning_FY0'] / f_ep['MV']
        f_ep['EP_LY'] = f_ep['Earning_LY'] / f_ep['MV']
        f_ep['PE_TTM'] = 1 / f_ep['EP_TTM']
        return f_ep

class RiskFactor :
    def __init__(self, settings):
        self.settings = settings

    def get_PE(self, params):
        beginDate = params.get('beginDate')
        endDate = params.get('endDate')
        uniTicker = params.get('uniTicker')



from datetime import datetime
import matplotlib

if __name__ == '__main__':
    ff = FactorFactory()

    params = {}
    params['ticker'] = '000905' # zhongzheng 500 ETF
    # params['beginDate'] = datetime.strptime('20080101', '%Y%m%d')
    # params['endDate'] = datetime.today()
    pd_etf = ff.getMarketIndex(params)

    # ep = ff.calcFactor_EP( params)
    # print ep.columns

    '''test 2
    '''
    # days = ff.getTradingDays(start='20080101')
    # print days

    '''test 3
    '''
    # params = {}
    # params['tradeDate'] = '20160216'
    # factors = ff.getStockFactors(params)
    # print factors

    '''test 4
    '''
    # params={}
    # indices = ff.getIndexInfo(params)
    # indices_info = indices[['secID', 'secShortName']]
    # print indices_info
    #
    # params['secID'] = indices_info.loc[1, 'secID']
    # universe = ff.getIndexComponents(params)
    # universe_tickers = universe['consTickerSymbol']
    # print universe_tickers


    ff.update_returns()
