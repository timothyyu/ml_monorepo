import zipfile
import newdb
import util
import datafiles
import datetime
import os

########################
database = newdb.get_db()
##########################
__usToCsPriceTranslate = {"open":"PRCOD",
                    "close":"PRCCD",
                    "low":"PRCLD",
                    "high":"PRCHD",
                    "volume":"CSHTRD",
                    "adj":"AJEXDI",
                    "adrrc":"ADRRC",
                    "cond":"PRCSTD",
                    }
__csToUsPriceTranslate = {}
for k, v in __usToCsPriceTranslate.iteritems():
    __csToUsPriceTranslate[v] = k
##########################
__usToCsDividendTranslate = {"dividend":"DIV",
                    "casheq":"CHEQV",
                    }
__csToUsDividendTranslate = {}
for k, v in __usToCsDividendTranslate.iteritems():
    __csToUsDividendTranslate[v] = k
#############################
__usToCsSplitTranslate = {"rate":"SPLIT",
                    }
__csToUsSplitTranslate = {}
for k, v in __usToCsSplitTranslate.iteritems():
    __csToUsSplitTranslate[v] = k
###############################

def __getSplitLine(file):
    buffer = []
    while True:
        line = file.readline().strip()
        
        if line == "":
            break
        elif line[-1] == '\\':
            buffer.append(line[:-1])
            continue
        else:
            buffer.append(line)
            break
    
    if len(buffer) > 0:
        return "".join(buffer)
    else:
        return None
    
def __parseHeaderLine(line):
    tokens = line.split("|")
    table = tokens[2]
    numOfKeys = int(tokens[3])
    
    keys = tuple(tokens[4:4 + numOfKeys])
    attributes = tuple(tokens[4 + numOfKeys:])
    
    return (table, numOfKeys, keys, attributes)
    
def __parseDataLine(line, numOfKeys):
    tokens = line.split("|")
    command = tokens[0]
    keys = tuple(tokens[1:1 + numOfKeys])
    attributes = tuple(tokens[1 + numOfKeys:])
    
    return (command, keys, attributes)

#def __processSplits(keys,attributes):

def __datePlusOne(date, delta=datetime.timedelta(days=1)):
    return datetime.datetime.strptime(date, "%Y%m%d") + delta

__SHARES_UPDATE_THRESHOLD = 0.05
def __CSHOCEquals(previous, current):
    if previous == 0:
        if current == 0: return True
        else: return False
    else:
        return abs(current / previous) <= (1 + __SHARES_UPDATE_THRESHOLD) and abs(current / previous) >= (1 - __SHARES_UPDATE_THRESHOLD)

def __processSecurity(command, keys, attributes, timestamp, source, backfill, global_cs):
    secid = database.getSecidFromCsid(keys["GVKEY"], keys["IID"], timestamp)
        
    if secid is None:
        secid = database.createNewCsid(keys["GVKEY"], keys["IID"], timestamp)
        util.warning("Created new secid: {}.{}=>{}".format(keys['GVKEY'], keys['IID'], secid))
                
    for n, v in attributes.iteritems():
        if n in ("CUSIP", "ISIN", "SEDOL", "TIC"):
            if command in ("C", "I"):
                #database.insertTimelineRow(database.XREF_TABLE, {"secid":secid, "xref_type":database.getXrefType(n), "source":database.getSourceType(source)}, {"value":v}, timestamp)
                database.insertXref(secid, source, n, v, timestamp)
            elif command in ("D", "R"):
                #database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":secid, "xref_type":database.getXrefType(n), "source":database.getSourceType(source)}, timestamp)
                database.deleteXref(secid, source, n, timestamp)
        elif n in ("SECSTAT", "TPCI", "EXCNTRY", 'DSCI'):
            date = 0L
            if command in ("C", "I"):
                database.insertAttribute("sec", "s", secid, date, source, n, v, timestamp, None, backfill)
            elif command in ("D", "R"):
                database.deleteAttribute("sec", "s", secid, date, source, n, timestamp)
        elif n in ("EXCHG"):
            date = 0L
            if command in ("C", "I"):
                database.insertAttribute("sec", "n", secid, date, source, n, v, timestamp, None, backfill)
            elif command in ("D", "R"):
                database.deleteAttribute("sec", "n", secid, date, source, n, timestamp)
        elif n in ("DLDTEI"):
            date = 0L
            if command in ("C", "I"):
                database.insertAttribute("sec", "d", secid, date, source, n, util.convert_date_to_millis(v), timestamp, None, backfill)
            elif command in ("D", "R"):
                database.deleteAttribute("sec", "d", secid, date, source, n, timestamp)
          
