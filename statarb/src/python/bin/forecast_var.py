#!/usr/bin/env python
import sys
import os
import math

if __name__=="__main__":
    if len(sys.argv)<3:
        print "Use as forecast_var.py <forecast> <mus folder>"
    
    fcast = sys.argv[1]
    muDir = sys.argv[2]
    
    secid2fcast={}
    
    for file in sorted(os.listdir(muDir)):
        if not file.startswith("mu"): continue
        
        with open(muDir+"/"+file, "r") as f:
            for line in f:
                tokens = line.strip().split("|")
                secid = int(tokens[0])
                fc = tokens[1]
                mu = 10000*float(tokens[2])
                
                if fc != fcast: continue
                
                values = secid2fcast.get(secid, None)
                if values is None:
                    values=[]
                    secid2fcast[secid]=values
                values.append(mu)
                
    
    secid2var={}
    for secid, mus in secid2fcast.iteritems():
        sum = 0
        sum2 = 0
        cnt = 0
        
        for x in mus:
            sum+=x
            sum2+=x*x
            cnt+=1
        
        try:
            secid2var[secid]=math.sqrt(sum2/cnt - sum*sum/cnt/cnt)
        except ValueError:
            continue
        
    topvars = sorted(secid2var.iteritems(), key=lambda x : -x[1])
    
    kkk=0
    for secid, var in topvars:
        mus = secid2fcast[secid]
        mus= ["{:.1f}".format(x) for x in mus]
        print secid," ".join(mus)
        kkk+=1
        if kkk==100: break
        