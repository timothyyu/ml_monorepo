import util
import properties
from newdb import xrefsolve
from util import LRU
import copy

class DBConsistencyError(Exception):
    pass

class DBQueryError(Exception):
    pass

class DBLogicBase:

    def __init__(self, config_file,databaseConnection):
        p = properties.Properties()
        p.load(open(config_file))
        dbConfig = p.getPropertyDict()
        self.__databaseConnection=databaseConnection
        self.__databaseConnection.init(dbConfig)
        self.__conn=self.__databaseConnection.conn
        self.__curs=self.__databaseConnection.curs
        
        #constants
        self.__MAX_STR_LEN = 32
        self.MAX_STR_LEN = self.__MAX_STR_LEN
        
        self.XREF_TABLE="xref"
        self.STOCK_TABLE="stock"
        self.SECURITY_TABLE="security"
        self.PROCESSED_FILES_TABLE="processed_files"
        self.PROCESSED_FILES_ATTR_STATS_TABLE="processed_files_att_stats"
        self.ATTRIBUTE_TYPE_TABLE="attribute_type"
        self.ATTR_TABLE="_attr_"
        self.PRICE_TABLE="price"
        self.PRICE_FULL_TABLE="price_full"
        self.DIVIDEND="dividend"
        self.SPLIT="split"
        self.SOURCE_TYPE="source_type"
        self.FUTURE_SPLIT="future_split"
        self.COMPANY_MAPPINGS="company_mappings"
        self.CO_ESTIMATES="co_estimates_"
        self.BROKERS="brokers"
        self.CURRENCY_TABLE="currency"
        self.CO_ACTUALS="co_actuals_"
        self.XREF_TYPE="xref_type"
        self.CO_ESTIMATE_FLAGS="co_estimate_flags"
        self.MAPPING_FAILURES="mapping_failures"
        self.BARRA="barra_"
        self.REUTERS="reuters_"
        self.EXRATE="exrate"
        
        #statistics
        self.__keepStats=True
        self.__rowsInserted=0;
        self.__rowsDeleted=0;
        self.__rowsUpdated=0;
        self.__rowsSelected=0;
        self.__attributeStats={}
                
        #mappings of names to internal codes
        self.__attTypes = dict()
        self.__sourceTypes = dict()
        self.__xrefTypes = dict()
        self.__securityTypes = dict()
        self.__exchangeTypes = dict()
        self.__countryTypes = dict()
        self.__currencyTypes = dict()
        self.__preloadCodes()
        
        self.__csToSecCache=LRU(100000)
        self.__secToCsCache=LRU(100000)
        
        self.__inserts=dict()
        self.__kills=dict()
        
        self.__brokerCache=LRU(100000)
        self.__companyMappingCache=dict()
        #automatically create unknown attributes
        self.__attAutoCreate=False
        self.__brokerAutoCreate=False
        self.__currencyAutoCreate=False
        
    ########## STATISTICS ##############
        
    def updateAttributeStats(self,type,inserted=0,killed=0):
        attStats=self.__attributeStats.get(type,None)
        if attStats is None:
            attStats=[0,0]
            self.__attributeStats[type]=attStats
        attStats[0]+=inserted
        attStats[1]+=killed
            
    def cloneAttributeStats(self):
        return copy.deepcopy(self.__attributeStats)
    
    def getRowStats(self):
        return (self.__rowsSelected,self.__rowsInserted,self.__rowsUpdated,self.__rowsDeleted)

    ######Methods provided by the database specific connection object#######
    def __getParam(self, param = None):
        return self.__databaseConnection.getParam(param)

    def __getQuoted(self, param):
        return self.__databaseConnection.getQuoted(param)

    def start_transaction(self):
        self.__databaseConnection.start_transaction()

    def commit(self):
        self.__databaseConnection.commit()

    def rollback(self):
        self.__databaseConnection.rollback()
    #################################

    #Mop-up
    def close(self):
        try:
            self.__curs.close()
            self.__conn.close()
        except:
            util.warning("Error closing db connection!")
            # Connection wasn't made, self._conn doesn't exist

    def __del__(self):
        self.close()
        
    #################################
                
    def __preloadCodes(self):
        util.debug("Loading Types from DB")
        self.execute("SELECT code, name,source FROM {}".format(self.ATTRIBUTE_TYPE_TABLE))
        for row in self.__curs.fetchall():
            self.__attTypes[(row['name'],row["source"])] = int(row['code'])
        util.debug(self.__attTypes)
        
        self.execute("SELECT code, name FROM {}".format(self.SOURCE_TYPE))
        for row in self.__curs.fetchall():
            self.__sourceTypes[row['name']] = int(row['code'])
        util.debug(self.__sourceTypes)

        self.execute("SELECT code, name FROM {}".format(self.XREF_TYPE))
        for row in self.__curs.fetchall():
            self.__xrefTypes[row['name']] = int(row['code'])
        util.debug(self.__xrefTypes)

        self.execute("SELECT code, name FROM security_type")
        for row in self.__curs.fetchall():
            self.__securityTypes[row['name']] = int(row['code'])
        util.debug(self.__securityTypes)

        self.execute("SELECT code, name FROM exchange")
        for row in self.__curs.fetchall():
            self.__exchangeTypes[row['name']] = int(row['code'])
        util.debug(self.__exchangeTypes)

        self.execute("SELECT code, name FROM country")
        for row in self.__curs.fetchall():
            self.__countryTypes[row['name']] = int(row['code'])
        util.debug(self.__countryTypes)

        self.execute("SELECT code, name FROM {}".format(self.CURRENCY_TABLE))
        for row in self.__curs.fetchall():
            self.__currencyTypes[row['name']] = int(row['code'])
        util.debug(self.__currencyTypes)
                                
    ########### helper methods for introducing new securities in the db
            
    def createNewCsid(self,coid,issueid,timestamp,country=None,currency=None, parse=True):
        assert parse is True or (country is not None and currency is not None)
    
        #invalidate cache
        self.__secToCsCache.clear()
        self.__csToSecCache.clear()
    
        if parse:    
            country=issueid[2:3]
            currency = 'NA'
    
            if country == '':
                country = 'US'
                currency = 'USD'
            elif country == 'C':
                country = 'CA'
                currency = 'CAD'
            elif country == 'W':
                country = 'NA'
                    
        history=self.getTimelineRowHistory(self.STOCK_TABLE, {"coid" : coid, "issueid": issueid})
        
        #not present
        if len(history)==0:
            secid=self.createNewSecurity("STOCK")
            self.insertTimelineRow(self.STOCK_TABLE, {"coid" : coid, "issueid": issueid}, {"secid": secid, "country" : self.getCountryType(country), "currency" : self.getCurrencyType(currency)},timestamp) 
        else:
            secid=history[0]["secid"]
            secidBorn=history[0]["born"]
            secidDied=history[0]["died"]
            self.killOrDeleteTimelineRow(self.STOCK_TABLE, {"coid" : coid, "issueid": issueid}, secidBorn)
            self.insertTimelineRow(self.STOCK_TABLE, {"coid" : coid, "issueid": issueid}, {"secid": secid, "country" : self.getCountryType(country), "currency" : self.getCurrencyType(currency)},timestamp,secidDied)
        return secid
                
    def createNewSecurity(self, type):
        self.execute("INSERT INTO {}(sectype) VALUES (%s)".format(self.SECURITY_TABLE), (self.getSecurityType(type),) )
        self.execute("SELECT LAST_INSERT_ID() as lastid")
        return self.__curs.fetchone()['lastid']
    
    ############ Data file processing methods ################
    def getProcessedFiles(self, source):
        seen = set()
        self.execute("SELECT path FROM {} WHERE source=%s".format(self.PROCESSED_FILES_TABLE), (self.getSourceType(source),))
        for row in self.__curs.fetchall():
            seen.add(row['path'])
        return seen

    def getProcessedFilesTimeOrdered(self,source):
        self.execute("SELECT path FROM {} WHERE source=%s ORDER BY ts ASC".format(self.PROCESSED_FILES_TABLE), (self.getSourceType(source),))
        return [row["path"] for row in self.__curs.fetchall()]

    def addProcessedFiles(self, source, path,processingTime=None,dateModified=None,reallyProcessed=True):
        #self.execute("INSERT INTO {} (source, path, ts,processing_time,rows_selected,rows_inserted,rows_updated,rows_deleted) VALUES ({)".format(self.PROCESSED_FILES_TABLE), (self.getSourceType(source), path, util.now(),processingTime)
        params={"source":self.getSourceType(source),"path":path,"ts":util.now(),"processing_time":processingTime,"date_modified":dateModified,"really_processed":reallyProcessed}
        sqlInsertAtts,sqlInsertValues=self.getInsertString(params)
        self.execute("INSERT INTO {}({}) VALUES({})".format(self.PROCESSED_FILES_TABLE,sqlInsertAtts,sqlInsertValues),params)
        
    def addProcessedFileAttributeStats(self,source,path,statsBefore,statsNow):
        for code,sn in statsNow.iteritems():
            sb=statsBefore.get(code,None)
            if sb is None: sb=(0,0)
    
            inserted=sn[0]-sb[0]
            killed=sn[1]-sb[1]
            if inserted==0 and killed==0:
                continue
            
            args={"source":self.getSourceType(source),"path":path,"type":code,"inserted":inserted,"killed":killed}
            sqlInsertAtts,sqlInsertValues=self.getInsertString(args)
            self.execute("INSERT INTO {}({}) VALUES({})".format(self.PROCESSED_FILES_ATTR_STATS_TABLE,sqlInsertAtts,sqlInsertValues),args)
            
    
    def getProcessedFilesLock(self):
        try:
            self.execute("INSERT INTO process_lock VALUES(1)")
            return True
        except:
            return False

    def releaseProcessedFilesLock(self):
        self.execute("DELETE FROM process_lock")
        
    def getLastProcessedFile(self,source):
        self.execute("SELECT path FROM {} WHERE source=%(source)s ORDER BY ts DESC LIMIT 1".format(self.PROCESSED_FILES_TABLE),{"source" : self.getSourceType(source)})
        row=self.__curs.fetchone()
        if row is None:
            return None
        else:
            return row["path"]
        
    def getLastProcessedFileTuple(self,source):
        self.execute("SELECT * FROM {} WHERE source=%(source)s ORDER BY ts DESC LIMIT 1".format(self.PROCESSED_FILES_TABLE),{"source" : self.getSourceType(source)})
        row=self.__curs.fetchone()
        if row is None:
            return None
        else:
            return row
    
    ########### identifier transformation methods ##############
    
    def getSecidFromCsid(self,coid,issueid,timestamp=None):
        
        secid=self.__csToSecCache.get((int(coid),issueid,timestamp),None)
        if secid is not None:
            return secid
        
        table=self.STOCK_TABLE
        row=self.getTimelineRow(table, {"coid":coid, "issueid":issueid}, timestamp)
        if row is None:
            return None
        else:            
            secid=row["secid"]
            self.__secToCsCache[(int(secid),timestamp)]=(int(coid),issueid)
            self.__csToSecCache[(int(coid),issueid,timestamp)]=int(secid)
            
            return secid
    
    def getCsidFromSecid(self,secid,timestamp=None):
        coid,issueid=self.__secToCsCache.get((int(secid),timestamp),(None,None))
        if coid is not None:
            return coid,issueid
        
        table=self.STOCK_TABLE
            
        row=self.getTimelineRow(table, {"secid":secid}, timestamp)
        if row is None:
            return None,None
        else:
            coid=row["coid"]
            issueid=row["issueid"]
            
            self.__secToCsCache[(int(secid),timestamp)]=(int(coid),issueid)
            self.__csToSecCache[(int(coid),issueid,timestamp)]=int(secid)
            
            return coid,issueid
        
    #in theory we would like every xref to point to a single secid.
    #unfortunately this doesn't happen. however using a sensible policy we
    #can resolve the confict. for instance, almost all conflicts in compustat
    #are due to companies in us and ca having the same ticker, or two issues
    #from the same company sharing a cusip.
    def getSecidFromXref(self,xrefType,xrefValue,timestamp=None,source=None,resolutionPolicy=xrefsolve.noneOnAmbiguity):
        #get authorititative sources
        if source is None:
            if xrefType=="BARRAID":
                source="barraid"
            elif xrefType=="TIC":
                source="compustat_idhist"
            elif xrefType=="CUSIP":
                source="compustat_idhist"
            elif xrefType=="SEDOL":
                source="compustat_idhist"
            elif xrefType=="ISIN":
                source="compustat_g_idhist"
        
        source=self.getSourceType(source)
        xrefType=self.getXrefType(xrefType)
        
        table=self.XREF_TABLE    
        rows=self.getRows(table, {'value':xrefValue, 'xref_type':xrefType,"source":source}, timestamp)
        
        if len(rows)==0:
            return None
        elif len(rows)==1:
            return rows[0]["secid"]
        elif resolutionPolicy is not None:
            return resolutionPolicy(self,rows,timestamp)
        else:
            raise 
    
    #occasionally, the compustat database enters a slightly inconsistent state
    #for a single secid. so, we also need a resolution policy, although 98%
    #of the time, for 99.99% of securities a secid should point to a single
    #xref
    def getXrefFromSecid(self,xrefType,secid,timestamp=None,source=None,resolutionPolicy=xrefsolve.noneOnAmbiguity):
        #get authorititative sources
        if source is None:
            if xrefType=="BARRAID":
                source="barraid"
            elif xrefType=="TIC":
                source="compustat_idhist"
            elif xrefType=="CUSIP":
                source="compustat_idhist"
            elif xrefType=="SEDOL":
                source="compustat_idhist"
            elif xrefType=="ISIN":
                source="compustat_g_idhist"
        
        source=self.getSourceType(source)
        xrefType=self.getXrefType(xrefType)
        
        table=self.XREF_TABLE
        rows=self.getRows(table, {'secid':secid, 'xref_type':xrefType,"source":source}, timestamp)
        if len(rows)==0:
            return None
        elif len(rows)==1:
            return rows[0]["value"]
        elif resolutionPolicy is not None:
            return resolutionPolicy(self,rows,timestamp)
        else:
            raise 
        
    ########### mappings of names to internal codes ##############
    
    def setAttributeAutoCreate(self,autoCreate):
        self.__attAutoCreate=autoCreate
        
    def getAttributeAutoCreate(self):
        return self.__attAutoCreate
    
    def createAttributeType(self,name,source,datatype,tableref):
        sourceCode=self.getSourceType(source)
        try:
            code=self.__attTypes[(name,sourceCode)]
        except:
            code=None
            
        if code is not None:
            util.warning("Tried to recreate an existing attribute: {}",type)
            return code
        
        self.execute("SELECT code from {} ORDER BY code DESC LIMIT 1".format(self.ATTRIBUTE_TYPE_TABLE))
        row=self.__curs.fetchone()
        code=row["code"] if (row is not None) else 0
        code=code+1
        util.info("Creating new attribute code for ({},{})=>{}".format(name,source,code))
        
        if datatype=="n":
            datatype=1
        elif datatype=="s":
            datatype=2
        elif datatype=="d":
            datatype=3
        elif datatype=="b":
            datatype=4
        
        params={"code":code,"name":name, "source":sourceCode,"datatype":datatype, "tableref":tableref}
        (queryk,queryv)=self.getInsertString(params)
        self.execute("INSERT INTO " + self.ATTRIBUTE_TYPE_TABLE + " (" + queryk + ") VALUES (" + queryv + ")", params)
        self.__attTypes[(name,sourceCode)]=code
        return code
    
    def getAttributeType(self, type,source,datatype=None,tableref=None):
        try:
            return self.__attTypes[(type,self.__sourceTypes[source])]
        except KeyError:
            if self.__attAutoCreate:
                return self.createAttributeType(type, source, datatype, tableref)
            else:
                util.error("Could not lookup attribute type: %s" % type)
                raise DBQueryError

    def getSourceType(self, type):
        try:
            return self.__sourceTypes[type]
        except KeyError:
            util.error("Could not lookup source type in db: %s" % type)
            raise

    def getXrefType(self, type):
        try:
            return self.__xrefTypes[type]
        except KeyError:
            util.error("Could not lookup xref type: %s" % type)
            raise

    def getSecurityType(self, type):
        try:
            return self.__securityTypes[type]
        except KeyError:
            util.error("Could not lookup security type: %s" % type)
            raise

    def getExchangeType(self, type):
        try:
            return self.__exchangeTypes[type]
        except KeyError:
            util.error("Could not lookup exchange type: %s" % type)
            raise

    def getCountryType(self, type):
        try:
            return self.__countryTypes[type]
        except KeyError:
            util.error("Could not lookup country type: %s" % type)
            raise

    def getCurrencyType(self, name):
        try:
            return self.__currencyTypes[name]
        except KeyError:        
            if self.__currencyAutoCreate:
                return self.createCurrencyType(name)
            else:
                util.error("Could not lookup currency type: %s" % name)
                raise DBQueryError
        
    def createCurrencyType(self,name):
        self.execute("SELECT code from {} ORDER BY code DESC LIMIT 1".format(self.CURRENCY_TABLE))
        row=self.__curs.fetchone()
        code=row["code"] if (row is not None) else 0
        code=code+1
        util.info("Creating new currency code for {}=>{}".format(name,code))
                
        params={"code":code,"name":name}
        (queryk,queryv)=self.getInsertString(params)
        self.execute("INSERT INTO " + self.CURRENCY_TABLE + " (" + queryk + ") VALUES (" + queryv + ")", params)
        self.__currencyTypes[name]=code
        return code
    
    def setCurrencyAutoCreate(self,auto):
        self.__currencyAutoCreate=auto
    
    def getCurrencyAutoCreate(self):
        return self.__currencyAutoCreate
        
    ######SQL formation convenience methods ##############    
    def getSelectString(self,attributes):
        if len(attributes)==0:
            return "*"
        else:
            return ",".join(attributes)
        
    #transform a list of attributes into a parameterized WHERE clause
    def getWhereTemplateString(self,attributes):
        atts=["{0}=%({0})s".format(a) for a in attributes]
        return " AND ".join(atts)
    
    #transform a list of attributes into a parameterized WHERE clause
    def getSetTemplateString(self,attributes):
        atts=["{0}=%({0})s".format(a) for a in attributes]
        return ", ".join(atts)
    
    def getInsertString(self, fields):
        queryk = []
        queryv = []
        for field in fields.iterkeys():
            queryk.append(self.__getQuoted(field))
            queryv.append(self.__getParam(field))
        return (", ".join(queryk), ", ".join(queryv))
    
    ##########data access and manipulation functionality ############
    
    #execute ad hoc sql query
    def execute(self, sqlstring, args=None):
        if util.DEBUG: 
            util.debug(sqlstring + " : " +  str(args))
            #self.__curs.execute("explain "+sqlstring)
            #util.debug(self.__curs.fetchone())
        
        self.__curs.execute(sqlstring, args)
            
        if self.__keepStats:
            rowcount=self.__curs.rowcount
            if rowcount==-1 or rowcount is None: rowcount=0
            command=sqlstring[0:6]
            if command=="SELECT": self.__rowsSelected+=rowcount
            elif command=="INSERT": self.__rowsInserted+=rowcount
            elif command=="UPDATE": self.__rowsUpdated+=rowcount
            elif command=="DELETE": self.__rowsDeleted+=rowcount
        
        return self.__curs
        
    #get all the rows that have a particular key and where live on a particular interval [born,died)
    def getRows(self,table,keys,born=None):
        assert born is None or isinstance(born,long)
        assert len(keys)>0
        
        sqlWhere=self.getWhereTemplateString(keys.iterkeys())

        if born is not None:
            params=keys.copy()
            params["born"]=born
            self.execute("SELECT * FROM {} WHERE {} AND born<=%(born)s AND (died IS NULL or died>%(born)s)".format(table,sqlWhere),params)
        else:
            params=keys;
            self.execute("SELECT * FROM {} WHERE {} AND (died IS NULL)".format(table,sqlWhere),params)
            
        return self.__curs.fetchall()
    
    #Blindly insert row, no checks whatsoever
    def insertRow(self,table,keys,data,born,died=None):
        assert isinstance(born,long) and born is not None
        assert len(keys)>0
        
        params=keys.copy()
        params.update(data)
        params["born"]=born
        params["died"]=died
        
        (k,v)=self.getInsertString(params)    
        self.execute("INSERT INTO {}({}) VALUES({})".format(table,k,v),params)
        
    def insertTuple(self,table,keys,data,replace = False):
        assert len(keys)>0
        
        params=keys.copy()
        params.update(data)
        
        (k,v)=self.getInsertString(params)    
        self.execute("{} INTO {}({}) VALUES({})".format("REPLACE" if replace else "INSERT", table,k,v),params)
                
    def updateRows(self,table,keys,data,timestamp=None, limit=None):
        assert timestamp is None or isinstance(timestamp,long)
        assert len(keys)>0
        assert limit is None or (isinstance(limit,int) and limit>0)
        
        sqlWhere=self.getWhereTemplateString(keys.iterkeys())
        sqlSet=self.getSetTemplateString(data.iterkeys())
        if limit is None:
            sqlLimit=""
        else:
            sqlLimit=" ORDER BY born DESC LIMIT {}".format(limit)
        
        if timestamp is not None:
            params=keys.copy()
            params.update(data)
            params["born1"]=timestamp
            self.execute("UPDATE {} SET {} WHERE {} AND born<=%(born1)s AND (died IS NULL or died>%(born1)s){}".format(table,sqlSet,sqlWhere,sqlLimit),params)
        else:
            params=keys.copy()
            params.update(data)
            self.execute("UPDATE {} SET {} WHERE {} AND (died IS NULL){}".format(table,sqlSet,sqlWhere,sqlLimit),params)
        
    #completely removes timeline row. this should only be used in the case that an insertion
    #causes a dead row with born=died
    def deleteRows(self,table,keys,timestamp=None,limit=None):
        assert timestamp is None or isinstance(timestamp,long)
        assert len(keys)>0
        
        sqlWhere=self.getWhereTemplateString(keys.iterkeys())
        if limit is None:
            sqlLimit=""
        else:
            sqlLimit=" ORDER BY born DESC LIMIT {}".format(limit)
        
        if timestamp is not None:
            params=keys.copy()
            params["born"]=timestamp
            self.execute("DELETE FROM {} WHERE {} AND born<=%(born)s AND (died IS NULL or died>%(born)s){}".format(table,sqlWhere,sqlLimit),params)
        else:
            params=keys.copy()
            self.execute("DELETE FROM {} WHERE {} AND (died IS NULL){}".format(table,sqlWhere,sqlLimit),params)
                
    #############################
    ### TIMELINE ROWS          ##
    #############################
    #By default, we would like our data to form a timeline. For the notion defined by keys,
    #our knowledge about it forms a timeline if 
    #(1)at any given time only a single row is active
    #(2)rows are only inserted in increasing born order 
    #(3)gaps can be present and signified by either the absensce of row at the interval
    #or preferable the presense of a row with null data
        
    def getTimelineRow(self,table,keys,timestamp=None):
        assert timestamp is None or isinstance(timestamp,long)
        assert len(keys)>0
                
        sqlWhere=self.getWhereTemplateString(keys.iterkeys())
        
        if timestamp is not None:
            params=keys.copy()
            params["born"]=timestamp
            self.execute("SELECT * FROM {} WHERE {} AND born<=%(born)s AND (died IS NULL or died>%(born)s) LIMIT 2".format(table,sqlWhere),params)
        else:
            params=keys;
            self.execute("SELECT * FROM {} WHERE {} AND (died IS NULL) ORDER BY born DESC LIMIT 2".format(table,sqlWhere),params)
            
        row=self.__curs.fetchone()
        
        if row is None:
            return None
        elif self.__curs.fetchone() is not None:
            util.error("getLiveRow returned more than one rows")
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending timestamp: {}".format(str(timestamp)))
            raise DBConsistencyError
        else:
            return row
        
    def getMostRecentTimelineRows(self,table,keys,data,limit=1,returnAllFields=False):
        assert isinstance(keys,dict) and len(keys)>0
        assert data is None or isinstance(data,dict)
        assert isinstance(limit,int) and limit>0
        
        if returnAllFields is True:
            sqlSelect="*"
        elif data is None:
            sqlSelect="born,died"
        else:
            sqlSelect=self.getSelectString(data.keys())
            sqlSelect=self.getSelectString((sqlSelect,"born","died"))      
        sqlWhere=self.getWhereTemplateString(keys)
        return self.execute("SELECT {} FROM {} WHERE {} ORDER BY born DESC LIMIT {}".format(sqlSelect,table,sqlWhere,limit), keys).fetchall()
            
    #Insert row in a timeline. The timeline is defined
    ############
    # VERY IMPORTANT
    #############
    #The code checks for equality between the data values of two tuples. In order for this to work
    #as expected, the provided data values and the data values in a typle must be of the same type.
    #E.g, if you provide data={"value":"0.1"} and the database stores value as a float, then the
    #comparison will return false (unequal) because "0.1"!=0.1
    
    #return rows inserted and killed as tuple (inserted,killed)
    def insertTimelineRow(self,table,keys,data,born,died=None,equals=util.dict_fields_eq):
        assert isinstance(born,long) and born is not None
        assert len(keys)>0
        
        mostRecentRows=self.getMostRecentTimelineRows(table, keys, data,2)
        mostRecent=None
        secondToMostRecent=None
        if len(mostRecentRows)==2:
            mostRecent=mostRecentRows[0]
            secondToMostRecent=mostRecentRows[1]
        elif len(mostRecentRows)==1:
            mostRecent=mostRecentRows[0]
        
        #cases that indicate non-consistent insertion:
        if mostRecent is not None and mostRecent["born"]>born:
            util.error("attempt for out-of-order insertion: {}".format(mostRecent))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending data: {}".format(str(data)))
            util.error("Offending timestamp: {}".format(str(born)))
            raise DBConsistencyError  
        elif mostRecent is not None and mostRecent["died"] is not None and mostRecent["died"]>born: #simply the inequality check suffices (because None>number always returs false), but keep it for clarity
            util.error("insert on a dead row: {}".format(mostRecent))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending data: {}".format(str(data)))
            util.error("Offending timestamp: {}".format(str(born)))
            raise DBConsistencyError        
            
        if mostRecent is None:#no history
            self.insertRow(table, keys, data, born, died)
            return (1,0)
        elif mostRecent["died"] is not None and mostRecent["died"]<born:
            self.insertRow(table, keys, data, born, died)
            return (1,0)
        elif mostRecent["died"]==born:#row that died on born
            if equals(mostRecent,data,data.iterkeys()):
                self.updateRows(table, keys, {"died":None}, born-1,1) #same data, ressurect old
                return (1,0)
            else:
                self.insertRow(table, keys, data, born,died)
                return (1,0)
        else: #existing live row            
            if equals(mostRecent,data,data.iterkeys()): #exact same data
                #pass
                return (0,0)
            elif mostRecent["born"]==born and secondToMostRecent is not None and secondToMostRecent["died"]==born and equals(secondToMostRecent,data,data.iterkeys()): #overwrite of existing row. see if secondToMostRecent needs to be resurrected
                self.deleteRows(table, keys, born, 1)
                self.updateRows(table, keys, {"died":None}, born-1,1)
                return (1,1)
            elif mostRecent["born"]==born:
                self.updateRows(table, keys, data, born,1)
                return (1,1)
            else:
                self.updateRows(table, keys, {"died":born}, born,1)
                self.insertRow(table, keys, data, born,died)
                return (1,1)
                
    #return rows inserted and killed as tuple (inserted,killed)
    def updateTimelineRow(self,table,keys,data,born,died=None,equals=util.dict_fields_eq):
        assert isinstance(born,long) and born is not None
        assert len(keys)>0
        
        mostRecentRows=self.getMostRecentTimelineRows(table, keys, data,2,True)
        mostRecent=None
        secondToMostRecent=None
        if len(mostRecentRows)==2:
            mostRecent=mostRecentRows[0]
            secondToMostRecent=mostRecentRows[1]
        elif len(mostRecentRows)==1:
            mostRecent=mostRecentRows[0]
        
        #cases that indicate non-consistent update:
        if mostRecent is not None and mostRecent["born"]>born:
            util.error("attempt for out-of-order insertion: {}".format(mostRecent))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending data: {}".format(str(data)))
            util.error("Offending timestamp: {}".format(str(born)))
            raise DBConsistencyError  
        elif mostRecent is not None and mostRecent is not None and mostRecent["died"]>born:
            util.error("insert on a dead row: {}".format(mostRecent))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending data: {}".format(str(data)))
            util.error("Offending timestamp: {}".format(str(born)))
            raise DBConsistencyError
        
        if mostRecent is None:#no history, insert the update values only, rest will got to db defaults
            self.insertRow(table, keys, data, born, died)
            return (1,0)
        elif mostRecent["died"] is not None and mostRecent["died"]<born:
            self.insertRow(table, keys, data, born, died)
            return (1,0)
        elif mostRecent["died"]==born:#row that died on born
            if equals(mostRecent,data,data.iterkeys()):
                self.updateRows(table, keys, {"died":None}, born-1,1) #same data, resurect old
                return (1,0)
            else:
                newData={}
                newData.update(data)
                for k,v in mostRecent.iteritems():
                    if k not in keys and k not in ("born","died") and k not in data: newData[k]=v      
                self.insertRow(table, keys, newData, born,died)
                return (1,0)
        else: #existing live row            
            if equals(mostRecent,data,data.iterkeys()): #exact same data
                #pass
                return (0,0)
            elif mostRecent["born"]==born and secondToMostRecent is not None and secondToMostRecent["died"]==born and equals(secondToMostRecent,data,data.iterkeys()): #overwrite of existing row. see if secondToMostRecent needs to be resurrected
                self.deleteRows(table, keys, born, 1)
                self.updateRows(table, keys, {"died":None}, born-1,1)
                return (1,1)
            elif mostRecent["born"]==born:
                self.updateRows(table, keys, data, born,1)
                return (1,1)
            else:
                self.updateRows(table, keys, {"died":born}, born,1) #kill existing row
                #self.insertRow(table, keys, data, born,died)
                newData={}
                newData.update(data)
                for k,v in mostRecent.iteritems():
                    if k not in keys and k not in ("born","died") and k not in data: newData[k]=v  
                self.insertRow(table, keys, newData, born,died)
                return (1,1)
                 
    #return rows killed or deleted (zero or one)       
    def killOrDeleteTimelineRow(self,table,keys,timestamp=None):
        assert timestamp is None or isinstance(timestamp,long)
        assert len(keys)>0
        
        mostRecentRows=self.getMostRecentTimelineRows(table, keys, None,1)
        if len(mostRecentRows)==0:
            mostRecentRow=None
        else:
            mostRecentRow=mostRecentRows[0]
        
        #cases that indicate non-consistent deletion:
        if mostRecentRow is not None and mostRecentRow["born"]>timestamp:
            util.error("attempt for out-of-order kill or delete: {}".format(mostRecentRow))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending timestamp: {}".format(str(timestamp)))
            raise DBConsistencyError  
        elif mostRecentRow is not None and mostRecentRow["died"] is not None and mostRecentRow["died"]>timestamp:
            util.error("attemp to kill or delete a dead row: {}".format(mostRecentRow[0]))
            util.error("Offending table: {}".format(table))
            util.error("Offending keys: {}".format(str(keys)))
            util.error("Offending timestamp: {}".format(str(timestamp)))
            raise DBConsistencyError   
        
        if mostRecentRow is None:
            return (0,0)
        elif mostRecentRow["died"] is not None and mostRecentRow["died"]<=timestamp: #nothing to delete. optimization, last case would pick it up
            return (0,0)
        elif mostRecentRow["born"]==timestamp:
            self.deleteRows(table, keys, timestamp, 1)
            #also resurrect previous. We assume that the previous was killed by the row that is now deleted
            self.updateRows(table, keys, {"died":None}, timestamp-1,1)
            return (0,1)
        else:
            self.updateRows(table, keys, {"died":timestamp}, timestamp, 1)
            return (0,1)
                            
    def getTimelineRowHistory(self,table,keys,asc=True):
        assert len(keys)>0
        
        sqlWhere=self.getWhereTemplateString(keys)
        order="ASC" if asc else "DESC"
        self.execute("SELECT * FROM {} WHERE {} ORDER BY born {}".format(table,sqlWhere,order),keys)
        
        rows=self.__curs.fetchall()
                
        return rows
                
    ##############################################################
            
    def __attributeCommon(self,target,datatype,attributeValue=None):
        if target == 'co':
            key = 'coid'
        elif target == 'sec':
            key = 'secid'
        else:
            util.error("Unkown target {}".format( target))
            raise DBQueryError
        
        if attributeValue is None:
            return key,None
        
        if datatype == 'n':
            value = float(attributeValue)
        elif datatype == 's':
            value = attributeValue[0:self.__MAX_STR_LEN]
        elif datatype == 'd':
            assert attributeValue.__class__ is long
            value=attributeValue
        else:
            util.error("Unkown datatype {}".format(datatype))
            raise DBQueryError
        
        return key,value
    
    
    def insertAttribute(self,target,datatype,id,date, source, attributeName, attributeValue,born,died=None,backfill=0,historical=False,compareWithRecent=False,valueEquals=(lambda x,y: x==y)):
        assert date.__class__ is long and born.__class__ is long and (died.__class__ is long or died is None)
        assert not (historical and compareWithRecent)
        
        code=self.getAttributeType(attributeName, source, datatype, target+self.ATTR_TABLE+datatype)
        key,value=self.__attributeCommon(target, datatype, attributeValue)
        
        #historical, no questions asked
        if historical:
            self.insertRow(target+self.ATTR_TABLE+datatype, {key:id, "type":code, "date":date},{"value":value,"backfill":backfill},born,died)
            updates=(1,0)
            self.updateAttributeStats(code, *updates)
        elif not compareWithRecent:
            updates=self.insertTimelineRow(target+self.ATTR_TABLE+datatype, {key:id, "type":code, "date":date},{"value":value,"backfill":backfill},born,died)
            self.updateAttributeStats(code, *updates)
        elif compareWithRecent:
            sqlTable=target+self.ATTR_TABLE+datatype
            sqlWhere=key+"=%(id)s AND type=%(type)s AND date<=%(date)s"
            if born is None:
                sqlWhere=sqlWhere+" AND died IS NULL"
            else:
                sqlWhere=sqlWhere+" AND born<=%(born)s AND (died is NULL OR died>%(born)s)"
    
            params={"id": id, "type": code, "date":date,"born":born}
            self.execute("SELECT value FROM {} WHERE {} ORDER BY date DESC,born DESC LIMIT 1".format(sqlTable, sqlWhere),params)
            row=self.__curs.fetchone() 
    
            if row is None or not valueEquals(row["value"],value):
                updates=self.insertTimelineRow(target+self.ATTR_TABLE+datatype, {key:id, "type":code, "date":date},{"value":value,"backfill":backfill},born,died)
                self.updateAttributeStats(code, *updates)
        
    def deleteAttribute(self,target,datatype,id,date, source, attributeName,born,historical=False):
        assert date.__class__ is long and born.__class__ is long
        
        code=self.getAttributeType(attributeName, source,datatype,target+self.ATTR_TABLE+datatype)
        key,value=self.__attributeCommon(target, datatype)
        
        if historical:
            self.deleteRows(target+self.ATTR_TABLE+datatype, {key:id, "type":code, "date":date},born)
            updates=(0,1)
        else:
            updates=self.killOrDeleteTimelineRow(target+self.ATTR_TABLE+datatype, {key:id, "type":code, "date":date},born)
        self.updateAttributeStats(code, *updates)
            
    def insertXref(self,secid,source,xref,value,born,died=None,historical=False):
        assert isinstance(born,long) and (died is None or isinstance(died,long))
        code=self.getAttributeType(xref, source, "s", self.XREF_TABLE)
        if historical:
            self.insertRow(self.XREF_TABLE, {"secid":secid, "source":self.getSourceType(source),"xref_type":self.getXrefType(xref)}, {"value":value}, born, died)
            updates=(1,0)
        else:
            updates=self.insertTimelineRow(self.XREF_TABLE, {"secid":secid, "source":self.getSourceType(source),"xref_type":self.getXrefType(xref)},  {"value":value}, born, died)
        self.updateAttributeStats(code, *updates)
            
    def deleteXref(self,secid,source,xref,born,historical=True):
        code=self.getAttributeType(xref, source, "s", self.XREF_TABLE)
        if historical:
            self.deleteRows(self.XREF_TABLE, {"secid":secid, "source":self.getSourceType(source),"xref_type":self.getXrefType(xref)}, born)
            updates=(0,1)
        else:
            updates=self.killOrDeleteTimelineRow(self.XREF_TABLE, {"secid":secid, "source":self.getSourceType(source),"xref_type":self.getXrefType(xref)}, born)
        self.updateAttributeStats(code, *updates)
    
    def setBrokerAutoCrate(self,auto):
        self.__brokerAutoCreate=auto
    
    def getBrokerId(self,source,source_brokerid,timestamp=None):
        #if timestamp==None:
        brokerid=self.__brokerCache.get((self.getSourceType(source),source_brokerid,timestamp),None)
        if brokerid is not None:
            return brokerid
        
        row=self.getTimelineRow(self.BROKERS, {"source":self.getSourceType(source),"source_brokerid":source_brokerid}, timestamp)
        
        if row is None and self.__brokerAutoCreate:
            brokerid=self.insertBroker(source, source_brokerid, None, timestamp)            
            self.__brokerCache[(self.getSourceType(source),source_brokerid,timestamp)]=brokerid
            return brokerid
        elif row is None:
            return None
        else:
            brokerid=row["brokerid"]
            self.__brokerCache[(self.getSourceType(source),source_brokerid,timestamp)]=brokerid
            return brokerid
            
    #The only purpose of allowing and tracking updates is for name changes
    def insertBroker(self,source,brokerid,name,born):
        if name is not None:
            name=name.strip()[0:self.__MAX_STR_LEN]
        if born==None:
            born=util.now()
        rows=self.getTimelineRowHistory(self.BROKERS, {"source":self.getSourceType(source),"source_brokerid":brokerid})
        #rows=sorted(rows,key=lambda row:row["born"])
        if len(rows)==0: #allowed scenario 1: new broker
            row=self.execute("SELECT MAX(`brokerid`) as max FROM {}".format(self.BROKERS)).fetchone()
            newid=row["max"]+1 if row["max"] is not None else 1
            self.insertRow(self.BROKERS, {"brokerid":newid}, {"source":self.getSourceType(source),"source_brokerid":brokerid,"name":name}, born)
            return newid
        elif born>=rows[-1]["born"]:#allowd scenario 2:update current broker
            currentid=rows[-1]["brokerid"]
            self.insertTimelineRow(self.BROKERS, {"brokerid":currentid,"source":self.getSourceType(source),"source_brokerid":brokerid}, {"name":name}, born)
            return currentid
        elif born<rows[0]["born"] and name==rows[0]["name"]:#allowed scenario 3: push broker's record with oldest born date to the past
            self.updateRows(self.BROKERS, {"brokerid":rows[0]["brokerid"]}, {"born":born}, rows[0]["born"])
            return rows[0]["brokerid"]
        elif born<rows[0]["born"] and rows[0]["name"] is None: #allowed scenario 4: as before, but update brokers name if null
            self.updateRows(self.BROKERS, {"brokerid":rows[0]["brokerid"]}, {"born":born,"name":name}, rows[0]["born"])
            return rows[0]["brokerid"]
        else:
            util.error("Out-of-order broker update")
            raise DBConsistencyError
        
    def insertCoEstimate(self,rkd,source,measureName,datatype,source_brokerid,date,orig,value,currency,born,died=None,backfill=0):
        #assert isinstance(date,long)
        assert isinstance(orig,long)
        assert isinstance(born,long)
        assert died is None or isinstance(died,long)
        assert datatype in ("n","b","d")
        
        table=self.CO_ESTIMATES+datatype
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        brokerid=self.getBrokerId(source, source_brokerid, None)
        currencyCode=self.getCurrencyType(currency)
        if datatype=="n" and value is not None: value=float(value)
        if datatype=="d": assert isinstance(value,long)
        if datatype=="b" and value is not None: value=str(value)
        