def __processCSHOC(command, keys, attributes, timestamp, source, backfill, global_cs):
    if "CSHOC" not in attributes:
        return
    
    secid = database.getSecidFromCsid(keys["GVKEY"], keys["IID"], timestamp)
    
    if secid is None:
        secid = database.createNewCsid(keys["GVKEY"], keys["IID"], timestamp)
        util.warning("Created new secid: {}.{}=>{}".format(keys['GVKEY'], keys['IID'], secid))
    date = util.convert_date_to_millis(keys["DATADATE"])
    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    
    if command in ("I", "C"):
        database.insertAttribute("sec", "n", secid, date, source, "CSHOC", attributes["CSHOC"], timestamp, None, backfill, False, True, __CSHOCEquals)
    elif command in ("R", "D"):
        database.deleteAttribute("sec", "n", secid, date, source, "CSHOC", timestamp, False)
               
def __processPrice(command, keys, attributes, timestamp, source, backfill, global_cs):
    if global_cs and not keys["IID"].endswith("W"):
        return
    elif not global_cs and keys["IID"].endswith("W"):
        return
    
    secid = database.getSecidFromCsid(keys["GVKEY"], keys["IID"], timestamp)
    
    if secid is None:
        secid = database.createNewCsid(keys["GVKEY"], keys["IID"], timestamp) 
        util.warning("Created new secid: {}.{}=>{}".format(keys['GVKEY'], keys['IID'], secid))
    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    
    code = database.getAttributeType("PRICE", source, "n", database.PRICE_FULL_TABLE)
    updates = (0, 0)
    if command in ("I"):
        data = {"backfill":backfill, "currency":database.getCurrencyType(keys["CURCDD"])}
        #get the data that we track and translate them to our own names. make also sure that you get the attribute types right
        for k, v in __usToCsPriceTranslate.iteritems():
            value = attributes.get(v, None)
            if value is not None:
                data[k] = float(value)
            else:
                data[k] = value #i.e., None
        #finally do the insertion
        updates = database.insertTimelineRow(database.PRICE_FULL_TABLE, {"secid":secid, "date": int(keys["DATADATE"])}, data, timestamp)
    elif command in ("R"):
        updates = database.killOrDeleteTimelineRow(database.PRICE_FULL_TABLE, {"secid":secid, "date": int(keys["DATADATE"])}, timestamp)
    elif command in ("C", "D"):
        data = {"backfill":backfill, "currency":database.getCurrencyType(keys["CURCDD"])}
        for n, v in attributes.iteritems(): #for each attribute from the compustat line
            if n in __csToUsPriceTranslate: #if it is among the ones we track
                ourName = __csToUsPriceTranslate[n]
                if v is not None: #else
                    data[ourName] = float(v)
                else:
                    data[ourName] = None #i.e None
        updates = database.updateTimelineRow(database.PRICE_FULL_TABLE, {"secid":secid, "date": int(keys["DATADATE"])}, data, timestamp)
        
    database.updateAttributeStats(code, *updates)
        
