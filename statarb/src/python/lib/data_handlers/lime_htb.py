import os

import datafiles
import util
import newdb
import newdb.xrefsolve
import re

database = newdb.get_db()
SOURCE="lime"

def handle_htb(ticker, date, born,backfill):
    origTicker=ticker
    #Do the following conversions: - to .P, +$ to .WS, +X to .WX
    ticker=ticker.strip()
    ticker=re.sub(r"-",".P",ticker)
    ticker=re.sub(r"\+$", ".WS", ticker)
    ticker=re.sub(r"\+",".W",ticker)
    
    secid=database.getSecidFromXref("TIC", ticker, born, "compustat_idhist", newdb.xrefsolve.preferUS)
    if secid is None:
        util.warning("Failed to map ticker {}".format(origTicker))
        return
    
    database.insertAttribute("sec", "n", secid, date, SOURCE, "LHTB", 1, born, None, backfill)
        
def process(filepath, source):
    date = os.path.basename(filepath).split('.')[2]
    born = date + " 09:30 EST"
    date_millis = util.convert_date_to_millis(date)
    born_millis = util.convert_date_to_millis(born)

    # If we have acquisition times, use these for real born_millis time
    info = datafiles.read_info_file(filepath)
    if info['date_last_absent'] is not None:
        born = util.convert_date_to_millis(info['date_first_present'])
        backfill=0
    else:
        born=util.convert_date_to_millis(date+" 09:30 EST")
        backfill=1
        
    database.setAttributeAutoCreate(True)

    for line in file(filepath):
        handle_htb(line, date_millis, born_millis,backfill)