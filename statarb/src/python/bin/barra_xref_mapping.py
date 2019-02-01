#!/usr/bin/env python
import os
import newdb
import util
import warnings
import time
import sys
import argparse
import re

database = newdb.get_db()

NONE = 999999999999999

def __toNumericalNone(died):
    if died is None:
        return NONE
    else:
        return died
    
def __toDBNone(died):
    if died == NONE:
        return None
    else:
        return died

def __getSecidRange(rangeStart, data):
    if rangeStart >= len(data):
        return len(data), len(data)
    
    end = rangeStart + 1;
    while end < len(data) and data[end]["secid"] == data[rangeStart]["secid"]:
        end += 1
    return rangeStart, end

def __getSecidBornRange(rangeStart, rangeEnd, data):
    if rangeStart >= len(data):
        return len(data), len(data)
    
    end = rangeStart + 1;
    while end < len(data) and end < rangeEnd and data[end]["secid"] == data[rangeStart]["secid"] and data[end]["cs_born"] == data[rangeStart]["cs_born"]:
        end += 1
    return rangeStart, end

#def __getUni():
#    olduni=set()
#    uni=set()
#    oldSystemUniFile=os.environ["ROOT_DIR"]+"/run/"+os.environ["STRAT"]+"/uni.txt"
#    oldSystemTranslationFile=os.environ["ROOT_DIR"]+"/run/"+os.environ["STRAT"]+"/old.secids.txt"
#    
#    with open(oldSystemUniFile,"r") as file:
#        for line in file:
#            tokens=line.strip().split("|")
#            olduni.add((int(tokens[0]),int(tokens[1])))
#    
#    with open(oldSystemTranslationFile,"r") as file:
#        for line in file:
#            tokens=line.strip().split("|")
#            oldid=(int(tokens[0]),int(tokens[1]))
#            if oldid in olduni:
#                uni.add(int(tokens[2]))
#                
#    return uni


#def __getUni():
#    uni=set()
#    uniFile=os.environ["ROOT_DIR"]+"/run/"+os.environ["STRAT"]+"/uni.20100901.txt"
#    
#    with open(uniFile,"r") as file:
#        for line in file:
#            tokens=line.strip().split("|")
#            uni.add(int(tokens[0]))
#                    
#    return uni

#get the most recent tickers.txt file
def __getUni():
    uni=set()
    dir = os.path.join(os.environ["ROOT_DIR"], "run", os.environ["STRAT"])
    for datedir in sorted(os.listdir(dir), reverse = True):
        if (not os.path.isdir(dir + "/" + datedir)) or (not re.match(r"\d{8}", datedir)): continue
        tickersFile = os.path.join(dir, datedir, "tickers.txt")
        if not os.path.isfile(tickersFile): continue
        with open(tickersFile, "r") as file:
            for line in file:
                tokens = line.strip().split("|")
                secid = tokens[1]
                alive = tokens[8]
                if alive == "A": uni.add(int(secid))
        break
    return uni

def __reconcile(barrainfo, aggressiveness):
    #filter so that countries match. we have filtered us secids, so this is not an issue here
    f1 = barrainfo
    
    #sort by born to detect overlaps
    f1.sort(key=lambda x : x["b_born"])
    overlaps = []
    for i in xrange(len(f1)):
        for j in xrange(i + 1, len(f1)):
            died1 = __toNumericalNone(f1[i]["b_died"])#f1[i]["r_died"] if f1[i]["r_died"] is not None else 999999999999999L
            born2 = f1[j]["b_born"]
            if (died1 > born2): overlaps.append((i, j))
    
    #remove overlaps completely
    #in the future we might want to dig deeper, etc, look at which overlapping rkd issue was active, or traded in a non-OTC exchange
    ol = set()
    for i, j in overlaps:
        ol.add(i)
        ol.add(j)
    f2 = [x for i, x in enumerate(f1) if i not in ol]

    res = []
    if len(f2) == 0:
        pass
    elif len(f2) == 1:
        if aggressiveness == 0:
            row = f2[0]
            born = max(row["cs_born"], row["b_born"])
            died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
            res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
        elif aggressiveness == 1:
            row = f2[0]
            born = row["cs_born"] #we should never go before cs_born?
            died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
            res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
    else:            
        if aggressiveness == 0:
            for row in f2:
                born = max(row["cs_born"], row["b_born"])
                died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
                res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
        elif aggressiveness == 1:
            for i in xrange(len(f2)):
                if i == 0:
                    row = f2[i]
                    born = row["cs_born"] #we should never go before cs_born?
                    died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
                    res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
                elif i == (len(f2) - 1):
                    row1 = f2[i - 1]
                    row = f2[i]
                    born = min(row1["b_died"], row["b_born"])
                    died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
                    res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
                else:
                    row1 = f2[i - 1]
                    row = f2[i]
                    born = min(row1["b_died"], row["b_born"])
                    died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["b_died"]))
                    res.append((row["secid"], row["barraid"], born, __toDBNone(died)))
        
    return res
    
