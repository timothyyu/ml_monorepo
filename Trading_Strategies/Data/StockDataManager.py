import json

import blaze
import odo
import pandas as pd
import tushare as ts

import pymongo
from sqlalchemy import *
import pymysql

class Settings :
    MAX_DOWNLOAD_TRIALS = 6

    _local_db = False

    if _local_db == True:
        _mysql_hostname = 'localhost'
        _mongo_hostname = 'localhost'
    else :
        _mysql_hostname = '188.166.179.144'
        _mongo_hostname = '188.166.179.144'

    _mysql_username = 'darwin'
    _mysql_password = 'darwinlab'
    _mysql_database = 'darwindb'
    _mysql_url = "mysql+pymysql://{user}:{passwd}@{host}/{db}".format(user=_mysql_username, passwd=_mysql_password,
            host=_mysql_hostname, db=_mysql_database)

    _sqlite_db = '/home/jianbo/sqlite_db/darwinlab.db'
    _sqlite_url = "sqlite://{path}".format(path=_sqlite_db)
    _sqlite_engine = None

    _mysql_engine = None
    _mysql_conn = None
    _mysql_metadata = None

    _table_price_tmp = 'Stock_Price_Daily_tmp'
    _table_price = 'Stock_Price_Daily'
    _table_info = 'Stock_Info'

    MONGO_COLL_Job_Daily = "Job_Daily"
    _mongo_collection_stock_daily_price = "Stock_Price_Daily"
    _mongo_collection_stock_daily_price_tmp = "Stock_Price_Daily_tmp"
    _mongo_collection_stock_info = "Stock_info"

    MONGO_COLL_Rawdata_Equity_Fundamental_IS = "RAW_Equity_IncomeStatment"
    MONGO_COLL_Rawdata_Equity_Market = "StockPrices"
    MONGO_COLL_Rawdata_Equity_Factors = "StockFactors"
    MONGO_COLL_Rawdata_Index_Information = "RAW_Index_Information"
    MONGO_COLL_Rawdata_Index_Components = "RAW_Index_Components"

    _mongo_port = 27017
    _mongo_conn_uri = 'mongodb://' + _mongo_hostname + ':' + str(_mongo_port)

    _mongo_db_name = "darwin_test"

    _mongo_conn = None

    def __init__(self):
        self._mongo_conn = self.get_mongo_conn()
        #self._local_mongo_db = self.get_mongo_db()

    def get_mongo_conn(self, local=False):
        if local == False:
            self._mongo_conn = pymongo.MongoClient(self._mongo_hostname, self._mongo_port)
        else :
            self._mongo_conn = pymongo.MongoClient('localhost', self._mongo_port)



    def get_mongo_db(self, local=False):
        self.get_mongo_conn(local)
        return self._mongo_conn[self._mongo_db_name]

    def get_mongo_db(self, name_db, local=False):
        self.get_mongo_conn(local)
        return self._mongo_conn[name_db]

    def get_sqlite_engine(self):
        if self._sqlite_engine is None:
            self._sqlite_engine = create_engine(Settings._sqlite_url, echo=True)
        return self._sqlite_engine

    def get_mysql_engine(self):
        if self._mysql_engine is None :
            self._mysql_engine = create_engine(Settings._mysql_url, echo=True)
        return self._mysql_engine

    def get_mysql_conn(self):
        self.get_mysql_engine()
        if self._mysql_conn is None:
            self._mysql_conn = self._mysql_engine.connect()
        return self._mysql_conn

    def get_mysql_metadata(self):
        if self._mysql_metadata is None:
            self._mysql_metadata = MetaData(bind=self.get_mysql_engine(), reflect=True)
        return self._mysql_metadata

    def get_mysql_table(self, table_name):
        table = Table(table_name, self.get_mysql_metadata(), autoload=True, autoload_with=self.get_mysql_engine() )
        return table

    ### functions to get local mongo collections
    def get_mongo_coll_job(self):
        return self.get_mongo_coll(self.MONGO_COLL_Job_Daily)


    def get_mongo_coll_price_tmp(self):
        return self.get_mongo_coll(self._mongo_collection_stock_daily_price_tmp)

    def get_mongo_coll_price(self):
        return self.get_mongo_coll(self._mongo_collection_stock_daily_price)

    def get_mongo_coll_info(self):
        return self.get_mongo_coll(self._mongo_collection_stock_info)

    ### mongo collections for equity fundamental
    def get_mongo_coll_equity_funda_is(self):
        return self.get_mongo_coll(self.MONGO_COLL_Rawdata_Equity_Fundamental_IS)

    def get_mongo_coll_equity_market(self):
        return self.get_mongo_coll(self.MONGO_COLL_Rawdata_Equity_Market)

    def get_mongo_coll_eq_factors(self):
        return self.get_mongo_coll(self.MONGO_COLL_Rawdata_Equity_Factors)

    def get_mongo_coll_index_info(self):
        return self.get_mongo_coll(self.MONGO_COLL_Rawdata_Index_Information)

    def get_mongo_coll_index_components(self):
        return self.get_mongo_coll(self.MONGO_COLL_Rawdata_Index_Components)

    def get_mongo_coll(self, name_coll, local=True):
        mongo_db = self.get_mongo_db(local)
        mongo_coll = mongo_db[name_coll]

        return mongo_coll

    def get_mongo_coll(self, name_coll, name_db, local=True):
        mongo_db = self.get_mongo_db(name_db, local)
        mongo_coll = mongo_db[name_coll]
        return mongo_coll



