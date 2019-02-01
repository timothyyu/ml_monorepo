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
#    olduni = set()
#    uni = set()
#    oldSystemUniFile = os.environ["ROOT_DIR"] + "/run/" + os.environ["STRAT"] + "/uni.txt"
#    oldSystemTranslationFile = os.environ["ROOT_DIR"] + "/run/" + os.environ["STRAT"] + "/old.secids.txt"
#    
#    with open(oldSystemUniFile, "r") as file:
#        for line in file:
#            tokens = line.strip().split("|")
#            olduni.add((int(tokens[0]), int(tokens[1])))
#    
#    with open(oldSystemTranslationFile, "r") as file:
#        for line in file:
#            tokens = line.strip().split("|")
#            oldid = (int(tokens[0]), int(tokens[1]))
#            if oldid in olduni:
#                uni.add(int(tokens[2]))
#                
#    return uni

#def __getUni():
#    uni = set()
#    uniFile = os.environ["ROOT_DIR"] + "/run/" + os.environ["STRAT"] + "/uni.20100901.txt"
#    
#    with open(uniFile, "r") as file:
#        for line in file:
#            tokens = line.strip().split("|")
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

def __mergeConsecutive(goodMappings):
    evenBetterMappings = []
    
    rangeStart = 0;
    start = 0;
    end = 1;
    
    while rangeStart < len(goodMappings):
        while end < len(goodMappings) and goodMappings[start][0] == goodMappings[end][0] and goodMappings[start][1] == goodMappings[end][1] and goodMappings[start][2] == goodMappings[end][2] and goodMappings[start][4] <= goodMappings[end][3]:
            start += 1
            end += 1
        
        evenBetterMappings.append((goodMappings[rangeStart][0], goodMappings[rangeStart][1], goodMappings[rangeStart][2], goodMappings[rangeStart][3], goodMappings[end - 1][4]))
        rangeStart = end
        start = end
        end = start + 1
        
    return evenBetterMappings

def __xrefAt(xrefHist, xref, born):
    for ii, entry in enumerate(xrefHist):
        if entry[0] == xref and entry[1] == born:
            return ii

def __reconcile(rkdinfo, rkdXrefHistory, aggressiveness):
    #filter so that countries match
    f1 = [x for x in rkdinfo if (x["cs_country"] == 1 and x["r_country"] == 'USA') or (x["cs_country"] == 2 and x["r_country"] == 'CAN')]
    
    #sort by born to detect overlaps
    f1.sort(key=lambda x : x["r_born"])
    overlaps = []
    for i in xrange(len(f1)):
        for j in xrange(i + 1, len(f1)):
            died1 = __toNumericalNone(f1[i]["r_died"])
            born2 = f1[j]["r_born"]
            if (died1 > born2): overlaps.append((i, j))
    
    #remove overlaps completely
    #in the future we might want to dig deeper, etc, look at which overlapping rkd issue was active, or traded in a non-OTC exchange
    ol = set()
    for i, j in overlaps:
        if f1[i]["r_active"] > f1[j]["r_active"]:
            ol.add(j)
        elif f1[j]["r_active"] > f1[i]["r_active"]:
            ol.add(i)
        else:
            ol.add(i)
            ol.add(j)
    f2 = [x for i, x in enumerate(f1) if i not in ol]
    #f2=f1
    
#    if len(f2)>1:
#        print secid,cs_country,cs_born,cs_died
#        for x in f1:
#            print x["rkd"],x["rkd_id"],x["r_born"],x["r_died"],x["r_country"]
#        print " "

    res = []
    if len(f2) == 0:
        pass
    elif len(f2) == 1:
        if aggressiveness == 0:
            row = f2[0]
            born = max(row["cs_born"], row["r_born"])
            died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))
            res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
        elif aggressiveness == 1:
            row = f2[0]
            #get the xref history of the matching reuters id
            hist = rkdXrefHistory[(row["rkd"], row["rkd_id"])]
            pos = __xrefAt(hist, row["xref"], row["r_born"])
            #see if we can extend reuters born to match compustat born.
            #born = row["cs_born"] if pos == 0 else max(row["cs_born"], row["r_born"])
            born = row["cs_born"]            
            #see if we can extend reuters died to match compustat died
            died = __toNumericalNone(row["cs_died"]) if pos == len(hist) - 1 else min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))

            res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
    else:            
        if aggressiveness == 0:
            for row in f2:
                born = max(row["cs_born"], row["r_born"])
                died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))
                res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
        elif aggressiveness == 1:
            for i in xrange(len(f2)):
                if i == 0:
                    row = f2[i]
                    #get the xref history of the matching reuters id