def __mergeConsecutive(goodMappings):
    evenBetterMappings = []
    
    rangeStart = 0;
    start = 0;
    end = 1;
    
    while rangeStart < len(goodMappings):
        while end < len(goodMappings) and goodMappings[start][0] == goodMappings[end][0] and goodMappings[start][1] == goodMappings[end][1] and goodMappings[start][3] == goodMappings[end][2]:
            start += 1
            end += 1
        
        evenBetterMappings.append((goodMappings[rangeStart][0], goodMappings[rangeStart][1], goodMappings[rangeStart][2], goodMappings[end - 1][3]))
        rangeStart = end
        start = end
        end = start + 1
        
    return evenBetterMappings
    
def getManualMappings():
    mappings=[]
    filepath=os.environ["ROOT_DIR"]+"/run/"+os.environ["STRAT"]+"/mapping.overrides.txt"
    if not os.path.isfile(filepath):
        util.error("Failed to locate mapping overrides file")
        return mappings
    with open(filepath,"r") as file:
        #skip header
        file.readline()
        for line in file:
            tokens=line.strip().split("|")
            if len(tokens)!=6:
                continue
            if tokens[0]!="barra":
                continue
            mappings.append((int(tokens[1]),tokens[2],long(tokens[3]),long(tokens[4]) if tokens[4]!="None" else None))
    return mappings

