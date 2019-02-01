#!/usr/bin/env python
import sys

if __name__=="__main__":
    secidApp = {}
    bars = 0
    emptyBars = 0
    
    for line in sys.stdin:
        if len(line)<=0: continue
        tokens = line.strip().split("|")
        
        if len(tokens)<15:
            open=float(tokens[2])
            secid=int(tokens[0])
            if open<=0:
                emptyBars+=1
            bars+=1
            secidApp[secid]=secidApp.get(secid,0)+1
        else:
            first=float(tokens[4])
            secid=int(tokens[0])
            if first<=0:
                emptyBars+=1
            bars+=1
            secidApp[secid]=secidApp.get(secid,0)+1
            
            
    print "Bars: {}, Empty: {} ({:.0f}%), Secids:{}, MaxBars:{}".format(bars, emptyBars, 100.0*emptyBars/bars, len([s for s in secidApp.iterkeys()]), max([x for x in secidApp.itervalues()]))