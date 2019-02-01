import csv
import os.path
import util
import datafiles
import newdb
import config

database = newdb.get_db()
#SOURCE = "compustat_splits"
#BACKFILL = 1

def _parseFile(filepath):
    #this should only happen when we process the first file ever
    if filepath is None:
        return set(), None, None
    
    data = set()
    
    info = datafiles.read_info_file(filepath)
    if info['date_last_absent'] is None:
        timestamp = util.convert_date_to_millis(info['date_modified']) 
    else:
        timestamp = util.convert_date_to_millis(info['date_first_present'])
        
    csvfile = open(filepath)
    dialect = csv.Sniffer().sniff(csvfile.read(1024))
    csvfile.seek(0)
    reader = csv.DictReader(csvfile, dialect=dialect)
    for row in reader:
        secid = database.getSecidFromCsid(row['GVKEY'], row['IID'], timestamp)
        if secid is None:
            secid = database.createNewCsid(row['GVKEY'], row['IID'], timestamp, None, None, True)
            util.warning("Created new secid: {}.{}=>{}".format(row['GVKEY'], row['IID'], secid))
        data.add((secid, int(row["SPLITDATE"]), float(row["SPLITRATE"])))
        
    #get the file start date from the filename
    startDate = os.path.normpath(filepath).split("/")[-1][0:8] #split the filepath
    startDate = int(startDate)
            
    return data, startDate, timestamp

#A yearn file
def _getDeltas(filepath, source):
    localDir = config.load_source_config(source)["local_dir"]
    lastFilepath = database.getLastProcessedFile(source)
    if lastFilepath is not None:
        lastFilepath = "/".join((os.environ["DATA_DIR"], localDir, lastFilepath))
        
    lastData, lastStartDate, lastBornMillis = _parseFile(lastFilepath)
    currentData, currentStartDate, currentBornMillis = _parseFile(filepath)
    assert (currentStartDate >= lastStartDate)
    
    remove = ()
    for lastDatum in lastData:
        if lastDatum[2] < currentStartDate: #entry[1] is the annMillis
            continue
        if lastDatum not in currentData:
            remove.add(lastDatum)
            remove[lastDatum] = currentBornMillis
            
    #get the data that need be inserted. similar to above
    insert = set()
    for currentDatum in currentData:
        if currentDatum not in lastData:
            insert.add(currentDatum)

    return insert, remove, currentBornMillis

def process(filepath, source):
    insert, delete, born = _getDeltas(filepath, source)
    database.setAttributeAutoCreate(True)
    code=database.getAttributeType("FUTURE_SPLIT", source, "n", database.FUTURE_SPLIT)
    
    for entry in delete:
        updates=database.killOrDeleteTimelineRow(database.FUTURE_SPLIT, {"secid":entry[0], "date":entry[1]}, born)
        database.updateAttributeStats(code, *updates)
    
    for entry in insert:
        updates=database.insertTimelineRow(database.FUTURE_SPLIT, {"secid":entry[0], "date":entry[1]}, {"rate":entry[2]}, born)
        database.updateAttributeStats(code,*updates)
        

if __name__=="__main__":
    newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
    database=newdb.get_db()
    
    try:
        database.start_transaction()
        process("/apps/ase/data/compustat/splits/2009/01/01/20090101_future_splits.txt.f5f5cabe","compustat_splits")
        process("/apps/ase/data/compustat/splits/2009/01/02/20090102_future_splits.txt.90f7b861","compustat_splits")
    except Exception, e:
        database.rollback()
        raise
    else:
        database.rollback();