def __processDividend(command, keys, attributes, timestamp, source, backfill, global_cs):
    if global_cs and not keys["IID"].endswith("W"):
        return
    elif not global_cs and keys["IID"].endswith("W"):
        return
    
    secid = database.getSecidFromCsid(keys["GVKEY"], keys["IID"], timestamp)

    if secid is None:
        secid = database.createNewCsid(keys["GVKEY"], keys["IID"], timestamp)
        util.warning("Created new secid: {}.{}=>{}".format(keys['GVKEY'], keys['IID'], secid))
    if backfill == 1:
        timestamp = min(timestamp, util.convert_date_to_millis(__datePlusOne(keys["DATADATE"])))

    code = database.getAttributeType("DIVIDEND", source, "n", database.DIVIDEND)
    updates = (0, 0)
    if command in ("I"):
        data = {"backfill":backfill, "currency":database.getCurrencyType(keys["CURCDDV"])}
        #get the data that we track and translate them to our own names. make also sure that you get the attribute types right
        for k, v in __usToCsDividendTranslate.iteritems():
            value = attributes.get(v, None)
            if value is not None:
                data[k] = float(value)
            else:
                data[k] = value #i.e., None
        #finally do the insertion
        updates = database.insertTimelineRow(database.DIVIDEND, {"secid":secid, "date": int(keys["DATADATE"])}, data, timestamp)
    elif command in ("R"):
        updates = database.killOrDeleteTimelineRow(database.DIVIDEND, {"secid":secid, "date": int(keys["DATADATE"])}, timestamp)
    elif command in ("C", "D"):
        data = {"backfill":backfill, "currency":database.getCurrencyType(keys["CURCDDV"])}
        for n, v in attributes.iteritems(): #for each attribute from the compustat line
            if n in __csToUsDividendTranslate: #if it is among the ones we track
                ourName = __csToUsDividendTranslate[n]
                if v is not None: #else
                    data[ourName] = float(v)
                else:
                    data[ourName] = None #i.e None
        updates = database.updateTimelineRow(database.DIVIDEND, {"secid":secid, "date": int(keys["DATADATE"])}, data, timestamp)
        
    database.updateAttributeStats(code, *updates)
                
def __processSplit(command, keys, attributes, timestamp, source, backfill, global_cs):
    if "SPLIT" not in attributes:
        return
    
    if global_cs and not keys["IID"].endswith("W"):
        return
    elif not global_cs and keys["IID"].endswith("W"):
        return
    
    secid = database.getSecidFromCsid(keys["GVKEY"], keys["IID"], timestamp)
    
    if secid is None:
        secid = database.createNewCsid(keys["GVKEY"], keys["IID"], timestamp)
        util.warning("Created new secid: {}.{}=>{}".format(keys['GVKEY'], keys['IID'], secid))
    if backfill:
        timestamp = min(timestamp, util.convert_date_to_millis(__datePlusOne(keys["DATADATE"])))

    code = database.getAttributeType("SPLIT", source, "n", database.SPLIT)
    updates = (0, 0)
    if command in ("I", "C"):
        updates = database.insertTimelineRow(database.SPLIT, {"secid":secid, "date": int(keys["DATADATE"])}, {"backfill":backfill, "rate":float(attributes["SPLIT"])}, timestamp)
    elif command in ("D", "R"):
        updates = database.killOrDeleteTimelineRow(database.SPLIT, {"secid":secid, "date": int(keys["DATADATE"])}, timestamp)
        
    database.updateAttributeStats(code, *updates)
    
def __processExchange(command, keys, attributes, timestamp, source, backfill, global_cs):
    if global_cs:
        return
    
    if backfill:
        timestamp = min(timestamp, util.convert_date_to_millis(__datePlusOne(keys["DATADATE"])))

    code = database.getAttributeType("EXRATE", source, "n", database.EXRATE)
    updates = (0, 0)
    if command in ("I", "C") and "EXRATD" in attributes:
        updates = database.insertTimelineRow(database.EXRATE, {"currency": database.getCurrencyType(keys["TOCURD"]), "date": int(keys["DATADATE"])}, {"backfill":backfill, "rate":float(attributes["EXRATD"])}, timestamp)
    elif command in ("D", "R"):
        updates = database.killOrDeleteTimelineRow(database.EXRATE, {"currency": database.getCurrencyType(keys["TOCURD"]), "date": int(keys["DATADATE"])}, timestamp)
        
    database.updateAttributeStats(code, *updates)

