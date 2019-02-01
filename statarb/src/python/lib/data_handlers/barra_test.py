import os
import string

import util
import datetime
import newdb
import datafiles
#import config

database = newdb.get_db()

__CAPITALIZATION_UPDATE_THRESHOLD = 0.03 # 5%
def __capEquals(previous, new):
    if previous == 0:
        if new == 0: return True
        else: return False
    else:
        return abs(new / previous) <= 1 + __CAPITALIZATION_UPDATE_THRESHOLD and abs(new / previous) >= 1 - __CAPITALIZATION_UPDATE_THRESHOLD

def __barraDateToCompact(barraDate):
    return datetime.datetime.strptime(barraDate, "%d%b%Y")

#comma separated, string attributes enclosed in double quotes. floats always contain . , otherwise integers
def __getListFromBarraLine(line):
    tokens = line.strip().split(",")
    data = []
    try:
        for token in tokens:
            if token[0] == '"' or token[-1] == '"': #string. it should be an and there, changed it to protect from compustat using commas within quotes
                data.append(token.strip('"').strip())
            elif token.find(".") < 0: #integer
                data.append(int(token))
            else: #double
                data.append(float(token))
        return data
    except ValueError, e:
        util.error("Error processing line: {}".format(line))
        util.error(str(e))
        return []

def __removeUnwantedAttributes(data):
    if "BARRID" in data: del data["BARRID"]
    #del data["TICKER"]
    #del data["CUSIP"]
    #del data["NAME"]
    if "INTRA_MONTH_ADDITION" in data: del data["INTRA_MONTH_ADDITION"]

def insertBarraAttribute(datatype, barraid, date, source, attributeName, attributeValue, born, backfill=0, compareWithRecent=False, valueEquals=(lambda x, y: x == y)):
    assert date.__class__ is long and born.__class__ is long
    assert len(barraid) == 7
    assert datatype in ("n", "s")
    
    table = database.BARRA + datatype
    attrType = database.getAttributeType(attributeName, source, datatype, table)
    if datatype == 'n':
        value = float(attributeValue)
    elif datatype == 's':
        value = str(attributeValue)[0:database.MAX_STR_LEN]
        
    if not compareWithRecent:
        updates = database.insertTimelineRow(table, {"barraid":barraid, "type":attrType, "date":date}, {"value":value, "backfill":backfill}, born)
        database.updateAttributeStats(attrType, *updates)
    else:
        sqlWhere = "barraid=%(barraid)s AND type=%(type)s AND date<=%(date)s"
        if born is None:
            sqlWhere = sqlWhere + " AND died IS NULL"
        else:
            sqlWhere = sqlWhere + " AND born<=%(born)s AND (died IS NULL OR died>%(born)s)"

        params = {"barraid": barraid, "type": attrType, "date":date, "born":born}
        row = database.execute("SELECT value FROM {} WHERE {} ORDER BY date DESC,born DESC LIMIT 1".format(table, sqlWhere), params).fetchone()

        if row is None or not valueEquals(row["value"], value):
            updates = database.insertTimelineRow(table, {"barraid":barraid, "type":attrType, "date":date}, {"value":value, "backfill":backfill}, born)
            database.updateAttributeStats(attrType, *updates)
            
    #extra processing for TICKER,CUSIP
    if attributeName == "TICKER":
        database.killOrDeleteTimelineRow(database.BARRA + "xref", {"xref_type":2, "value":attributeValue}, date)
        database.insertTimelineRow(database.BARRA + "xref", {"barraid":barraid, "xref_type":2}, {"value":attributeValue}, date)
    elif attributeName == "CUSIP":
        database.killOrDeleteTimelineRow(database.BARRA + "xref", {"xref_type":1, "value":util.cusip8to9(attributeValue)}, date)
        database.insertTimelineRow(database.BARRA + "xref", {"barraid":barraid, "xref_type":1}, {"value":util.cusip8to9(attributeValue)}, date)