#                    hist = rkdXrefHistory[(row["rkd"], row["rkd_id"])]
#                    pos = __xrefAt(hist, row["xref"], row["r_born"])
#                    #see if we can extend reuters born to match compustat born.
#                    born = row["cs_born"] if pos == 0 else max(row["cs_born"], row["r_born"])
                    born = row["cs_born"]
                    died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))
                    res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
                elif i == (len(f2) - 1):
                    row1 = f2[i - 1]
                    row = f2[i]
                    born = min(row1["r_died"], row["r_born"])
                    #get the xref history of the matching reuters id
                    hist = rkdXrefHistory[(row["rkd"], row["rkd_id"])]
                    pos = __xrefAt(hist, row["xref"], row["r_born"])       
                    #see if we can extend reuters died to match compustat died
                    died = __toNumericalNone(row["cs_died"]) if pos == len(hist) - 1 else min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))
                    res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
                else:
                    row1 = f2[i - 1]
                    row = f2[i]
                    born = min(row1["r_died"], row["r_born"])
                    died = min(__toNumericalNone(row["cs_died"]), __toNumericalNone(row["r_died"]))
                    res.append((row["secid"], row["rkd"], row["rkd_id"], born, __toDBNone(died)))
        
    return res
    
def cs2reutersMappings(aggressiveness):
    #get the cusip timeline of reuters xrefs
    query1 = "SELECT * FROM reuters_xref WHERE xref_type=1 ORDER BY rkd,issueid,born"
    rows = database.execute(query1).fetchall()
    rkdXrefHist = {}
    for row in rows:
        id = (row["rkd"], row["issueid"])
        history = rkdXrefHist.get(id, None)
        if history is None:
            history = []
            rkdXrefHist[id] = history
        entry = (row["value"], row["born"], row["died"])
        history.append(entry)
        
    #get tuples secid,cs_country,cs_born,cs_died,rkd,rkd_id,r_born,r_died,r_country so that the corresponding ranges [born,died) ranges of the two data sources overlap
    query2 = [None] * 6
    query2[0] = "SELECT distinct xref.value as xref,stock.secid AS secid,stock.country AS cs_country,xref.born AS cs_born,xref.died AS cs_died,reuters_xref.rkd AS rkd,reuters_xref.issueid AS rkd_id,reuters_xref.born AS r_born,reuters_xref.died AS r_died, r1.value AS r_country,r2.value AS r_active"   
    query2[1] = "FROM xref,reuters_xref,stock,reuters_s as r1,reuters_n as r2" 
    query2[2] = "WHERE (stock.country=1 OR stock.country=2) AND stock.secid=xref.secid AND xref.source=2 AND xref.xref_type=1 AND reuters_xref.xref_type=1 AND reuters_xref.value=xref.value AND reuters_xref.born<IFNULL(xref.died,999999999999999) AND IFNULL(reuters_xref.died,999999999999999)>xref.born" 
    query2[3] = "AND reuters_xref.rkd=r1.rkd AND reuters_xref.issueid=r1.issueid AND r1.type=2415" #country
    query2[4] = "AND reuters_xref.rkd=r2.rkd AND reuters_xref.issueid=r2.issueid AND r2.type=2412 AND r2.died IS NULL" #issue currentrly active
    query2[5] = "ORDER BY stock.secid,xref.born"
    rows = database.execute(" ".join(query2)).fetchall()
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
            goodRows = __reconcile(data[secidBornStart:secidBornEnd], rkdXrefHist, aggressiveness)
            goodData.extend(goodRows)
            
            secidBornStart = secidBornEnd;
        
        secidStart = secidEnd;
        
    return goodData

def getManualMappings():
    mappings = []
    filepath = os.environ["ROOT_DIR"] + "/run/" + os.environ["STRAT"] + "/mapping.overrides.txt"
    if not os.path.isfile(filepath):
        util.error("Failed to locate mapping overrides file")
        return mappings
    with open(filepath, "r") as file:
        #skip header
        file.readline()
        for line in file:
            tokens = line.strip().split("|")
            if len(tokens) != 6:
                continue
            if tokens[0] != "reuters":
                continue
            id = tokens[2].split(".")
            mappings.append((int(tokens[1]), int(id[0]), int(id[1]), long(tokens[3]), long(tokens[4]) if tokens[4] != "None" else None))
    return mappings