def __processCompany(command, keys, attributes, timestamp, source, backfill, global_cs):
    date = 0L
    coid = int(keys["GVKEY"])
    
    for n, v in attributes.iteritems():
        if n not in ('PRIUSA', 'PRICAN', 'PRIROW', 'COSTAT', 'SPCSRC', 'CONM', 'DLDTE', 'GSECTOR', 'GGROUP', 'GIND', 'GSUBIND', 'NAICS', 'SIC', 'SPCSECCD', 'SPCINDCD', 'FIC', 'FYRC', 'ACCTSTD', 'FYR', 'ISMOD', 'SRC', 'UPD'):
            continue
        if command in ("C", "I"):
            database.insertAttribute("co", "s", coid, date, source, n, v, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "s", coid, date, source, n, timestamp)
            
def __processIndustry(command, keys, attributes, timestamp, source, backfill, global_cs):
    if not global_cs and not (keys['POPSRC'] == "D" and keys["CONSOL"] == "C"):
        return
    elif global_cs and not (keys['POPSRC'] == "I" and keys["CONSOL"] == "C"):
        return
    
    date = util.convert_date_to_millis(keys["DATADATE"])
    if backfill: 
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])
                                
    for n, v in attributes.iteritems():
        if n not in ('NAICSH', 'SICH'):
            continue
        if command in ("C", "I"):
            database.insertAttribute("co", "s", coid, date, source, n, v, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "s", coid, date, source, n, timestamp)
            
def __processCredit(command, keys, attributes, timestamp, source, backfill):
    date = util.convert_date_to_millis(keys["DATADATE"])
    if backfill: 
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])
                                
    for n, v in attributes.iteritems():
        if n not in ('SPLTICRM', 'SPSTICRM', 'SPSDRM'):
            continue
        if command in ("C", "I"):
            database.insertAttribute("co", "s", coid, date, source, n, v, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "s", coid, date, source, n, timestamp)

def __processHgic(command, keys, attributes, timestamp, source, backfill, global_cs):
    if keys['INDTYPE'] != 'GICS':
        return

    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys['INDFROM']))

    date = -1L
    dateFrom = util.convert_date_to_millis(keys['INDFROM'])
    if "INDTHRU" in attributes and attributes["INDTHRU"] is not None:
        dateTo = util.convert_date_to_millis(__datePlusOne(attributes["INDTHRU"]))
    else:
        dateTo = None
    coid = int(keys["GVKEY"])
    
    #born = dateval #XXX why do we do this???
    for n, v in attributes.iteritems():
        if n not in ("GSUBIND", "GGROUP", "GIND", "GSECTOR"):
            continue
        if command in ("C", "I"):
            database.deleteAttribute("co", "s", coid, date, source, n, dateFrom, True)
            database.insertAttribute("co", "s", coid, date, source, n, v, dateFrom, dateTo, backfill, True)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "s", coid, date, source, n, dateFrom, True)
    
    coid = int(keys["GVKEY"])
    date = util.convert_date_to_millis(keys['INDFROM'])
    for n, v in attributes.iteritems():
        if n not in ("GSUBIND", "GGROUP", "GIND", "GSECTOR"):
            continue
        if command in ("C", "I"):
            database.insertAttribute("co", "s", coid, date, source, n + "H", v, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "s", coid, date, source, n + "H", timestamp)

