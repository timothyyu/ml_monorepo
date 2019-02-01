import dateutil
import zipfile
import datetime
import util
import datafiles
import newdb
import os
import config

database=newdb.get_db()

MODE="HISTORICAL"

MULTEX_EXCHANGE_MAP = {
    '7': 'TSE',
    '11': 'NYSE',
    '12': 'AMEX',
#    '13': '?',
    '14': 'NASD',
#    '15': '?',
#    '17': '?',
    '19': 'OTC',
    }

def __getOrCreateSecid(coid,issueid,country,currency,timestamp):
    secid=database.getSecidFromCsid(coid, issueid, timestamp)
    if secid is not None:
        return secid
    else:
        return database.createNewCsid(coid,issueid,timestamp,country,currency, parse=False)

def __insertExchangeHistorical(secid,exchangeAttributeName,exchange,source,born,died,backfill=1):
    if exchange in MULTEX_EXCHANGE_MAP:
        util.debug("Inserting new Exchange")
        #database.insertHistoricalAttribute('sec', 'n', secid, exchangeAttributeName, database.getExchangeType(MULTEX_EXCHANGE_MAP[exchange]), born, source , born, died,backfill)
        database.insertAttribute("sec", "n", secid, 0L, source, exchangeAttributeName, database.getExchangeType(MULTEX_EXCHANGE_MAP[exchange]), born, died, backfill, True)
    else:
        #database.handleAttribute('sec', 'n', secid, exchangeAttributeName, born, None, born, source, died,backfill)
        util.debug("Unknown exchange for secid={}".format(secid))
    
def __insertXrefHistorical(secid,xrefType,xrefValue,source,born,died=None):
    #database.insertRow(database.XREF_TABLE,{"secid" : secid ,"xref_type" : database.getXrefType(xrefType), "source" : database.getSourceType(source)},{"value":xrefValue},born,died)
    database.insertXref(secid, source, xrefType, xrefValue, born, died, True)
def __deleteXrefHistorical(secid,xrefType,source,born):
    #database.deleteRows(database.XREF_TABLE,{"secid" : secid ,"xref_type" : database.getXrefType(xrefType), "source" : database.getSourceType(source)},born)
    database.deleteXref(secid, source, xrefType, born, True)
    
def __deleteExchangeHistorical(secid,exchangeAttributeName,exchange,source,born):
    if exchange in MULTEX_EXCHANGE_MAP:
        #database.deleteHistoricalAttribute('sec', 'n', secid, exchangeAttributeName, born, source , born)
        database.deleteAttribute("sec", "n", secid, 0L, source, exchangeAttributeName, born, True)

#Get the deltas.
def __getDeltas(filepath,source,treatFutureData=False):
    ######get the previously processed file##########
    
    localDir=config.load_source_config(source)["local_dir"]
    previousData=set()
    previousFileName=database.getLastProcessedFile(source)
    if previousFileName is not None:
        previousFileName=os.environ["DATA_DIR"]+"/"+localDir+"/"+previousFileName
        previousFileInfo=datafiles.read_info_file(previousFileName)
        previousFileDate=previousFileInfo["date_first_present"]

        firstLoad=False
        zf=zipfile.ZipFile(previousFileName)
        names = zf.namelist()
        assert len(names) == 1
        file = zf.open(names[0])
        
        #skip header
        file.readline()
        for line in file:
            if treatFutureData:
                effectiveDate=line.strip().split("|")[4]
                effectiveDate=dateutil.parser.parse(effectiveDate + " 00:00:00.000000 UTC")
                if effectiveDate<previousFileDate:
                    previousData.add(line) 
            else:
                previousData.add(line)
            
        file.close()
        zf.close()
    else:
        firstLoad=True
                
    ##########get deltas from previous file#############
    currentData=set()
    zf=zipfile.ZipFile(filepath)
    names = zf.namelist()
    assert len(names) == 1
    file = zf.open(names[0])
    
    #skip header
    file.readline()
    for line in file:
        currentData.add(line)
        
    file.close()
    zf.close()
            
    newData=currentData-previousData
    removedData=previousData-currentData
    
    return (newData,removedData,firstLoad)