#        if currencyCode > 127:
#            util.error("Tried to insert currency code {}, in table {} for rkd {}. Aborting...".format(currencyCode, table, rkd))
#            return
        
#        if historical:
#            self.insertRow(table, {"coid":coid,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig}, {"value":value,"backfill":backfill,"currency":currencyCode}, born, died)
#        else:
        updates=self.insertTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig}, {"value":value,"backfill":backfill,"currency":currencyCode}, born, died,util.dict_fields_eq_num_stable)
        self.updateAttributeStats(measureCode, *updates)
    
    def insertCoEstimateFlags(self,rkd,source,measureName,datatype,source_brokerid,date,orig,orig2,flag,born,died=None,backfill=0):
                #assert isinstance(date,long)
        assert isinstance(orig,long)
        assert isinstance(born,long)
        assert died is None or isinstance(died,long)
        assert datatype in ("n","b","d")
        assert flag in ('C','U','N','T','S') #haha
        
        table=self.CO_ESTIMATE_FLAGS
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        brokerid=self.getBrokerId(source, source_brokerid, None)
        
#        if historical:
#            raise DBQueryError
#        else:
        updates=self.insertTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig,"orig2":orig2,"flag":flag}, {"backfill":backfill}, born, died,util.dict_fields_eq)
        self.updateAttributeStats(measureCode, *updates)
    
    def deleteCoEstimateFlags(self,rkd,source,measureName,datatype,source_brokerid,date,orig,timestamp):
                #assert isinstance(date,long)
        assert isinstance(orig,long)
        assert isinstance(timestamp,long)
        assert datatype in ("n","b","d")
        
        table=self.CO_ESTIMATE_FLAGS
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        brokerid=self.getBrokerId(source, source_brokerid, None)

        #get all rows associated with orig
        params={"rkd":rkd,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig}
        rows=self.execute("SELECT orig2,flag,died FROM {} WHERE rkd=%(rkd)s AND type=%(type)s AND brokerid=%(brokerid)s AND date=%(date)s AND orig=%(orig)s".format(table), params)
        
        for row in rows:
            if row["died"] is None:
                updates=self.killOrDeleteTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig,"orig2":row["orig2"],"flag":row["flag"]}, timestamp)
                self.updateAttributeStats(measureCode, *updates)
        
    def deleteCoEstimate(self,rkd,source,measureName,datatype,source_brokerid,date,orig,born):
        #assert isinstance(date,long)
        assert isinstance(orig,long)
        assert isinstance(born,long)
        assert datatype in ("n","b","d")
        
        table=self.CO_ESTIMATES+datatype
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        brokerid=self.getBrokerId(source, source_brokerid, None)
        
