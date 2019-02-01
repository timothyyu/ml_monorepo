#!/usr/bin/env python
import sys
import os
import subprocess
import gzip
import util
import datetime

resetBornIndeps = set(["advp"])

def runR(script):
    rcommand="Rscript -e \"{}\"".format(script)
    p=subprocess.Popen(rcommand,env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    data=p.stdout.read()
    p.stderr.read()
    p.wait()
    return data

def getDeps(intraday):
    separator="-----"
    if intraday:
        function = "print.deps.intra()"
    else:
        function = "print.deps()"
    data=runR("source('fit.R'); write('{}',file=''); {};".format(separator,function))
    data=data.splitlines(False)
    return data[data.index(separator)+1:]

def getIndeps(intraday):
    separator="-----"
    if intraday:
        function = "print.indeps.intra()"
    else:
        function = "print.indeps()"
    data=runR("source('fit.R'); write('{}',file=''); {};".format(separator,function))
    data=data.splitlines(False)
    return data[data.index(separator)+1:]

### SIM_DIR
simdir = sys.argv[1]
intraday = True if (len(sys.argv)>2 and (sys.argv[2] == "TRUE" or sys.argv[2].startswith("intra"))) else False
slim = True if (len(sys.argv)>3 and (sys.argv[3] == "TRUE" or sys.argv[3].startswith("slim"))) else False
print "Massageing fit data..."

calcresFolder = simdir+"/calcres_intraday" if slim else simdir+"/calcres"
calcresPrefix = "calcres"

fitresFolder = simdir + "/fit/fitres"
fitresPrefix = "fitres_intraday." if intraday else "fitres."

######### INDEPENDENT VARIABLES ######################

indeps=set(getIndeps(intraday))
indepsTable={}

for calcFile in os.listdir(calcresFolder):
    if not calcFile.startswith(calcresPrefix): continue
    print "Reading " + calcFile
    
    #get the timestamp of the calcres
    ts = calcFile.split(".")[1]
    ts = util.convert_date_to_millis(datetime.datetime.strptime(ts, "%Y%m%d_%H%M"))
    
    with gzip.open(calcresFolder+"/"+calcFile,"r") as file:
        for line in file:
            tokens = line.strip().split("|")
            if tokens[1] in indeps:
                vdata=indepsTable.get(tokens[1], None)
                if vdata is None:
                    vdata=[]
                    indepsTable[tokens[1]]=vdata
                born = long(tokens[6])
                #if it is a full calcres, see if we need to reset the born time of the attribute
                if (not slim) and (tokens[1] in resetBornIndeps): 
                    born = ts
                vdata.append((int(tokens[0]),float(tokens[4]), born))
                
for fitFile in os.listdir(fitresFolder):
    if not fitFile.startswith(fitresPrefix): continue
    print "Reading: " + fitFile
    with gzip.open(fitresFolder+"/"+fitFile,"r") as file:
        for line in file:
            tokens = line.strip().split("|")
            if tokens[1] in indeps:
                vdata=indepsTable.get(tokens[1], None)
                if vdata is None:
                    vdata=[]
                    indepsTable[tokens[1]]=vdata
                vdata.append((int(tokens[0]),float(tokens[4]), long(tokens[6])))

indepsDir = simdir+"/fit/intra.indeps" if intraday else simdir+"/fit/indeps"
try:
    os.makedirs(indepsDir)
except:
    pass
for indep,e in indepsTable.iteritems():
    print "Writing indep: " + indep
    with gzip.open(indepsDir+"/"+indep+".gz","w") as file:
        for data in e:
            file.write(str(data[0])+"|"+str(data[1])+"|"+str(data[2])+"\n")
indepsTable.clear()


######### DEPENDENT VARIABLES ######################

deps=set(getDeps(intraday))
depsTable={}

for fitFile in os.listdir(fitresFolder):
    if not fitFile.startswith(fitresPrefix): continue
    print "Reading: " + fitFile
    with gzip.open(fitresFolder+"/"+fitFile,"r") as file:
        for line in file:
            tokens = line.strip().split("|")
            if tokens[1] in deps:
                vdata=depsTable.get(tokens[1], None)
                if vdata is None:
                    vdata=[]
                    depsTable[tokens[1]]=vdata
                vdata.append((int(tokens[0]),float(tokens[4]), long(tokens[6])))
                
depsDir = simdir+"/fit/intra.deps" if intraday else simdir+"/fit/deps"
try:
    os.makedirs(depsDir)
except:
    pass
for dep,e in depsTable.iteritems():
    print "Writing dep: " + dep
    with gzip.open(depsDir+"/"+dep+".gz","w") as file:
        for data in e:
            file.write(str(data[0])+"|"+str(data[1])+"|"+str(data[2])+"\n")
