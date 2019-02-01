import os

import util
import datetime
import newdb
import newdb.xrefsolve
import datafiles
import config

database=newdb.get_db()

__CAPITALIZATION_UPDATE_THRESHOLD=0.05 # 5%
def __capEquals(previous,new):
    if previous==0:
        if new==0: return True
        else: return False
    else:
        return abs(new/previous)<=1+__CAPITALIZATION_UPDATE_THRESHOLD and abs(new/previous)>=1-__CAPITALIZATION_UPDATE_THRESHOLD

def __barraDateToCompact(barraDate):
    return datetime.datetime.strptime(barraDate,"%d%b%Y")

#comma separated, string attributes enclosed in double quotes. floats always contain . , otherwise integers
def __getListFromBarraLine(line):
    tokens=line.strip().split(",")
    data=[]
    for token in tokens:
        if token[0]=='"' or token[-1]=='"': #string. it should be an and there, changed it to protect from compustat using commas within quotes
            data.append(token.strip('"').strip())
        elif token.find(".")<0: #integer
            data.append(int(token))
        else: #double
            data.append(float(token))
    return data

def __getSecId(barraId,cusip,ticker,source,timestamp,resolution,filepath):
    #return database.getSecidFromXref("BARRAID", barraId,timestamp, source,resolution) 
    #first step, see if mapping to secid exists
    barraSecid=database.getSecidFromXref("BARRAID", barraId,timestamp, source,resolution) 
#    if barraSecid is not None:
#        return barraSecid
    #only map successfully if both the cusip and the ticker map to the same secid
    cusipSecid=database.getSecidFromXref("CUSIP",cusip,timestamp,"compustat_idhist",resolution)
    tickerSecid=database.getSecidFromXref("TIC",ticker,timestamp,"compustat_idhist",resolution)
        
    #check if the cusipId and tickerid agree, even if none. Else, none
    if cusipSecid==tickerSecid:
        secid=cusipSecid
    else:
        secid=None
        
    #if the mapping is established and it agrees with both cusip and ticker, return it
    if barraSecid is not None and barraSecid==secid:
        return barraSecid
    #if the barraSecid is None and secid is not None, add it to the database
    elif barraSecid is None and secid is not None:
        database.insertTimelineRow(database.XREF_TABLE, {"secid" : secid, "xref_type": database.getXrefType("BARRAID"), "source" : database.getSourceType(source)}, {"value":barraId} , timestamp)
        util.info("Created new mapping from BarraId to SecId {}=>{}".format(barraId,secid))
        return secid
    #if the barraSecid is None and the secid is none, we could not established a mapping
    elif barraSecid is None and secid is None:
        util.warning("Could not map BARRAID to SECID through agreeing CUSIP and TICKER: BARRAID={}, CUSIP={}=>{}, TICKER={}=>{}".format(barraId,cusip,cusipSecid,ticker,tickerSecid))
        return None
    #there is a barraSecid, but it doesn't agree with the new mapping
    elif barraSecid is not None and barraSecid!=secid:
        note="BARRAID {} {}, CUSIP {} {}, TIC {} {}".format(barraId,barraSecid,cusip,cusipSecid,ticker,tickerSecid)
        database.insertMappingFailure(util.now(), source, filepath, barraId, barraSecid, secid, note)
        util.warning("Inconsistent existing mapping with mapping implied by xrefs: {}".format(note)) 
        #for now return old secid
        return barraSecid

def __verifyMapping(barraId,cusip,ticker,source,timestamp,resolution=None):
    #first step, see if mapping to secid exists
    barraSecid=database.getSecidFromXref("BARRAID", barraId,timestamp, source,resolution)    
    #if it doesn't no need to verify
    if barraSecid is None:
        return None
    
    #try to reestablish mapping based on cusip and secid
    #only map successfully if both the cusip and the ticker map to the same secid
    cusipSecid=database.getSecidFromXref("CUSIP",cusip,timestamp,"compustat_idhist",resolution)
    tickerSecid=database.getSecidFromXref("TIC",ticker,timestamp,"compustat_idhist",resolution)
    
    if not (barraSecid==tickerSecid and barraSecid==cusipSecid):
        return {"BARRAID":(barraId,barraSecid), "CUSIP":(cusip,cusipSecid), "TIC":(ticker,tickerSecid)}

def __removeUnwantedAttributes(data):
    del data["BARRID"]
    del data["TICKER"]
    del data["CUSIP"]
    del data["NAME"]
    del data["INTRA_MONTH_ADDITION"]
    