class DownloadManager:
    def __init__(self):
        pass

    # downloading stock historical price
    def download_stock_hist_price(self, code, start, end=None):
        print "downloading " + code
        if end is None:
            price = ts.get_h_data(code, start)
        else:
            price = ts.get_h_data(code, start, end)
        return price


class TaskManager :
    _downloader = None
    _settings = None

    def __init__(self, settings):
        self._downloader = DownloadManager()
        self._settings = settings

    def load_stock_price_into_db(self, code, start, end=None):
        df_prices = self._downloader.download_stock_hist_price(code, start, end)
        df_prices = df_prices.reset_index()
        df_prices['code'] = code
        df_prices['date_num'] = pd.to_numeric(df_prices['date'])
        df_prices['key'] = df_prices['code'] + '_' + df_prices['date_num'].astype(str)

        df_1 = df_prices[['key', 'code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']]

        ### delete all the duplicated keys in the original database
        max_key = max(df_1['key'])
        min_key = min(df_1['key'])

        db_conn = self._settings.get_mysql_conn()
        tl_price = self._settings.get_mysql_table(self._settings._table_price)
        qr_delete = tl_price.delete().where(tl_price.c.key <= max_key).where(tl_price.c.key >= min_key)
        result = db_conn.execute(qr_delete)

        try :
            df_1.to_sql(Settings._table_price, db_conn, chunksize=1000, index=False, if_exists='append' )
        except pymysql.err.IntegrityError :
            print 'Duplicate Entry: Fail to insert'

        #db_conn.close()
        ### load the data into the
        #tl_price_tmp = self._settings.get_mysql_table(self._settings._table_price_tmp)
        #qr_insert = tl_price.insert()
        #result = db_conn.execute(qr_insert, df_1.to_records(index=False,convert_datetime64= False ))
        #odo.odo(blaze.Data(df_1), Settings._mysql_url + '::' + Settings._table_price)


import factors
from datetime import datetime