def updateBarraRef(source, barraid, cusip, timestamp, historical):
    #get existing barraref
    refTable = database.BARRA + "ref"
    refTable = refTable + "_hist" if historical else refTable 
    code = database.getAttributeType("BARRAID", source, "s", refTable)
    
    row = database.getTimelineRow(refTable, {"barraid":barraid}, timestamp)
    barraSecid = None if row is None else row["secid"]
    
    #get the implied mapping based on cusip
    cusipSecid = database.getSecidFromXref("CUSIP", cusip, timestamp, "compustat_idhist", newdb.xrefsolve.preferUS)
    
    if barraSecid is None and cusipSecid is None:
        return None
    elif barraSecid is None and cusipSecid is not None:
        #database.insertTimelineRow(refTable, {"secid":cusipSecid}, {"barraid":barraid}, timestamp)
        updates = database.killOrDeleteTimelineRow(refTable, {"secid":cusipSecid}, timestamp)
        database.updateAttributeStats(code, *updates)
        
        updates = database.insertTimelineRow(refTable, {"barraid":barraid}, {"secid":cusipSecid}, timestamp)
        database.updateAttributeStats(code, *updates)
        
        return cusipSecid
    elif barraSecid is not None and cusipSecid is not None and barraSecid == cusipSecid:
        return barraSecid
    elif barraSecid is not None and cusipSecid is not None and barraSecid != cusipSecid:
        updates = database.killOrDeleteTimelineRow(refTable, {"secid":cusipSecid}, timestamp)
        database.updateAttributeStats(code, *updates)
        
        updates = database.insertTimelineRow(refTable, {"barraid":barraid}, {"secid":cusipSecid}, timestamp)
        database.updateAttributeStats(code, *updates)
        
        return cusipSecid
    else: #barraSecid is not None and cusipSecid is None
        updates = database.killOrDeleteTimelineRow(refTable, {"barraid":barraid}, timestamp) #only one should be needed
        database.updateAttributeStats(code, *updates)
        
        return None
    
#remove non printable characters that can have creeped in name
def __printableString(name):
    #check first if it is printable
    printable = reduce(lambda x, y: x and (y in string.printable), name, True)
    if printable:
        return name
    else:
        newName = [c for c in name if c in string.printable]
        newName = ''.join(newName).strip()
        return newName

def verifyMappings(filePath, source):
    return process(filePath, source, True)
    
def process(filePath, source, verifyOnly=False):
    #process the RSK files for now
    if filePath.find(".RSK.") < 0:
        return
    
    file = open(filePath, "r")
    
    #The first 2 lines should be the pricedate and the modeldate for daily files
    #For the monthly files it is just the model date
    
    #check if it is a daily file or a monthly file. Check if the first line contains PriceDate
    firstLine = file.readline()
    if "PriceDate" in firstLine:
        daily = True
        file.seek(0) #get to the first line again
        
        tokens = file.readline().strip().split(":")
        if tokens[0] != "PriceDate":
            util.error("It doesn't seem like a barra daily format")
            raise Exception
        else:
            priceDate = __barraDateToCompact(tokens[1].strip())
                
        tokens = file.readline().strip().split(":")
        if tokens[0] != "ModelDate":
            util.error("It doesn't seem like a barra daily format")
            raise Exception
        else:
            modelDate = __barraDateToCompact(tokens[1].strip())
    else:
        daily = False
        file.seek(0) #get to the first line again
        
        token = file.readline().strip()
        priceDate = __barraDateToCompact(token)
        modelDate = __barraDateToCompact(token)

    # If we have acquisition times, use these for real born time.
    # Else, use the priceDate + 1 day
    fileInfo = datafiles.read_info_file(filePath)
    if fileInfo['date_last_absent'] is not None:
        timestamp = util.convert_date_to_millis(fileInfo['date_first_present'])
        backfill = 0;
    else:
        if daily:
            date = priceDate + datetime.timedelta(days=1)
        else:
            date = priceDate + datetime.timedelta(days=2)
        timestamp = util.convert_date_to_millis(date.strftime("%Y%m%d"))
        backfill = 1
        
    database.setAttributeAutoCreate(True)
        
    priceDate = util.convert_date_to_millis(priceDate)
    modelDate = util.convert_date_to_millis(modelDate)
        
    #get the header names. comma separated, surrounded by double quotes
    line = file.readline()
    headers = __getListFromBarraLine(line)
            
    for line in file:        
        data = __getListFromBarraLine(line)
        
        if len(data) != len(headers):
            util.warning("Skipping bad line: {}".format(line))
            continue
                
        data = dict(zip(headers, data))
                
        barraid = data["BARRID"]
        cusip = util.cusip8to9(data["CUSIP"])
        #updateBarraRef(barraid, cusip, timestamp, False)
        updateBarraRef(source, barraid, cusip, priceDate, True)
                
        #Now, insert barra attributes and attribute values
        __removeUnwantedAttributes(data)
        for attributeName, attributeValue in data.iteritems():
            if isinstance(attributeValue, str):
                table = "s"
            elif isinstance(attributeValue, int):
                table = "n"
            elif isinstance(attributeValue, float):
                table = "n"
            else:
                util.error("Dude, attribute values should be either int,float or str")
                raise
            
            
                        
            #With the exeption of capitalization and price, the other barra attributes
            #are attributes that are evaluated monthly. for them, the date should be the
            #model date. price we ignore, while capitatlization, we only create a new tuple
            #if the capitalization has changed more than a threshould since the last date
            #for which we have a tuple
            if attributeName == "PRICE":
                continue
            elif attributeName == "CAPITALIZATION":
                insertBarraAttribute("n", barraid, priceDate, source, attributeName, attributeValue, timestamp, backfill, True, __capEquals)
            elif attributeName in ("TICKER", "CUSIP", "NAME"):
                #protect against crappy names:
                if attributeName == "NAME": attributeValue = __printableString(attributeValue)
                insertBarraAttribute("s", barraid, priceDate, source, attributeName, attributeValue, timestamp, backfill, True)
            else:
                insertBarraAttribute(table, barraid, modelDate, source, attributeName, attributeValue, timestamp, backfill)
                
    file.close()
    
