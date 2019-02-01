#!/usr/bin/env python
import sys

portnew = sys.argv[1]
portold = sys.argv[2]

old2new = {}
secmappingfile = "/apps/ase/run/useq-live/old.secids.txt"
with open(secmappingfile) as file:
    for line in file:
        if len(line) <= 1: continue
        tokens = line.strip().split("|")
        old2new[tokens[0]] = tokens[2]

newsec2pos = {}
newnot = 0
with open(portnew) as file:
    for line in file:
        if len(line) <= 1: continue
        tokens = line.strip().split("|")
        if tokens[1] == "target_pos": continue
        pos = float(tokens[1])
        newsec2pos[tokens[0]] = pos 
        newnot += abs(pos)
        
oldsec2pos = {}
oldnot = 0
with open(portold) as file:
    for line in file:
        if len(line) <= 1: continue
        tokens = line.strip().split("|")
        if tokens[1] == "coid": continue
        newsecid = old2new[tokens[1]]
        pos = float(tokens[4])
        oldsec2pos[newsecid] = pos
        oldnot += abs(pos)
        
maxdiff = 0
maxsec = 0
cnt = 0
diffdollars = 0
dirdiff = 0
for secid in set(newsec2pos).union(oldsec2pos):
    newpos = newsec2pos[secid] if secid in newsec2pos else 0
    oldpos = oldsec2pos[secid] if secid in oldsec2pos else 0
    
    diff = newpos - oldpos
    if diff > maxdiff:
        maxdiff = diff
        maxsec = secid
    
    if newpos*oldpos>=0:    
        print "DIFF:  {}|{}|{}|{}".format(secid,newpos,oldpos, abs(diff))
    else:
        print "RDIFF:  {}|{}|{}|{}".format(secid,newpos,oldpos, abs(diff))
        
    if newpos == 0 and oldpos != 0:
#        print "THEM {} {} {}".format(secid, newpos, oldpos)
        if (abs(newpos - oldpos) > 500.0):
            dirdiff += 1
        diffdollars += abs(oldpos)
    elif newpos != 0 and oldpos == 0:
#        print "US {} {} {}".format(secid, newpos, oldpos)
        if (abs(newpos - oldpos) > 500.0):
            dirdiff += 1
        diffdollars += abs(newpos)
    elif newpos > 0 and oldpos > 0 or newpos < 0 and oldpos < 0:
        diffdollars += abs(diff)
    else:
        diffdollars += abs(diff)
        if (diffdollars > 500.0):
            dirdiff += 1
    cnt += 1
    
print "MAXDiff Security: {} {} Us: {} Them: {}".format(maxsec, maxdiff, newsec2pos[maxsec], oldsec2pos[maxsec])
print "New Notionasl: {} OldNotional: {}".format(newnot, oldnot)
print "Direction diffs: {} Pct: {}".format(dirdiff, float(dirdiff)/float(cnt))
print "Overlap pct: {}".format(1.0 - (diffdollars/newnot))

