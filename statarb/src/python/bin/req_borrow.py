#!/usr/bin/env python
import os
import sys
import util
from gzip import GzipFile
from data_sources import file_source
import datafiles

ADV_FRACTION = 1.3 / 100.0
LOT_SIZE = 100
MIN_REQUEST = 5000
MAX_DOLLARS = 1.5e7
    
if __name__ == "__main__":
    util.check_include()
    util.set_log_file()
    
    #get last calcres of day
    fs = file_source.FileSource(os.environ["RUN_DIR"] + "/calcres")
    calcresFiles = fs.list(r'calcres.*\.txt\.gz')
    if len(calcresFiles) == 0:
        util.error("Failed to locate calcres file")
        sys.exit(1)
        
    calcresFiles.sort(key=lambda x: x[0], reverse=True)
    lastCalcresFile = os.environ["RUN_DIR"] + "/calcres/" + calcresFiles[0][0]    
    
    #get tradeable secs and advp
    tradeable = set()
    advps = {}
    prices = {}
    for line in GzipFile(lastCalcresFile, "r"):
        if line.startswith("FCOV"): continue
        secid, name, datatype, datetime, value, currency, born = line.split("|")
        if name == "TRADEABLE":
            tradeable.add(int(secid))
        elif name == "advp":
            advps[int(secid)] = float(value)
        elif name == "prcC": 
            prices[int(secid)] = float(value)
    
    #get tickers
    tic2sec, sec2tic = datafiles.load_tickers(os.environ["RUN_DIR"] + "/tickers.txt")
    
    requests = {}
    tot_requested = 0.0
    for secid in tradeable:
        ticker = sec2tic.get(secid, None)
        advp = advps.get(secid, None)
        price = prices.get(secid, None)
        
        if ticker is None or advp is None or price is None:
            util.error("Error while getting data for secid {}: ticker={}, advp={}, price={}".format(secid, ticker, advp, price))
            continue
        
        adv_frac = min(ADV_FRACTION * advp, MAX_DOLLARS)
        req = (int(adv_frac / price)/LOT_SIZE+1)*LOT_SIZE
        req = max(req, MIN_REQUEST)
        requests[ticker] = req
        tot_requested += price * req
    
    #now print the files
    requestFile=os.environ["RUN_DIR"]+"/locate_requests.txt"
    
    print "Writing request file: {}".format(requestFile)
    print "Total Requested Dollars: {}".format(tot_requested)
    print "Total stocks: {}".format(len(tradeable))
    print "Avg Requested: {}".format(tot_requested/len(tradeable))
     
    with open(requestFile,"w") as file:
        for ticker, request in sorted(requests.iteritems(),key=lambda x : x[0]):
            file.write(ticker+"|"+str(request)+"\n")
    