class JobManager :
    _settings = None
    _taskmanager = None
    _factorfactory = None

    JOB_STATUS_READY = 'ready'
    JOB_STATUS_FAILED = 'failed'
    JOB_STATUS_SUCCESS = 'success'

    TASK_DOWNLOAD_MARKET_EQUITY = 'download_market_equity'
    TASK_DOWNLOAD_MARKET_EQUITY_BYDATE = 'download_market_equity_dydate'
    TASK_DOWNLOAD_EQUITY_FACTOR_BYDATE = 'download_equity_factor_dydate'

    def __init__(self, settings):
        self._settings = settings
        self._taskmanager = TaskManager(settings)
        self._factorfactory = factors.FactorFactory()

    def processJob_DownloadEquityMktByDate(self):
        db = self._settings.get_mongo_db('chinese_market', local=True)  # get mongo db
        coll_job = db[self._settings.MONGO_COLL_Job_Daily]
        coll_market = db[self._settings.MONGO_COLL_Rawdata_Equity_Market]
        while True:
            job = coll_job.find_one({'status':self.JOB_STATUS_READY, 'task':self.TASK_DOWNLOAD_MARKET_EQUITY_BYDATE})
            if job is None:
                print 'No more job to process'
                return

            jobid = job['_id']

            # check whether jobs with the same tradeDate, task and done successfully exists
            exist_jobs = coll_job.find_one({'task':self.TASK_DOWNLOAD_MARKET_EQUITY_BYDATE,
                        'status':self.JOB_STATUS_SUCCESS, 'tradeDate':job['tradeDate']})
            if exist_jobs is not None:
                print 'The job {td} has done before: Next'.format(td=job['tradeDate'])
                self.remove_job(coll_job, jobid)
                continue

            n_trials = 0
            while True:
                jobid = job['_id']
                tradeDate = datetime.strptime(job['tradeDate'], '%Y-%m-%d').strftime('%Y%m%d')

                params = {}
                params['tradeDate'] = tradeDate
                try :
                    print "-------------------------------\n"
                    print "Downloading Market Overview for the equity market for date:{tradeDate}".format(tradeDate=tradeDate)
                    df_mk = self._factorfactory.getMarketEquity(params)
                    print 'Uploading to Mongo Server\n'
                    records = json.loads(df_mk.T.to_json()).values()
                    coll_market.insert(records)

                    print "Success"
                    self.update_job_status(coll_job, jobid, self.JOB_STATUS_SUCCESS)
                    break
                except:
                    print "Failed"
                    self.update_job_retry(coll_job, jobid, n_trials)
                    n_trials = n_trials + 1
                    if n_trials > self._settings.MAX_DOWNLOAD_TRIALS:
                        self.update_job_status(coll_job, jobid, self.JOB_STATUS_FAILED)
                        break

        pass



    def processJob_DownloadStockFactorByDate_TL(self, db):
        coll_job = db[self._settings.MONGO_COLL_Job_Daily]
        coll_factor = db[self._settings.MONGO_COLL_Rawdata_Equity_Factors]
        while True:
            job = coll_job.find_one({'status':self.JOB_STATUS_READY, \
                'task':self.TASK_DOWNLOAD_EQUITY_FACTOR_BYDATE}) # download job which is ready to process

            
            # no more job to process. exit
            if job is None:
                print 'No more job to process'
                return

            jobid = job['_id']

            # check whether jobs with the same tradeDate, task and done successfully exists
            exist_jobs = coll_job.find_one({'task':self.TASK_DOWNLOAD_EQUITY_FACTOR_BYDATE,
                        'status':self.JOB_STATUS_SUCCESS, 'tradeDate':job['tradeDate']})
            if exist_jobs is not None:
                print 'The job {td} has done before: Next'.format(td=job['tradeDate'])
                self.remove_job(coll_job, jobid)
                continue

            # ready to process
            n_trials = 0
            while True:
                
                tradeDate = datetime.strptime(job['tradeDate'], '%Y-%m-%d').strftime('%Y%m%d')

                params = {}
                params['tradeDate'] = tradeDate
                try :
                    print "-------------------------------\n"
                    print "Downloading Stock Factors for date:{tradeDate}".format(tradeDate=tradeDate)
                    df_mk = self._factorfactory.getStockFactors(params)
                    print 'Uploading to Mongo Server\n'
                    records = json.loads(df_mk.T.to_json()).values()
                    coll_factor.insert(records)

                    print "Success"
                    self.update_job_status(coll_job, jobid, self.JOB_STATUS_SUCCESS)
                    break
                except:
                    print "Failed"
                    self.update_job_retry(coll_job, jobid, n_trials)
                    n_trials = n_trials + 1
                    if n_trials > self._settings.MAX_DOWNLOAD_TRIALS:
                        self.update_job_status(coll_job, jobid, self.JOB_STATUS_FAILED)
                        break

        pass


    def processJob_Fundamental_Equity_IS(self):
        while True:
            jobs = self._settings.get_mongo_coll_job().find_one({'action':'EquityIS', 'status':0})
            if jobs is None:
                print "no more job to process"
                return

            n_trials = 0
            while n_trials <= self._settings.MAX_DOWNLOAD_TRIALS:
                jobid = jobs['_id']
                code = jobs['code']
                start = jobs['start']
                end = jobs['end']

                try :
                    print "----------------------------\n"
                    print "Downloading Equity Income Statement for  " + code + "\n"
                    self.task_Fundamental_Equity_IS(code, start, end)

                    print "success "
                    self.update_job_status(jobid, -1)
                    break
                    # self._mongo_coll.find_one_and_update({"_id":jobid}, {"$set": {"status": 1}})
                except:
                    print "failed "
                    n_trials = n_trials + 1
                    self.update_job_status(jobid, n_trials)
                    continue
                    # self._mongo_coll.find_one_and_update({"_id":jobid}, {"$set": {"status": 2}})

    def task_UpdateIndexInfo(self) :
        params = {}
        df_ind = self._factorfactory.getIndexInfo(params)
        records = json.loads(df_ind.T.to_json()).values()

         # remove the old information in the
        coll = self._settings.get_mongo_coll_index_info()
        coll.delete_many({})
        coll.insert(records)

    def task_UpdateIndexComponents(self):
        params = {}
        df_ind_con = self._factorfactory.getIndexComponents(params)
        records = json.loads(df_ind_con.T.to_json()).values()

        coll = self._settings.get_mongo_coll_index_components()
        coll.delete_many({})
        coll.insert(records)

    def task_Fundamental_Equity_IS(self, code, start, end):
        try :
            print '---------------------------------------\n'
            print 'Downloading Equity Income Statement for {code}\n'.format(code=code)
            params = {}
            params['ticker'] = code

            params['beginDate'] = datetime.strptime(start, '%Y%m%d')
            params['endDate'] = datetime.strftime(end, '%Y%m%d')
            df_is = self._factorfactory.getData(self._factorfactory.form_funda_cf, params)

            if df_is is None:
                print 'Failed to download\n'
                return
            df_is['ticker'] = code

            print 'Uploading to Mongo Server\n'
            records = json.loads(df_is.T.to_json()).values()
            self._settings.get_mongo_coll_equity_funda_is().insert(records)

            print 'Success'
        except Exception, e:
            print 'Failed'
            raise e



    def task_UpdatePrice(self):
        try:
            coll_eq_mkt = self._settings.get_mongo_coll_equity_market()

            # get mysql connection
            db_engine = self._settings.get_mysql_engine()
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
                              Column('turnoverRate', Float ),
                              Column('marketValue', BigInteger),
                              Column('negMarketValue', BigInteger))

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
                df_returns['open'] = df_prices['openPrice'] #* df_prices['accumAdjFactor']
                df_returns['high'] = df_prices['highestPrice'] #* df_prices['accumAdjFactor']
                df_returns['low'] = df_prices['lowestPrice'] #* df_prices['accumAdjFactor']
                df_returns['close'] = df_prices['closePrice'] #* df_prices['accumAdjFactor']
                df_returns['turnoverValue'] = df_prices['turnoverValue']
                df_returns['turnoverRate'] = df_prices['turnoverRate']
                df_returns['marketValue'] = df_prices['marketValue']
                df_returns['negMarketValue'] = df_prices['negMarketValue']
                #df_returns.set_index('date', inplace=True)

                df_returns.set_index('date', inplace=True)
                df_returns = df_returns.dropna()

                try :
                    print ("--- loading to db")
                    df_returns.to_sql('Stock_Price', db_engine, index=True, if_exists='append')
                    print ("--- Deleting the old entries")
                    coll_eq_mkt.remove({'ticker': ticker})
                    #import odo
                    #odo.odo(df_returns, tl_prices )
                    print ("--- Success")
                except Exception, a:
                    print a
                    print "--- Failed"
                    continue


        except Exception, e:
            raise e


    def process_job_download_stock_daily_price(self):
        while True:
            # jobs = mongo_coll_job.find_one({'status': 0})
            jobs = self._settings.get_mongo_coll_job().find_one({'$and'[{'action':'load'}, {'status': 0 }]})
            if jobs is None:
                print "no more job to process!"
                return

            n_trials = 0
            while n_trials <= self._settings.MAX_DOWNLOAD_TRIALS:
                jobid = jobs["_id"]
                code = jobs["code"]
                start = jobs["start"]
                end = jobs["end"]

                try:
                    print "----------------------------\n"
                    print "loading " + code + "\n"
                    self._taskmanager.load_stock_price_into_db(code, start, end)
                    print "success "
                    self.update_job_status(jobid, -1)
                    break
                    # self._mongo_coll.find_one_and_update({"_id":jobid}, {"$set": {"status": 1}})
                except:
                    print "failed "
                    n_trials = n_trials + 1
                    self.update_job_status(jobid, n_trials)
                    continue
                    # self._mongo_coll.find_one_and_update({"_id":jobid}, {"$set": {"status": 2}}

    def restart_failed_jobs(self):
        db = self._settings.get_mongo_db('chinese_market', local=True)  # get mongo db
        coll_job = db[self._settings.MONGO_COLL_Job_Daily]
        result = coll_job.update_many({'status':self.JOB_STATUS_FAILED}, \
            {'$set':{'status':self.JOB_STATUS_READY}})
        print 'success '


    def update_job_status(self, mongo_coll_jobs, job_id, status):
        mongo_coll_jobs.find_one_and_update({"_id": job_id}, {"$set": {"status": status}})

    def update_job_retry(self, mongo_coll_jobs, job_id, retries):
        mongo_coll_jobs.find_one_and_update({"_id": job_id}, {"$set": {"retry": retries}})

    def remove_job(self, mongo_coll_jobs, job_id):
        mongo_coll_jobs.remove({"_id": job_id})

    def get_all_stock_info(self):
        mongo_coll = self._settings.get_mongo_coll_info()
        df_stock_info = pd.DataFrame(list(mongo_coll.find()))
        return df_stock_info

    # download_and_store_stock_info()
    def add_download_jobs(self, start, end=None):
        infos = self.get_all_stock_info()
        codes = infos['code']

        self.add_download_job(codes, start, end)

    def add_download_job(self, codes, start, end):
        mongo_coll_jobs = self._settings.get_mongo_coll_job()
        jobs = pd.DataFrame()
        jobs['code'] = codes
        jobs['action'] = 'load'
        jobs['start'] = start

        if end is None:
            jobs['end'] = None
        else:
            jobs['end'] = end
        jobs['status'] = 0
        # jobs = jobs.set_index('code')
        records = json.loads(jobs.T.to_json()).values()
        mongo_coll_jobs.insert(records)
        print jobs

    def addJob_Fundamental_Equity_IS(self, codes=None, start=None, end=None):
        mongo_coll_jobs = self._settings.get_mongo_coll_job()
        jobs = pd.DataFrame()

        if codes is None:
            infos = self.get_all_stock_info()
            codes = infos['code']

        jobs['code'] = codes
        jobs['action'] = 'EquityIS'
        jobs['start'] = start
        jobs['end'] = end

        jobs['status'] = 0

        records = json.loads(jobs.T.to_json()).values()
        mongo_coll_jobs.insert(records)


    def addJob_DownloadEquityMktByDate(self, start=None, end=None):
        db = self._settings.get_mongo_db('chinese_market', local=True)  # get mongo db
        coll_job = db[self._settings.MONGO_COLL_Job_Daily]

        jobs = pd.DataFrame()

        if end is None:
            end = datetime.today().strftime('%Y%m%d')

        if start is None:
            jobs['tradeDate'] = {end}
        else :
            days = self._factorfactory.getTradingDays(start, end)
            jobs['tradeDate'] = days.iloc[:, 0]

        jobs['task'] = self.TASK_DOWNLOAD_MARKET_EQUITY_BYDATE
        jobs['status'] = self.JOB_STATUS_READY
        jobs['retry'] = 0

        records = json.loads(jobs.T.to_json()).values()
        coll_job.insert(records)

    def addJob_DownloadStockFactorByDate(self, start=None, end=None):
        db = self._settings.get_mongo_db('chinese_market', local=True)  # get mongo db
        coll_job = db[self._settings.MONGO_COLL_Job_Daily]

        jobs = pd.DataFrame()

        if end is None:
            end = datetime.today().strftime('%Y%m%d')

        if start is None:
            jobs['tradeDate'] = {end}
        else :
            days = self._factorfactory.getTradingDays(start, end)
            jobs['tradeDate'] = days.iloc[:, 0]

        jobs['task'] = self.TASK_DOWNLOAD_EQUITY_FACTOR_BYDATE
        jobs['status'] = self.JOB_STATUS_READY
        jobs['retry'] = 0

        records = json.loads(jobs.T.to_json()).values()
        coll_job.insert(records)

    def get_price_from_mongo(self, db):
        mongo_coll_price = self._settings.get_mongo_coll_price()

        df_prices = pd.DataFrame(list(mongo_coll_price.find()))
        df_prices['date'] = pd.to_datetime(df_prices['date'] * 1000 * 1000)
        df_prices = df_prices.set_index('date')
        df_prices = df_prices.sort_index()
        return df_prices

    def update_latest_stock_price(self):
        # todo
        pass

