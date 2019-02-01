import datetime
import os
import os.path
import util
import config
import datafiles
import newdb
import newdb.xrefsolve

database = newdb.get_db()
SOURCE = "yahoo"

def _parseFile(filepath):
    #this should only happen when we process the first file ever
    if filepath is None:
        return {},None,None,None
    
    info = datafiles.read_info_file(filepath)
    if os.path.basename(filepath).startswith("yearn_archive.txt"):
        backfill = 1
        archive = True
    elif info['date_last_absent'] is None:
        timestamp = util.convert_date_to_millis(info['date_modified'])
        backfill = 1
        archive = False
    else:
        timestamp = util.convert_date_to_millis(info['date_first_present'])
        backfill = 0
        archive = False
    
    file = open(filepath, "r")
    data={}
    
    for line in file:
        line = line.rstrip("\n")
        
        # Parse date
        # XXX all dates need to be in UTC based on exchange of stock
        annDate, name, ticker, value, time = line.split("\t")
        if time == 'Time Not Supplied':
            exactAnnDate = annDate + ' 00:00 UTC'
        elif time == 'Before Market Open':
            exactAnnDate = annDate + ' 08:00 EST'
        elif time == 'After Market Close':
            exactAnnDate = annDate + ' 17:00 EST'
        else:
            exactAnnDate = annDate +" "+ time.replace("ET", "EST")
        
        #annDate to millis
        try:
            exactAnnDate = util.convert_date_to_millis(exactAnnDate)
        except:
            util.warning("Failed to parse {}".format(exactAnnDate))
            print "Failed to parse {}".format(exactAnnDate)
            continue
        if archive:
            timestamp = util.convert_date_to_millis(annDate) - util.convert_date_to_millis(datetime.timedelta(days=30))
        
        secid = database.getSecidFromXref("TIC", ticker, timestamp, "compustat_idhist", newdb.xrefsolve.preferUS)
        if secid is None:
            util.warning("Failed to map ticker {}".format(ticker))
            continue

        coid, issueid = database.getCsidFromSecid(secid)
        assert coid is not None
    
        data[(coid,exactAnnDate,backfill)]=annDate
        #data.append((coid,exactAnnDate,backfill,timestamp))
    
    file.close()
        
    #get the file start date from the filename
    if not archive:
        startDate=os.path.normpath(filepath).split("/")[-1][0:8] #split the filepath, take last token and its first 8 chars
    else:
        startDate="20060101"
            
    return (data,archive,startDate,timestamp)

#A yearn file
def _getDeltas(filepath, source):
    localDir=config.load_source_config(source)["local_dir"]
    lastFilepath=database.getLastProcessedFile(source)
    if lastFilepath is not None:
        lastFilepath="/".join((os.environ["DATA_DIR"],localDir,lastFilepath))
        
    (lastData,lastArchive,lastStartDate,lastBornMillis)=_parseFile(lastFilepath)
    currentData,currentArchive,currentStartDate,currentBornMillis=_parseFile(filepath)
    assert (lastArchive is None and currentArchive is True) or currentArchive is False
    assert (currentStartDate>=lastStartDate)
    
    #get the data that need to be killed. these are data that were in the previous file, but not in
    #the current. The death time can be the timestamp in any item in currentData, since, except for
    #the very first archive file, all data should have the same timestamp 
    remove={}
    for entry,annDate in lastData.iteritems():
        if annDate<currentStartDate: #entry[1] is the annMillis
            continue
        if entry not in currentData:
            remove[entry]=currentBornMillis
            
    #get the data that need be inserted. similar to above
    insert={}
    for entry,annDate in currentData.iteritems():
        if entry not in lastData:
            insert[entry]=currentBornMillis

    return insert,remove

def process(filepath, source):

    insert,remove=_getDeltas(filepath, source)

    database.setAttributeAutoCreate(True)

    for k,v in remove.iteritems():
        coid=k[0]
        annMillis=k[1]
        died=v
        database.deleteAttribute("co", "d", coid, annMillis, source, "FUTURE_ANN_DATE", died)

    for k,v in insert.iteritems():
        coid=k[0]
        annMillis=k[1]
        backfill=k[2]
        born=v
        database.insertAttribute("co", "d", coid, annMillis, source, "FUTURE_ANN_DATE", annMillis, born, None,backfill)
    
if __name__ == "__main__":
    newdb.init_db()
    database = newdb.get_db()
    try:
        database.start_transaction()
        process("/apps/logs/ase/data/yahoo/yearn/2009/01/01/yearn_archive.txt.9aaa0838", "yearn")
        database.addProcessedFiles("yearn", "2009/01/01/yearn_archive.txt.9aaa0838", None)
        process("/apps/logs/ase/data/yahoo/yearn/2009/02/19/20090219.txt.f2b89c95", "yearn")
        database.addProcessedFiles("yearn","2009/02/19/20090219.txt.f2b89c95",None)
        process("/apps/logs/ase/data/yahoo/yearn/2009/02/20/20090220.txt.b7027c6c", "yearn")
    finally:
        database.rollback()