def __lineToDict(line):
    info={}
    tokens = line.strip().split('|')
    info["coid"] = int(tokens[0])
    info["issueid"] = tokens[1]
    info["attributeName"] = tokens[2]
    info["attributeValue"] = tokens[3]
    info["start"] = dateutil.parser.parse(tokens[4] + " 00:00:00.000000 UTC")
    if tokens[5]>"20500101":
        info["end"]=None
    else:
        info["end"] = dateutil.parser.parse(tokens[5] + " 00:00:00.000000 UTC")+datetime.timedelta(days=1)
            
    country=tokens[1][2:3]
    currency = 'NA'
    
    if country == '':
        country = 'US'
        currency = 'USD'
    elif country == 'C':
        country = 'CA'
        currency = 'CAD'
    elif country == 'W':
        country = 'NA'
    else:
        util.error("Unknown Country: " + country)
        raise Exception
    
    info["currency"]=currency
    info["country"]=country
    
    return info
    

def process(filepath, source):
    if MODE=="HISTORICAL":
        __processHistorical(filepath, source)
    elif MODE=="LIVE":
        pass
        #__processLive(filepath,source)
    
#processing compustat_idhist as historical information has the following peculiarities.
#First, between two updates, compustat can not only provide new info, but also undo old info!
#Second, info about older dates can be provided.
def __processHistorical(filepath,source):
    #currentFileInfo = datafiles.read_info_file(filepath)
    #currentFileDate= currentFileInfo['date_first_present']
    #currentFileTimestamp = util.convert_date_to_millis(currentFileDate)
            
    #set autocreate attributes
    autocreate=database.getAttributeAutoCreate()
    database.setAttributeAutoCreate(True)

    (newData,removedData,firstLoad)=__getDeltas(filepath, source)
        
    ######process the deltas##########
    ####Important!!!! To maintain consistency they should processed in ascending effective date
    removedData=list(removedData)
    removedData.sort(key=lambda x : x.split("|")[4])
    for line in removedData:
        info=__lineToDict(line)
            
        born=util.convert_date_to_millis(info["start"])
        died=None if info["end"] is None else util.convert_date_to_millis(info["end"])

        #check row quality
        if died is not None and died<=born:
            continue
        if info["attributeValue"]=="":
            continue

        util.debug("Getting/Inserting Security {}.{}, {}".format(info["coid"],info["issueid"],born))
        secid=__getOrCreateSecid(info["coid"], info["issueid"], info["country"], info["currency"], born)
                                                                                    
        if info["attributeName"] == "EXCHG":
            __deleteExchangeHistorical(secid, info["attributeName"], info["attributeValue"], source, born)
        else:
            __deleteXrefHistorical(secid, info["attributeName"], source, born)
        
        
    ######process the deltas##########
    ####Important!!!! To maintain consistency they should processed in ascending effective date
    newData=list(newData)
    newData.sort(key=lambda x : x.split("|")[4])
    for line in newData:
        info=__lineToDict(line)
            
        born=util.convert_date_to_millis(info["start"])
        died=None if info["end"] is None else util.convert_date_to_millis(info["end"])
        
        #check row quality
        if died is not None and died<=born:
            continue
        if info["attributeValue"]=="":
            continue
        
        util.debug("Getting/Inserting Security {}.{}, {}".format(info["coid"],info["issueid"],born))
        secid=__getOrCreateSecid(info["coid"], info["issueid"], info["country"], info["currency"], born)
        
        if info["attributeName"] == "EXCHG":
            __insertExchangeHistorical(secid, info["attributeName"], info["attributeValue"], source, born, died,1)
        else:
            __insertXrefHistorical(secid, info["attributeName"], info["attributeValue"], source, born,died)
        
    #revert attribute autocreate
    database.setAttributeAutoCreate(autocreate)
            
if __name__=="__main__":
    #util.DEBUG=True
    newdb.init_db()
    database=newdb.get_db()
    database.start_transaction()