def generateCs2Rics():
    query = "INSERT INTO cs2rics SELECT cs2r.secid, rx.value, GREATEST(cs2r.born, rx.born), NULLIF(LEAST(IFNULL(cs2r.died,{NONE}), IFNULL(rx.died, {NONE})), {NONE}) \
    FROM cs2reuters as cs2r JOIN reuters_xref as rx ON (cs2r.rkd = rx.rkd AND cs2r.issueid = rx.issueid AND rx.xref_type=7) \
    WHERE rx.born < IFNULL(cs2r.died, {NONE}) AND IFNULL(rx.died, {NONE}) > cs2r.born \
    ORDER BY cs2r.secid".format(NONE=NONE)
    
    database.execute("DELETE FROM cs2rics")
    database.execute(query);

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DB utils')
    
    parser.add_argument("--aggressiveness", action="store", dest="aggressiveness", default="1")
    parser.add_argument("--database", action="store", dest="db", default="pri")
    parser.add_argument("--email", action="store_true", dest="email", default=False)
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
        existingMappings = set()
        for row in database.execute("SELECT * FROM cs2reuters").fetchall():
            existingMappings.add((row["secid"], row["rkd"], row["issueid"], row["born"], row["died"]))
        
        #get new mappings
        newMappings = set()
        aggressiveness = int(args.aggressiveness)
        for mapping in __mergeConsecutive(cs2reutersMappings(aggressiveness)):
            newMappings.add(mapping)           
        
        #manual overrides
        #remove secids with manual overrides
        manualMappings = getManualMappings()
        badSecids = set([x[0] for x in manualMappings])
        newMappings = [x for x in newMappings if x[0] not in badSecids]
        newMappings.extend(manualMappings)
        newMappings = set(newMappings)
        
        #insert them
        ts = util.now()
        database.execute("DELETE FROM cs2reuters")
        for mapping in sorted(newMappings, key=lambda x : (x[0], x[3])):
            database.insertRow("cs2reuters", {"secid":mapping[0]}, {"rkd":mapping[1], "issueid":mapping[2]}, mapping[3], mapping[4])
            database.insertRow("cs2reuters_bkup", {"ts": ts, "secid":mapping[0]}, {"rkd":mapping[1], "issueid":mapping[2]}, mapping[3], mapping[4])
        
        #further generate cs2rics mapping
        generateCs2Rics()
        
        #email the changes
        combined = set()
        for xx in newMappings - existingMappings:
            combined.add((xx[0], xx[1], xx[2], xx[3], xx[4], 1))
        for xx in existingMappings - newMappings:
            combined.add((xx[0], xx[1], xx[2], xx[3], xx[4], -1))
              
        uni = __getUni()              
        report = ["operation, secid, ticker, rkd_id, issue_id, from, to "]
        for xx in sorted(combined, key=lambda xx :(xx[0], xx[4], xx[2])):
            secid = int(xx[0])
            highlight = "***" if int(xx[0]) in uni else ""
            operation = "D" if xx[5] < 0 else "I"
            ticker = database.getXrefFromSecid("TIC", secid)
            rkd_id = xx[1]
            issue_id = xx[2]
            fromDate = util.convert_millis_to_datetime(long(xx[3])).strftime("%Y%m%d")
            toDate = util.convert_millis_to_datetime(long(xx[4])).strftime("%Y%m%d") if xx[4] is not None else None
            
            report.append("{} {}, {}, {}, {}.{}, {}, {}".format(highlight, operation, secid, ticker, rkd_id, issue_id, fromDate, toDate))
        
                #as a bonus, see which universe securities are unmapped
        for xx in newMappings:
            secid = int(xx[0])
            died = xx[4]

            if (died is None or died > util.now()) and secid in uni:
                uni.remove(secid)
        
        if len(uni) > 0:
            report.append('')
            report.append("Orphan secids")
            for secid in uni:
                report.append(str(secid) + " " + database.getXrefFromSecid("TIC", secid, util.now(), "compustat_idhist"))
        
        if args.email and (len(report) > 0):
            util.email("Compustat to Reuters mapping changes", "\n".join(report))
        #print "\n".join(report)
    except:
        database.rollback()
        raise
    else:
        #database.rollback()
        database.commit()
    finally:
        if locked: database.releaseProcessedFilesLock()