def __processFundamental(command, keys, attributes, timestamp, source, backfill, global_cs):
    if not global_cs and not (keys['INDFMT'] == 'INDL' and keys['DATAFMT'] == "STD" and keys['POPSRC'] == "D" and keys["CONSOL"] == "C"):
        return
    elif global_cs and not (keys['INDFMT'] == 'INDL' and keys['DATAFMT'] == "HIST_STD" and keys['POPSRC'] == "I" and keys["CONSOL"] == "C"):
        return
    
    date = util.convert_date_to_millis(keys['DATADATE'])
    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])

    for n, v in attributes.iteritems():
        if n[-3:] == "_DC":
            continue
        if global_cs and n not in ("ATQ", "IBQ", "SALEQ", "OANCFY"):
            continue
        #value=float(v) if v is not None else None
        if command in ("C", "I"):
            database.insertAttribute("co", "n", coid, date, source, n, v, timestamp, None, backfill)
        elif command in ("D", "R"):
            database.deleteAttribute("co", "n", coid, date, source, n, timestamp)

def __processDesind(command, keys, attributes, timestamp, source, backfill, global_cs):
    if not global_cs and not (keys['INDFMT'] == 'INDL' and keys['DATAFMT'] == "STD" and keys['POPSRC'] == "D" and keys["CONSOL"] == "C"):
        return
    elif global_cs and not (keys['INDFMT'] == 'INDL' and keys['DATAFMT'] == "HIST_STD" and keys['POPSRC'] == "I" and keys["CONSOL"] == "C"):
        return

    date = util.convert_date_to_millis(keys['DATADATE'])
    if backfill == 1:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])
    
    for n, v in attributes.iteritems():
        if n in ('AJEXQ', 'AJPQ', 'AJEX', 'AJP', 'ADRRQ', 'CURRTRQ'):
            datatype = "n"
            value = float(v) if v is not None else None
        elif n in ('APDEDATEQ', 'FDATEQ', 'PDATEQ', 'RDQ', 'APDEDATE', 'FDATE', 'PDATE'):
            datatype = "d"
            value = util.convert_date_to_millis(v) if v is not None else None
        elif n in ('ACCTSTDQ', 'COMPSTQ', 'CURCDQ', 'CURNCDQ', 'DATACQTR', 'DATAFQTR', 'FQTR', 'FYEARQ', 'UPDQ', 'ACCTSTD', 'COMPST', 'CURCD', 'CURNCD', 'FYEAR', 'UPD'):
            datatype = "s"
            value = v
        else:
            continue
            
        if command in ("C", "I"):
            database.insertAttribute("co", datatype, coid, date, source, n, value, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", datatype, coid, date, source, n, timestamp)
        
def __processMkt(command, keys, attributes, timestamp, source, backfill, global_cs):
    if global_cs:
        return
    
    if keys['CFFLAG'] != 'F':
        return

    date = util.convert_date_to_millis(keys['DATADATE'])
    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])
    
    for n, v in attributes.iteritems():
        if n in ('MKVALT', 'PRCC', 'PRCH', 'PRCL', 'MKVALTQ', 'PRCCQ', 'PRCHQ', 'PRCLQ'):
            datatype = "n"
            value = float(v) if v is not None else None
        elif n in ('CLSM', 'CLSMQ'):
            datatype = "s"
            value = v
        else:
            continue
        
        if command in ("C", "I"):
            database.insertAttribute("co", datatype, coid, date, source, n, value, timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", datatype, coid, date, source, n, timestamp)

def __processFiledate(command, keys, attributes, timestamp, source, backfill, global_cs):
    if keys['SRCTYPE'] not in ('10Q', '10K'):
        return
    
    date = util.convert_date_to_millis(keys['DATADATE'])
    if backfill:
        timestamp = util.convert_date_to_millis(__datePlusOne(keys["DATADATE"]))
    coid = int(keys["GVKEY"])
        
    for n, v in attributes.iteritems():
        if n not in ("FILEDATE"):
            continue
        if command in ("C", "I"):
            database.insertAttribute("co", "d", coid, date, source, n, util.convert_date_to_millis(v), timestamp, None, backfill)
        elif command in ("R", "D"):
            database.deleteAttribute("co", "d", coid, date, source, n, timestamp)
            
def __consecutiveEqual(list, start, key):
    end = start
    while end < len(list) and key(list[start]) == key(list[end]):
        end = end + 1
    return start, end
  
def __optimize(file):
    organizer = {}
    table = None
    keyNames = None
    attributeNames = None
    numOfKeys = None
    
    while True:
        line = __getSplitLine(file)
        if line is None: break

        if line[0] in ("T", "F", "E"):
            continue
        elif line[0] in ("H"):
            (table, numOfKeys, keyNames, attributeNames) = __parseHeaderLine(line)
            continue
        elif line[0] in ("I,C,D,R"):
            d = (command, keyValues, attributeValues) = __parseDataLine(line, numOfKeys)
            t = (table, numOfKeys, keyNames, attributeNames)
            if t in organizer:
                lines = organizer[t]
            else:
                lines = []
                organizer[t] = lines
            lines.append(d)
            continue
        else:
            util.warning("Oh no! a K command on table {}: {}".format(table, line))
            continue
    
    allLines = []
    for header, datalines in organizer.iteritems():
        datalines.sort(key=lambda x: x[1])
        #remove some redundancies from datalines
        start = 0
        end = 0
        while start != len(datalines):
            (start, end) = __consecutiveEqual(datalines, start, lambda x:x[1])
            
            for i in xrange(start, end - 1, 1):                
                if datalines[i][0] == "D" and datalines[i + 1][0] == "R":
                    datalines[i] = ()
                elif (datalines[i][0] == "D" or datalines[i][0] == "C") and datalines[i + 1][0] == "C":
                    same = True
                    for x, y in zip(datalines[i][2], datalines[i + 1][2]):
                        if len(x) == 0 and len(y) == 0:
                            continue
                        elif len(x) > 0 and len(y) > 0:
                            continue
                        else:
                            same = False
                            break
                    if same:
                        datalines[i] = ()
                    else:
                        newdataline = []
                        for x, y in zip(datalines[i][2], datalines[i + 1][2]):
                            if len(y) > 0:
                                newdataline.append('')
                            else:
                                newdataline.append(x)
                        datalines[i] = (datalines[i][0], datalines[i][1], tuple(newdataline))
                                
            start = end
        
        allLines.append(header)
        allLines.extend(datalines)
        
    return allLines

def process(filepath, source):
    #if full
    if "full" in source or "load" in source:
        #timestamp=util.convert_date_to_millis("18000101");
        fileInfo = datafiles.read_info_file(filepath)
        timestamp = util.convert_date_to_millis(fileInfo['date_modified'])
        backfill = 1;
        database.setAttributeAutoCreate(True)
        optimize = False
    else:
        fileInfo = datafiles.read_info_file(filepath)
        if fileInfo["date_last_absent"] is None:
            timestamp = util.convert_date_to_millis(fileInfo['date_modified'])
            backfill = 0 
        else:
            timestamp = util.convert_date_to_millis(fileInfo['date_first_present'])
            backfill = 0
        database.setAttributeAutoCreate(False)
        optimize = True
        
    if "_g" in source:
        global_cs = True
    else:
        global_cs = False
        
    database.setAttributeAutoCreate(True)
    database.setCurrencyAutoCreate(True)
        
    #open the zipped file
    zf = zipfile.ZipFile(filepath)
    names = zf.namelist()
    assert len(names) == 1
    file = zf.open(names[0])
    
    #variables that persist through loop
    #presented here for clarity only
    table = None
    keyNames = None
    attributeNames = None
    numOfKeys = None
        
    if optimize:
        parsedLines = __optimize(file)
                
    #process lines
    counter = 0
    while True:
        if optimize:
            if len(parsedLines) == 0: break
            line = parsedLines.pop(0)
            
            if len(line) == 3:
                (command, keyValues, attributeValues) = line[0], line[1], line[2]
            elif len(line) == 4:
                (table, numOfKeys, keyNames, attributeNames) = line[0], line[1], line[2], line[3]
                continue
            else:
                continue
        else:
            line = __getSplitLine(file)
            if line is None: break

            if line[0] in ("T", "F", "E"):
                continue
            elif line[0] in ("H"):
                (table, numOfKeys, keyNames, attributeNames) = __parseHeaderLine(line)
                continue 
            elif line[0] in ("I,C,D,R"):
                (command, keyValues, attributeValues) = __parseDataLine(line, numOfKeys)
            else:
                util.warning("Oh no! a K command on table {}: {}".format(table, line))
                continue
            
        #progress
        counter = counter + 1
        if counter % 10000 == 0:
            util.info("{}: Processing line {}k".format(datetime.datetime.now(), counter / 1000))
            
        #remove keys that are replicated in attributes
        keys = {}
        keys.update(zip(keyNames, keyValues))
        attributes = {}
        
        if command in ("I", "C"):            
            for n, v in zip(attributeNames, attributeValues):
                if n not in keys and v != "": attributes[n] = v
        elif command in ("D"):
            for n, v in zip(attributeNames, attributeValues):
                if n not in keys and v == " ": attributes[n] = None
        elif command in ("R"):
            for n, v in zip(attributeNames, attributeValues):
                if n not in keys: attributes[n] = None 
            
        if table == "security":
            __processSecurity(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "sec_dprc":
            __processPrice(command, keys, attributes, timestamp, source, backfill, global_cs)
            __processCSHOC(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "company":
            __processCompany(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "sec_divid":
            __processDividend(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "sec_split":
            __processSplit(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "co_industry":
            __processIndustry(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "co_hgic":
            __processHgic(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table in ("co_afnd1", "co_afnd2", "co_ifndq", "co_ifndsa", "co_ifndytd"):
            __processFundamental(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table in ("co_idesind", 'co_adesind'):
            __processDesind(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table in ("co_amkt", 'co_imkt'):
            __processMkt(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "co_filedate":
            __processFiledate(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "adsprate":
            __processCredit(command, keys, attributes, timestamp, source, backfill, global_cs)
        elif table == "exrt_dly":
            __processExchange(command, keys, attributes, timestamp, source, backfill, global_cs)
        else:
            continue
        
    #__processBufferedFundamentals(source, backfill, buffer)
    file.close()
    zf.close()

if __name__ == "__main__":
    try:
        newdb.init_db(os.environ["DB_CONFIG_FILE"])
        database = newdb.get_db()
        database.setAttributeAutoCreate("true")
        database.start_transaction()
        #process("/apps/ase/data/compustat/full/2008/09/20/co_hgic/200809_f_co_hgic.1.asc.zip.80a056dd","compustat_full")
        files = database.getProcessedFilesTimeOrdered("compustat")
        procFiles = set()
        for row in database.execute("SELECT * from tmp_files").fetchall():
            procFiles.add(row["path"])
        
        for file in files:
            if file in procFiles:
                continue        
            
            filepath = "/apps/ase/data/compustat/compustat/" + file
            if not os.path.exists(filepath):
                util.info("skipping file " + filepath)
                continue
                
            util.info("Processing file " + filepath)
            process(filepath, "compustat")
            database.execute("INSERT INTO tmp_files VALUES('{}')".format(file))
        
        #process("/apps/ase/data/compustat/full/2008/09/20/exrt_dly/200809_f_exrt_dly.1.asc.zip.a9fe2e8b","compustat_full")
        #database.addProcessedFiles("compustat", "20080920/exrt_dly/200809_f_exrt_dly.1.asc.zip.a9fe2e8b")
        #print 'ey, ok'
        #database.commit()
        #database.rollback()
        database.commit()
    except Exception, e:
        print e
        database.rollback()
        raise
