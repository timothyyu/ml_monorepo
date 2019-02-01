#!/usr/bin/env python
import sys
import calcresSummary
import util
import shutil
import os

if __name__=="__main__":
    if len(sys.argv)!=3:
        print "Use as compare_calcres.py <newfile> <oldfile>"
        sys.exit(1)
        
    util.set_silent()
    new2oldMappings = util.loadDictFromFile(os.environ["CONFIG_DIR"]+"/calcres.translation")
    
    newCalcresFile=sys.argv[1]
    oldCalcresFile=sys.argv[2]
    
    tmpdir=util.tmpdir()
    #load new calcres
    newC={}
    calcresSummary.calcresStats(newCalcresFile, tmpdir+"/new.txt", False)
    with open(tmpdir+"/new.txt","r") as file:
        for line in file:
            if len(line)<=1: continue
            tokens=line.strip().split("|")
            attr=tokens[0]
            size=int(tokens[1])
            
            mean=float(tokens[2]) if tokens[2]!="NA" else float('nan')
            std=float(tokens[3]) if tokens[3]!="NA" else float('nan')
            mmin=float(tokens[4]) if tokens[4]!="NA" else float('nan')
            mmax=float(tokens[5]) if tokens[5]!="NA" else float('nan')
            newC[attr]=(size,mean,std,mmin,mmax)
            
    oldC={}
    calcresSummary.calcresStats(oldCalcresFile, tmpdir+"/old.txt", True)
    with open(tmpdir+"/old.txt","r") as file:
        for line in file:
            if len(line)<=1: continue
            tokens=line.strip().split("|")
            attr=tokens[0]
            size=int(tokens[1])
            
            mean=float(tokens[2]) if tokens[2]!="NA" else float('nan')
            std=float(tokens[3]) if tokens[3]!="NA" else float('nan')
            mmin=float(tokens[4]) if tokens[4]!="NA" else float('nan')
            mmax=float(tokens[5]) if tokens[5]!="NA" else float('nan')
            oldC[attr]=(size,mean,std,mmin,mmax)
    
    shutil.rmtree(tmpdir)
    
    for k in sorted(newC.iterkeys()):
        if k in new2oldMappings and new2oldMappings[k] is not None:
            nc=newC[k]
            oc=oldC[new2oldMappings[k]]
            print '--------------------------------------------------------------------------------------'
            print "{:<45s} {:5d} {: .6f} {: .6f} {: .6f} {: .6f}".format(k,nc[0],nc[1],nc[2],nc[3],nc[4])
            print "{:<45s} {:5d} {: .6f} {: .6f} {: .6f} {: .6f}".format(new2oldMappings[k],oc[0],oc[1],oc[2],oc[3],oc[4])