import util
import datafiles
from collections import Counter
import tempfile
import os
import shutil
import newdb
import newdb.xrefsolve


database = newdb.get_db()

def __processHistoricalPush(filepath, source):
    
    date = None
    data = []
    with open(filepath, "r") as file:
        file.readline()
        for line in file:
            tokens = line.strip().split(",")
            lineDate = tokens[0];
            cusip = tokens[1]
            size = tokens[3]
            rate = tokens[4]
            type = "R"
            
            if date is not None and lineDate != date:
                __createAndProcessDummyFiles(date, data)
                data = []
                            
            data.append((lineDate, cusip, size, rate, type))
            date = lineDate
            
    __createAndProcessDummyFiles(date, data)
                
def __createAndProcessDummyFiles(date, data):
        if date >= "20100106":
            return
        else:
            print "Processing day "+date
        ass = [x[0] for x in data]
        ass = sorted(ass)
        assert ass[0] == ass[-1] and ass[0] == date
    
        tmpfilepath = os.environ["TMP_DIR"] + "/availabilitypush_{}.txt.xxxxxxxx".format(date)
        tmpinfofilepath = os.environ["TMP_DIR"] + "/availabilitypush_{}.txt.xxxxxxxx.info".format(date)
        
        with open(tmpfilepath, "w") as tmpfile:
            for d in data:
                tmpfile.write(",".join(d) + "\n")
        
        with open(tmpinfofilepath, "w") as tmpinfofile:
            for i in xrange(5):
                tmpinfofile.write("\n")

        __processPush(tmpfilepath, "morgan_htb")

        os.unlink(tmpfilepath);
        os.unlink(tmpinfofilepath)

def __processPush(filepath, source):
    #get the date the data are about
    date = util.convert_date_to_millis(filepath[-21:-13])
    
    fileInfo = datafiles.read_info_file(filepath)
    if fileInfo["date_last_absent"] is None:
        backfill = 1
        timestamp = date
    else:
        backfill = 0
        timestamp = util.convert_date_to_millis(fileInfo["date_first_present"])

    file = open(filepath, "r")
    
    #make a first pass and collect the data
    data = []
    counter = Counter()
    for line in file:
        tokens = line.strip().split(",")
        type = tokens[4]
        
        if type != 'R':
            util.error("Strange line in availability push file "+line)
            continue
        
        cusip = tokens[1]
        quantity = float(tokens[2])
        rate = float(tokens[3])
                        
        data.append((cusip, quantity, rate))
        counter[rate] += 1
                        
    #get the mode (most frequent) of the rates
    rateModes = counter.most_common(2)
    #assert that the most frequent rate lies at the left of the second most frequent, i.e., the mode corresponds to the "base" borrow rate
    assert rateModes[0][0] > rateModes[1][0]
    rateMode = rateModes[0][0]
    
    #insert the data
    failure = 0
    for datum in data:
        cusip = datum[0]
        quantity = datum[1]
        rateDiff = datum[2] - rateMode
        
        secid = database.getSecidFromXref("CUSIP", cusip, timestamp, "compustat_idhist", newdb.xrefsolve.preferUS)
        if secid is None:
            failure += 1
            util.warning("Failed to map CUSIP {}. Failure #{}".format(cusip, failure))
            continue
        
        if rateDiff > 0:
            util.error("Positive rate for {}: Rate={}, Mode={}, Diff={}".format(cusip, datum[2], rateMode, rateDiff))
        elif rateDiff == 0:
            pass
        else:
            database.insertAttribute("sec", "n", secid, date, source, "BORROW_RATE_PUSHED", rateDiff, timestamp, None, backfill, False, False, util.dict_fields_eq_num_stable)
        
        database.insertAttribute("sec", "n", secid, date, source, "BORROW_AVAILABILITY", quantity, timestamp, None, backfill, False, False, util.dict_fields_eq_num_stable)

    file.close()
    
def __processRequest(filepath, source):
    #get the date the data are about
    date = util.convert_date_to_millis(filepath[-21:-13])
    
    fileInfo = datafiles.read_info_file(filepath)
    if fileInfo["date_last_absent"] is None:
        backfill = 1
        timestamp = date
    else:
        backfill = 0
        timestamp = util.convert_date_to_millis(fileInfo["date_first_present"])

    file = open(filepath, "r")
    
    #make a first pass and collect the data
    data = []
    counter = Counter()
    for line in file:
        tokens = line.strip().split(",")
        ticker = tokens[0]
        requested = float(tokens[2])
        allocated = float(tokens[3])
        #notes=tokens[4]
        if len(tokens) > 5:
            rate = float(tokens[5])
            type = tokens[6]
        else:
            rate = None
            type = None
                     
        assert type is None or type == "R"   
        data.append((ticker, requested, allocated, rate))
        counter[rate] += 1
                        
    #get the mode (most frequent) of the rates
    rateModes = counter.most_common(2)
    #assert that the most frequent rate lies at the left of the second most frequent, i.e., the mode corresponds to the "base" borrow rate
    assert rateModes[0][0] > rateModes[1][0]
    rateMode = rateModes[0][0]
    
    #insert the data
    failure = 0
    for datum in data:
        ticker = datum[0]
        requested = datum[1]
        allocated = datum[2]
        rateDiff = datum[3] - rateMode if datum[3] is not None else None
                
        secid = database.getSecidFromXref("TIC", ticker, timestamp, "compustat_idhist", newdb.xrefsolve.preferUS)
        if secid is None:
            failure += 1
            util.warning("Failed to map TICKER {}. Failure #{}".format(ticker, failure))
            continue
        
        if rateDiff > 0:
            util.error("Positive rate for {}: Rate={}, Mode={}, Diff={}".format(ticker, datum[2], rateMode, rateDiff))
        elif rateDiff == 0:
            pass
        else:
            database.insertAttribute("sec", "n", secid, date, source, "BORROW_RATE", rateDiff, timestamp, None, backfill, False, False, util.dict_fields_eq_num_stable)
            
        database.insertAttribute("sec", "n", secid, date, source, "BORROW_REQUESTED", requested, timestamp, None, backfill, False, False, util.dict_fields_eq_num_stable)
        database.insertAttribute("sec", "n", secid, date, source, "BORROW_ALLOCATED", allocated, timestamp, None, backfill, False, False, util.dict_fields_eq_num_stable)
    
    file.close()

def process(filepath, source):
    database.setAttributeAutoCreate(True)
    #get the type of file
    if "push" in filepath:
        __processPush(filepath, source)
    elif "response" in filepath:
        __processRequest(filepath, source)
    else:
        util.error("Invalid file type")
        raise Exception

if __name__ == "__main__":
    newdb.init_db()
    database=newdb.get_db()
    
    try:
        database.start_transaction()
        __processHistoricalPush("/apps/ase/data/morgan/htb/20070101-20110428.csv", "morgan_htb")
        #process("/apps/logs/ase/data/morgan/htb/20101231/availabilitypush_20101231.txt.18ac5a4d","morgan_htb")
        #process("/apps/logs/ase/data/morgan/htb/20100906/availabilitypush_20100906.txt.d766b863","morgan_htb")
        #process("/apps/logs/ase/data/morgan/htb/20100329/availabilitypush_20100329.txt.07fe9e2a","morgan_htb")
        #process("/apps/logs/ase/data/morgan/htb/20101231/locate_auto_response_20101231.txt.5fec201f","morgan_htb")
    except Exception,e:
        print e
        database.rollback()
    else:
        database.commit()
