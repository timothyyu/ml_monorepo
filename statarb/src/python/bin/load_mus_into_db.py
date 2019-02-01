#!/usr/bin/env python
import argparse
import util
import os
import newdb
import sys
import datetime
import tempfile
import shutil

database = None

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
    parser.add_argument('--from',action="store",dest="fromDate")
    parser.add_argument('--to',action="store",dest="toDate")
    parser.add_argument('--day',action="store",dest="singleDate")
    parser.add_argument('--today',action="store_const",const=True,dest="today",default=False)
    parser.add_argument("--location",action="store",dest="location",default=os.path.join(os.environ["ROOT_DIR"], "run", os.environ["STRAT"]))
    parser.add_argument("--database", action="store", dest="db", default="pri")
    parser.add_argument("--force", action="store_const", const=True, dest="force", default = False)
    args = parser.parse_args()

    #Set debug
    if args.debug:
        util.set_debug()
    else:
        util.set_log_file()
        
    #Figure out from-to dates
    dayDelta=datetime.timedelta(days=1)
    if args.today is True:
        fromDate=datetime.datetime.utcnow()
        fromDate=datetime.datetime.strptime(fromDate.strftime("%Y%m%d"),"%Y%m%d") #Get only date
        toDate=fromDate+dayDelta
    elif args.singleDate is not None:
        fromDate=datetime.datetime.strptime(args.singleDate,"%Y%m%d")
        toDate=fromDate+dayDelta
    elif args.fromDate is not None and  args.toDate is not None:
        fromDate=datetime.datetime.strptime(args.fromDate,"%Y%m%d")
        toDate=datetime.datetime.strptime(args.toDate,"%Y%m%d")
    else:
        parser.print_help(util.LOGFILE)
        exit(1)
        
    if args.db == "pri":
        newdb.init_db()
        database = newdb.get_db()
    elif args.db == "sec":
        newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
        database = newdb.get_db()
    else:
        util.error("Valid database choices are [pri|sec]")
        sys.exit(1)
    
    try:    
        #create a lock
        lockf = None
        lockf = util.lock(args.db)
        tmpDir = None
        
        database.setAttributeAutoCreate(True)
        
        date=fromDate
        while date<toDate:
            datestr = date.strftime("%Y%m%d")
            buffer = []
            try:
                database.start_transaction()
                #get the most recent ts from the db
                max_ts_in_db = database.execute("SELECT max(date) as max_ts_in_db FROM mus").fetchall()
                if len(max_ts_in_db) == 0: max_ts_in_db = 0 
                else: max_ts_in_db = max_ts_in_db[0]["max_ts_in_db"]
                
                musdir = os.path.join(args.location, datestr, "mus")
                if not os.path.exists(musdir):
                    continue
                
                for mufile in sorted(os.listdir(musdir)):
                    util.info("Processing file {}/{}".format(musdir, mufile))
                    tokens = mufile.split(".")
                    if not tokens[0] == "mus": continue
                    ts_token = 1
                    mus_type = 0
                    if tokens[1] == "FULL":
                        ts_token += 1
                        mus_type = 2
                    elif tokens[1] == "SHORT":
                        ts_token += 1
                        mus_type = 1
                        
                    if mus_type != 2: continue
                        
                    mus_ts = util.convert_date_to_millis(datetime.datetime.strptime(tokens[ts_token], "%Y%m%d_%H%M"))
                    
                    if (not args.force) and (mus_ts <= max_ts_in_db):
                        continue
                    
                    row = {}
                    with open(musdir + "/" + mufile, "r") as file:
                        for line in file:
                            tokens = line.strip().split("|")
                            secid = int(tokens[0])
                            
                            fc = tokens[1]
                            fc_type = database.getAttributeType(fc, "mus", "n", "mus")                            
                            value = float(tokens[2])
                            
                            buffer.append((secid, fc_type, mus_ts, value))
                
                util.info("Sorting and writing")
                buffer.sort()

                tmpDir = util.tmpdir()
                tmpFile = tmpDir+"/mus.tmp"
                with open(tmpFile, "w") as f:
                    for row in buffer:
                        f.write("{},{},{},{}\n".format(row[0], row[1], row[2], row[3]))
                        
                database.execute("LOAD DATA LOCAL INFILE '{}' INTO TABLE mus FIELDS TERMINATED BY ','".format(tmpFile))
                
                shutil.rmtree(tmpDir, True)
                tmpDir = None
                    
            except Exception,e:
                database.rollback()
                util.error(str(e))
                raise e
            else:
                database.commit()
            finally:
                date=date+dayDelta
    finally:
        if lockf is not None: lockf.release()
        if tmpDir is not None: shutil.rmtree(tmpDir, True)
    
    