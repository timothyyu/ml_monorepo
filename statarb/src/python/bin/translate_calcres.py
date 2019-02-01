#!/usr/bin/env python
import os
import sys
import util
import re
import newdb
import gzip

newdb.init_db()
database = newdb.get_db()

def __getPrices(uni, date):
    prices={}
    args = {"secid" : None, "date" : date}
    for secid in uni:
        args["secid"] = secid
        row=database.execute("SELECT close FROM price_full WHERE secid=%(secid)s AND date=%(date)s AND died IS NULL ORDER BY date DESC LIMIT 1", args).fetchone()
        if row is not None:
            prices[secid]=row["close"]
        
    return prices
    
def __getBorrows(uni, date):
    borrows={}
    args = {"secid" : None, "date" : util.convert_date_to_millis(date)}
    for secid in uni:
        args["secid"] = secid
        row=database.execute("SELECT value FROM sec_attr_n WHERE secid=%(secid)s AND date=%(date)s AND type=2210 AND died IS NULL ORDER BY date DESC LIMIT 1", args).fetchone()
        if row is not None:
            borrows[secid]=row["value"]
        
    return borrows

def __getSplits(uni, date):
    splits={}
    args = {"date" : date}
    rows=database.execute("SELECT secid, IFNULL(rate,1.0) AS rate FROM split WHERE date=%(date)s AND died IS NULL",args)
    for row in rows:
        if not str(row["secid"]) in uni: continue
        splits[str(row["secid"])]=row["rate"]
        
    return splits

def __getDividends(uni, date):
    divs={}
    args = {"date" : date}
    rows=database.execute("SELECT secid, (IFNULL(dividend,0.0)+IFNULL(casheq,0.0)) AS divp FROM dividend WHERE date=%(date)s AND died IS NULL",args)
    for row in rows:
        if not str(row["secid"]) in uni: continue
        divs[str(row["secid"])]=row["divp"]
        
    return divs

def __translateFactor(factor):
    assert factor.startswith("F:")
    return factor.replace("F:B:", "F:B", 1)

if __name__ == "__main__":
    new2oldMappings = util.loadDictFromFile(os.environ["CONFIG_DIR"] + "/calcres.translation")
    old2newMappings = dict([(y, x) for x, y in new2oldMappings.iteritems()])
    
    #as strings
    old2newSecid = {}
    with open("/apps/ase/run/useq-live/old.secids.txt", "r") as file:
        for line in file:
            tokens = line.strip().split("|")
            old2newSecid[(tokens[0], tokens[1])] = tokens[2]
    
    reader = None        
    if len(sys.argv) == 2:
        assert sys.argv[1].endswith(".gz")
        reader = gzip.open(sys.argv[1], "r")
        date=sys.argv[1].split(".")[1]
        date=date[0:8]
    else:
        reader = sys.stdin
        date=None
        
    uni = set()
        
    for line in reader:
        if len(line) == 0: continue
        tokens = line.strip().split("|")
        assert re.match(r"\d{13}", tokens[0])
        
        #facror cov
        if tokens[3].startswith("C:"):
            continue
        elif tokens[1] == "0" and tokens[2] == "0" and tokens[4] == "-1":
            factors = tokens[3].split("::")
            assert len(factors) == 2, line
            print "|".join(("FCOV", __translateFactor(factors[0]), __translateFactor(factors[1]), tokens[5]))
        #fret
        elif tokens[1] == "0" and tokens[2] == "0" and tokens[3].startswith("fret_"):
            factor = tokens[3].split("_")[1]
            print "|".join(("-1", "R:fret_" + __translateFactor(factor), "N", "0", tokens[5], "NA", tokens[0]))
        elif tokens[3].startswith("F:"):
            factor=tokens[3]
            print "|".join((old2newSecid[(tokens[1], tokens[2])], __translateFactor(factor), "N", "0", tokens[5], "NA", tokens[0]))
        elif tokens[5] not in ("nan", "NaN"):
            uni.add(old2newSecid[(tokens[1], tokens[2])])
            print "|".join((old2newSecid[(tokens[1], tokens[2])], old2newMappings.get(tokens[3], tokens[3]), "N", str(max(0,long(tokens[4]))), tokens[5], "NA", tokens[0]))
            
            
    if date is not None:
        strdate=str(util.convert_date_to_millis(date))
        for secid, price in __getPrices(uni, date).iteritems():
            print "|".join((secid,"prcC","N",strdate,str(price),"NA",strdate))
        for secid, borrows in __getBorrows(uni, date).iteritems():
            print "|".join((secid,"BORROW_ALLOCATED","N",strdate,str(borrows),"NA",strdate))
        for secid, split in __getSplits(uni, date).iteritems():
            print "|".join((secid,"split","N",strdate,str(split),"NA",strdate))
        for secid, div in __getDividends(uni, date).iteritems():
            print "|".join((secid,"div","N",strdate,str(div),"NA",strdate))