#        if historical:
#            self.deleteRow(table, {"coid":coid,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig}, born)
#        else:
        updates=self.killOrDeleteTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date,"brokerid":brokerid,"orig":orig}, born)
        self.updateAttributeStats(measureCode, *updates)
            
    def insertCoActual(self,rkd,source,measureName,datatype,date,value,currency,born,died=None,backfill=0):
        #assert isinstance(date,long)
        assert isinstance(born,long)
        assert died is None or isinstance(died,long)
        assert datatype in ("n","d")
        
        table=self.CO_ACTUALS+datatype
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        currencyCode=self.getCurrencyType(currency)
        if datatype=="n" and value is not None: value=float(value)
        if datatype=="d": assert isinstance(value,long)
        
        #if historical:
        #    self.insertRow(table, {"rkd":rkd,"type":measureCode,"date":date}, {"value":value,"currency":currencyCode,"backfill":backfill}, born, died)
        #else:
        updates=self.insertTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date}, {"value":value,"currency":currencyCode,"backfill":backfill}, born, died,util.dict_fields_eq_num_stable)
        self.updateAttributeStats(measureCode, *updates)
    
    def deleteCoActual(self,rkd,source,measureName,datatype,date,born):
        assert isinstance(born,long)
        assert datatype in ("n","d")
        
        table=self.CO_ACTUALS+datatype
        measureCode=self.getAttributeType(measureName, source,datatype,table)
        
        #if historical:
        #    self.deleteRow(table, {"coid":coid,"type":measureCode,"date":date}, born)
        #else:
        updates=self.killOrDeleteTimelineRow(table, {"rkd":rkd,"type":measureCode,"date":date}, born)
        self.updateAttributeStats(measureCode, *updates)
                
    def insertMappingFailure(self,failureTimestamp,source,filePath,xref,oldId,newId,notes):
        assert isinstance(failureTimestamp,long)
        
        params={"failure_timestamp":failureTimestamp, "source":self.getSourceType(source),"filepath":filePath, "xref":xref,"old_id":oldId, "new_id":newId,"notes":notes}
        (k,v)=self.getInsertString(params)    
        self.execute("INSERT INTO {}({}) VALUES({})".format(self.MAPPING_FAILURES,k,v),params)
        