def cs2barraMappings(aggressiveness):
    #get tuples secid,cs_country,cs_born,cs_died,rkd,rkd_id,r_born,r_died,r_country so that the corresponding ranges [born,died) ranges of the two data sources overlap
    query = "SELECT xref.secid AS secid,xref.born AS cs_born,xref.died AS cs_died,barra_xref.barraid AS barraid,barra_xref.born AS b_born,barra_xref.died AS b_died FROM xref,barra_xref,stock WHERE stock.country=1 AND stock.secid=xref.secid AND xref.xref_type=1 AND xref.source=2 AND barra_xref.xref_type=1 AND barra_xref.value=xref.value AND barra_xref.born<IFNULL(xref.died,999999999999999) AND IFNULL(barra_xref.died,999999999999999)>xref.born ORDER BY stock.secid,xref.born"
    rows = database.execute(query).fetchall()
    data = list(rows)
    goodData = []

    secidStart = 0;
    secidEnd = None;
    secidBornStart = 0;
    secidBornEnd = None;

    #loop for processing a secid
    while secidStart < len(data):
        dummy, secidEnd = __getSecidRange(secidStart, data)
        
        #loop for processing a secid interval
        while secidBornStart < secidEnd:
            dummy, secidBornEnd = __getSecidBornRange(secidBornStart, secidEnd, data)

            #get tuples rkd,issue,r_born,r_died,r_country
            #overlapping with a single secid,cs_born,cs_died interval
            goodRows = __reconcile(data[secidBornStart:secidBornEnd], aggressiveness)
            goodData.extend(goodRows)
            
            secidBornStart = secidBornEnd;
        
        secidStart = secidEnd;
    
    return goodData

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DB utils')
    
    parser.add_argument("--aggressiveness", action="store", dest="aggressiveness", default="1")
    parser.add_argument("--email", action="store_true", dest="email", default=False)
    parser.add_argument("--database", action="store", dest="db", default="pri")
    args = parser.parse_args()
    
    util.set_log_file()
    
    if args.db == "pri":
        newdb.init_db()
        database = newdb.get_db()
    elif args.db == "sec":
        newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
        database = newdb.get_db()
    else:
        util.error("Valid database choices are [pri|sec]")
        sys.exit(1)
        
    warnings.simplefilter("ignore")
    newdb.init_db()
    database = newdb.get_db()
    
    locked = False
    try:
        startTime = time.time() #in seconds since epoch
        while not locked:
            if time.time() - startTime > 30 * 60: #have been polling for 30mins
                util.error("xref_mapping unable to establish lock after {} mins. Aborting".format(1.0 * (time.time() - startTime) / 60.0))
                sys.exit(1)
            time.sleep(1) #poll every 1 second
            locked = database.getProcessedFilesLock()
            
        util.debug("Lock established")
        
        database.start_transaction()
        
        #first take existing data for comparison purposes:
        existingMappings=set()
        for row in database.execute("SELECT * FROM cs2barra").fetchall():
            existingMappings.add((row["secid"],row["barraid"],row["born"],row["died"]))
            
        #get new mappings
        newMappings=set()
        aggressiveness=int(args.aggressiveness)
        for mapping in __mergeConsecutive(cs2barraMappings(aggressiveness)):
            newMappings.add(mapping)  
        
        #manual overrides
        #remove secids with manual overrides
        manualMappings=getManualMappings()
        badSecids=set([x[0] for x in manualMappings])
        newMappings=[x for x in newMappings if x[0] not in badSecids]
        newMappings.extend(manualMappings)
        newMappings=set(newMappings)
        
        #insert them
        ts = util.now()
        database.execute("DELETE FROM cs2barra")
        for mapping in newMappings:                
            database.insertRow("cs2barra", {"secid":mapping[0]}, {"barraid":mapping[1]}, mapping[2], mapping[3])
            database.insertRow("cs2barra_bkup", {"ts" : ts,  "secid":mapping[0]}, {"barraid":mapping[1]}, mapping[2], mapping[3])
        
        #email the changes
        combined=set()
        for xx in newMappings-existingMappings:
            combined.add((xx[0],xx[1],xx[2],xx[3],1))
        for xx in existingMappings-newMappings:
            combined.add((xx[0],xx[1],xx[2],xx[3],-1))
                
        uni=__getUni()
        report=["operation, secid, ticker, barraid, from, to "]
        for xx in sorted(combined,key=lambda xx :(xx[0],xx[4],xx[2])):
            secid = int(xx[0])
            highlight = "***" if int(xx[0]) in uni else ""
            operation = "D" if xx[4]<0 else "I"
            ticker = database.getXrefFromSecid("TIC", secid)
            barraid = xx[1]
            fromDate = util.convert_millis_to_datetime(long(xx[2])).strftime("%Y%m%d")
            toDate = util.convert_millis_to_datetime(long(xx[3])).strftime("%Y%m%d") if xx[3] is not None else None
            
            report.append("{} {}, {}, {}, {}, {}, {}".format(highlight, operation, secid, ticker, barraid, fromDate, toDate))
        
        #as a bonus, see which universe securities are unmapped
        for xx in newMappings:
            secid=int(xx[0])
            died=xx[3]
            if (died is None or died>util.now()) and secid in uni:
                uni.remove(secid)
        
        if len(uni)>0:
            report.append('')
            report.append("Orphan secids")
            for secid in uni:
                report.append(str(secid) + " " + database.getXrefFromSecid("TIC", secid, util.now(), "compustat_idhist"))
        
        if args.email and (len(report)>0):
            util.email("Compustat to Barra mapping changes", "\n".join(report))
    except:
        database.rollback()
        raise
    else:
        database.commit()
    finally:
        if locked: database.releaseProcessedFilesLock()