#    newData={}
#    newData["INDNAME1"]=data["INDNAME1"]
#    newData["INDNAME2"]=data["INDNAME2"]
#    newData["INDNAME3"]=data["INDNAME3"]
#    newData["INDNAME4"]=data["INDNAME4"]
#    newData["INDNAME5"]=data["INDNAME5"]
#    
#    data.clear()
#    data.update(newData)
    
def verifyMappings(filePath,source):
    return process(filePath, source, True)
    
def process(filePath,source,verifyOnly=False):
    #process the RSK files for now
    if filePath.find(".RSK.")<0:
        return
    file=open(filePath,"r")
    
    #The first 2 lines should be the pricedate and the modeldate
    tokens=file.readline().strip().split(":")
    if tokens[0]!="PriceDate":
        util.error("It doesn't seem like a barra daily format")
        raise Exception
    else:
        priceDate=__barraDateToCompact(tokens[1].strip())
    
    tokens=file.readline().strip().split(":")
    if tokens[0]!="ModelDate":
        util.error("It doesn't seem like a barra daily format")
        raise Exception
    else:
        #pass
        modelDate=__barraDateToCompact(tokens[1].strip())
        
    # If we have acquisition times, use these for real born time.
    # Else, use the priceDate + 1 day
    fileInfo=datafiles.read_info_file(filePath)
    if fileInfo['date_last_absent'] is not None:
        timestamp = util.convert_date_to_millis(fileInfo['date_first_present'])
        backfill=0;
        database.setAttributeAutoCreate(True)
    else:
        date=priceDate+datetime.timedelta(days=1)
        timestamp= util.convert_date_to_millis(date.strftime("%Y%m%d"))
        backfill=1
        database.setAttributeAutoCreate(True)
        
    #get the header names. comma separated, surrounded by double quotes
    line=file.readline()
    headers=__getListFromBarraLine(line)
        
    #init the dabase
    #database.dropXrefCache()
    #database.addXrefCache(timestamp) #cache xrefs
    
    #######MAPPING VERIFICATION CODE########
    inconcistentMappings=[]
    ########################################
    
    for line in file:        
        data=__getListFromBarraLine(line)
        
        if len(data)!=len(headers):
            util.warning("Skipping bad line: {}".format(line))
            continue
                
        data=dict(zip(headers,data))
        
        #######MAPPING VERIFICATION CODE########
        if verifyOnly:
            result=__verifyMapping(data["BARRID"], util.cusip8to9(data["CUSIP"]), data["TICKER"],source,timestamp,newdb.xrefsolve.preferUS) #mirror the getSecid call
            if result is not None: inconcistentMappings.append(result)
            continue
        ########################################
        
        secid=__getSecId(data["BARRID"], util.cusip8to9(data["CUSIP"]), data["TICKER"],source,timestamp,newdb.xrefsolve.preferUS,filePath)
        if secid is None:
            continue
        
        #Now, insert barra attributes and attribute values
        __removeUnwantedAttributes(data)
        for attributeName,attributeValue in data.iteritems():
            if isinstance(attributeValue, str):
                table="s"
            elif isinstance(attributeValue,int):
                table="n"
            elif isinstance(attributeValue,float):
                table="n"
            else:
                util.error("Dude, attribute values should be either int,float or str")
                raise
            
            #assert attributeName.startswith("INDNAME") and table=="s"
            
            #With the exeption of capitalization and price, the other barra attributes
            #are attributes that are evaluated monthly. for them, the date should be the
            #model date. price we ignore, while capitatlization, we only create a new tuple
            #if the capitalization has changed more than a threshould since the last date
            #for which we have a tuple
            if attributeName=="PRICE":
                continue
            elif attributeName=="CAPITALIZATION":
                database.insertAttribute("sec","n",secid,util.convert_date_to_millis(priceDate),source,attributeName,attributeValue,timestamp,None,backfill,False,True,__capEquals)
            else:
                database.insertAttribute("sec", table, secid, util.convert_date_to_millis(modelDate), source, attributeName, attributeValue, timestamp, None, backfill)
                
    file.close()
    
    #######MAPPING VERIFICATION CODE########
    if verifyOnly:
        return inconcistentMappings
    ########################################
    
if __name__=="__main__":
    #ammend barra data and add the INDNAME values
    
    newdb.init_db()
    database=newdb.get_db()
    #collect all the files processed so far
    processedFiles=database.getProcessedFilesTimeOrdered("barra")
    localDir=config.load_source_config("barra")["local_dir"]
    
    try:
        i=0
        for file in processedFiles:
            database.start_transaction()
            print datetime.datetime.now(), file
            process("/".join((os.environ["DATA_DIR"],localDir,file)),"barra")
            database.commit()
    except Exception, e:
        print e
        database.rollback()
    else:
        pass
        database.commit()