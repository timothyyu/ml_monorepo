#!/usr/bin/env python

import os
import time
import cPickle

import config
import datafiles
import util

def checkAcquireTimestamps():
    data_dir = os.environ['DATA_DIR']
    time_files = os.popen("find %s -name *.time" % data_dir).readlines()
    
    errors=[]
    warnings=[]
    normal=[]
    
    for file in time_files:
        result = os.popen("stat -c %%Y %s" % file)
        secs_since_timestamp = time.time() - float(max(result))

        if secs_since_timestamp>24*60*60: #24 hours
            errors.append("No new acquire timestamps on {} in {} hours".format(file.strip(), int(secs_since_timestamp) / (60*60)))
        elif secs_since_timestamp> 3*60*60: #3 hours
            warnings.append("No new acquire timestamps on {} in {} hours".format(file.strip(), int(secs_since_timestamp) / (60*60)))
        else:
            normal.append("No new acquire timestamps on {} in {} minutes".format(file.strip(), int(secs_since_timestamp) / 60))
            
    return (normal,warnings,errors)

def checkAcquireTimestampsAndNewFiles(dataCheckFrequency=1L*24L*60L*60L*1000L,defaultNewDataFrequency=1L*24L*60L*60L*1000L):
    sourceConfigDir=os.environ["CONFIG_DIR"]+"/sources"
    #sourceConfigDir="/apps/logs/ase/config/sources"
    
    errors=[]
    warnings=[]
    normal=[]
    
    for sourceConfigFile in os.listdir(sourceConfigDir):
        if sourceConfigFile[-3:]!=".py":
            continue
        
        sourceName=sourceConfigFile[:-3]
        sc=config.load_source_config(sourceName)
        
        #Check major errors first
        try:
            #sourceLocalDir=os.environ["DATA_DIR"]+"/"+sc["local_dir"]
            sourceLocalDir=os.environ["DATA_DIR"]+"/"+sc["local_dir"]
        except KeyError: #no local dir, old format
            #raise
            continue
        
        if not os.path.exists(sourceLocalDir):
            errors.append("{}: Never checked".format(sourceName))
            continue
        
        #get time file
        timeFile=sourceLocalDir+"/"+sourceName+".time"
        if not os.path.exists(timeFile):
            errors.append("{}: Never checked".format(sourceName))
            continue
        
        #optimize, go to the "oldest" subdir
        subdirs=os.listdir(sourceLocalDir)
        subdirs=sorted(filter(lambda x: os.path.isdir(sourceLocalDir+"/"+x),subdirs))
        
        if len(subdirs)==0:
            errors.append("{}: Never received a file".format(sourceConfigFile[:-3]))
            continue
        
        subdir=subdirs[-1]
        acquireTimestamp=0L;
        for node in os.walk(sourceLocalDir+"/"+subdir):
            dir=node[0]
            files=node[2]
            for file in files:
                if ".info" in file or ".time" in file or ".new" in file:
                    continue
                
                info=datafiles.read_info_file(dir+"/"+file)
                timestamp=util.convert_date_to_millis(info["date_first_present"])
                if timestamp>acquireTimestamp:
                    acquireTimestamp=timestamp
                    
        now=util.now()
        checkTimestamp=util.convert_date_to_millis(cPickle.load(open(timeFile, 'rb')))
        #get the frequency with which we expect new data
        expectedNewDataFrequency=sc.get("new_data_frequency",defaultNewDataFrequency)
                
        checkHours=(now-checkTimestamp)/(60*60*1000)
        checkMins=((now-checkTimestamp)%(60*60*1000))/(60*1000)
        acquireHours=(now-acquireTimestamp)/(60*60*1000)
        acquireMins=((now-acquireTimestamp)%(60*60*1000))/(60*1000)
        if (now-checkTimestamp)>dataCheckFrequency or (now-acquireTimestamp)>expectedNewDataFrequency:
            warnings.append("{}: Checked {} hours, {} mins ago, last file retrieved {} hours {} mins ago".format(sourceName,checkHours,checkMins,acquireHours,acquireMins))
        #elif (now-maxTimestamp)>36*60*60*1000: #1 day
        #    warnings.append("{}: Checked {} hours ago, last file retrieved {} hours ago".format(sourceName,(now-acquireTimestamp)/(60*60*1000),(now-maxTimestamp)/(60*60*1000)))
        else:
            normal.append("{}: Checked {} hours, {} mins ago, last file retrieved {} hours {} mins ago".format(sourceName,checkHours,checkMins,acquireHours,acquireMins))
            
    return normal,warnings,errors
            
#XXX need to check for how old the database lock is...

if __name__ == "__main__":
    totalErrors=[]
    totalWarnings=[]
    totalNormal=[]
        
    normal,warnings,errors=checkAcquireTimestampsAndNewFiles()
    totalNormal.extend(normal)
    totalWarnings.extend(warnings)
    totalErrors.extend(errors)
    
#    print "**ERRORS({})**".format(len(totalErrors))
#    for msg in totalErrors:
#        print msg
        
    print "**WARNINGS({})**".format(len(totalWarnings))
    for msg in sorted(totalWarnings):
        print msg
        
    print "\n\n**Normal({})**".format(len(totalNormal))
    for msg in sorted(totalNormal):
        print msg