class ChineseDataTools :
    db_name = 'chinese_market'


    def __init(self, settings):
        self.settings = settings
        self.db = self.settings.get_mongo_db(self.db_name, local=True)

    def getAllTickers(self):
        coll_prices = self.db[self.settings.MONGO_COLL_Rawdata_Equity_Market]
        coll_prices.find_all({})

## testing
if __name__ == '__main__' :
    settings = Settings()
    jobmgr = JobManager(settings)

    ''' Test case 1:
    '''
    #
    # jobmgr.add_download_jobs('2016-01-01')
    # jobmgr.process_job_download_stock_daily_price()

    ''' Test case 2:
    '''
    #jobmgr.addJob_Fundamental_Equity_IS()
    #jobmgr.processJob_Fundamental_Equity_IS()

    ''' Test case 3:
    '''
    jobmgr.restart_failed_jobs()
    #jobmgr.addJob_DownloadEquityMktByDate(start='20100101') #, end='20151231')
    jobmgr.processJob_DownloadEquityMktByDate()

    ''' Test case 4:
    '''
    #jobmgr.addJob_DownloadStockFactorByDate(start='20100101') #, end='20151231')
    mongo_db = settings.get_mongo_db("chinese_market", True)
    jobmgr.processJob_DownloadStockFactorByDate_TL(mongo_db)

    ''' Test case 5:
    '''
    #jobmgr.task_UpdateIndexInfo()
    #jobmgr.task_UpdateIndexComponents()

    #jobmgr.task_UpdatePrice()