def regenerateMappings():
    #get the cusips
    rows = database.execute("SELECT * FROM {} WHERE type={} ORDER BY born,barraid".format(database.BARRA + "s", database.getAttributeType("CUSIP", "barra", None, None))).fetchall()
    for row in rows:
        #kill whoever owned the cusip
        database.killOrDeleteTimelineRow("barra_xref", {"xref_type":1, "value":util.cusip8to9(row["value"])}, row["date"])
        database.insertTimelineRow("barra_xref", {"barraid":row["barraid"], "xref_type":1}, {"value":util.cusip8to9(row["value"])}, row["date"])
        
        #get the tickers
    rows = database.execute("SELECT * FROM {} WHERE type={} ORDER BY born,barraid".format(database.BARRA + "s", database.getAttributeType("TICKER", "barra", None, None))).fetchall()
    for row in rows:
        #kill whoever owned the cusip
        database.killOrDeleteTimelineRow("barra_xref", {"xref_type":2, "value":row["value"]}, row["date"])
        database.insertTimelineRow("barra_xref", {"barraid":row["barraid"], "xref_type":2}, {"value":row["value"]}, row["date"])
    
if __name__ == "__main__":
    #ammend barra data and add the INDNAME values
    
    newdb.init_db(os.environ["DB_CONFIG_FILE"])
    database = newdb.get_db()
    #collect all the files processed so far
    processedFiles = database.getProcessedFilesTimeOrdered("barra")
    
    #database.start_transaction()
    
    try:
        database.start_transaction()
        regenerateMappings();
        database.commit()
#        i = 0
#        for file in processedFiles:
#            if file=="20100401/USE3S1003.RSK.439dbb03":
#                continue            
#            path="/".join((os.environ["DATA_DIR"], "barra","use3s_init_load", file))
#            print datetime.datetime.now(), file
#            if not os.path.exists(path):
#                print "Not found, looking in other directory"
#                path="/".join((os.environ["DATA_DIR"], "barra","use3s_daily", file))
#            if not os.path.exists(path):
#                print "Not found, looking in other directory"
#                path="/".join((os.environ["DATA_DIR"], "barra","use3s_monthly", file))
#            if not os.path.exists(path):
#                print "Not found"
#                continue
#            database.start_transaction()
#            process(path, "barra")
#            database.commit()
    except Exception, e:
        print e
        database.rollback()
#    else:
#        database.commit()
