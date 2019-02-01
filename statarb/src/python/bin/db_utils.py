#!/usr/bin/env python
import argparse
import util
import newdb
import subprocess
import os
import time
import sys
import datetime
import shutil
import properties

database=newdb.get_db()
ROLLING_DAYS=7

def rollingBackupDB(dbConfig, raw):
    #backup current day T
    rollingDir=os.path.join(os.environ["ROOT_DIR"],"logs","db_bkups","rolling")
    weeklyDir=os.path.join(os.environ["ROOT_DIR"],"logs","db_bkups","weekly")
    if raw:
        bkupFile=rawBackupDB(dbConfig,dir=rollingDir)
    else:
        bkupFile=logicalBackupDB(dbConfig, dir=rollingDir)
    #also move to weekly if FRIDAY
    t=datetime.datetime.utcnow()
    if int(t.strftime("%w"))==5:
        shutil.copy(rollingDir+"/"+bkupFile, weeklyDir+"/"+bkupFile)
    
    #delete all backups <= T-ROLLING_DAYS
    t_minus_rollback=t-datetime.timedelta(days=ROLLING_DAYS)
    for path,dirs,files in os.walk(rollingDir):
        for file in files:
            if file.endswith(".mysql.gz") or file.endswith("tar.gz") or file.endswith(".bak"):
                bkupdate=file.split(".")[0]
                try:
                    bkupdate=datetime.datetime.strptime(bkupdate,"%Y%m%d_%H%M")
                    if bkupdate<=t_minus_rollback:
                        os.remove(path+"/"+file)
                except:
                    pass

def logicalBackupDB(dbConfig,dir=os.path.join(os.environ["ROOT_DIR"],"logs","db_bkups","adhoc"),filename="{}.mysql.gz".format(datetime.datetime.utcnow().strftime("%Y%m%d_%H%M"))):
    p=subprocess.Popen("{install_dir}/mysql/bin/mysqldump --opt --all-databases --skip-lock-tables --single-transaction --flush-logs --master-data=2 --host={host} --port={port} --user={user} --password={password} | gzip > {dir}/{filename}".format(install_dir=os.environ["INSTALL_DIR"],host=dbConfig["host"],port=dbConfig["port"],user="root",password="root1",dir=dir,filename=filename),shell=True)
    p.wait()
    return filename
    
def rawBackupDB(dbConfig,dir=os.path.join(os.environ["ROOT_DIR"],"logs","db_bkups","adhoc"),filename="{}.tar.gz".format(datetime.datetime.utcnow().strftime("%Y%m%d_%H%M"))):
    p=subprocess.Popen("tar -czf {dir}/{filename} {datadir}".format(dir=dir,filename=filename,datadir=dbConfig["datadir"]),shell=True)
    p.wait()
    return filename
    
def optimizeDB():
    rows=database.execute("SHOW TABLES").fetchall()
    for row in rows:
        database.execute("OPTIMIZE TABLE {}".format(row["Tables_in_ase"]))
    
    
if __name__=="__main__":
    parser = argparse.ArgumentParser(description='DB utils')
    
    parser.add_argument("--rolling",action="store_const",const=True,dest="rolling",default=False)
    parser.add_argument("--backup",action="store_const",const=True,dest="backup",default=False)
    parser.add_argument("--optimize",action="store_const",const=True,dest="optimize",default=False)
    parser.add_argument("--raw",action="store_const",const=True,dest="raw",default=False)
    parser.add_argument("--database",action="store",dest="db",default="pri")
    args = parser.parse_args()
    
    util.set_log_file()
    
    dbConfig=None
    if args.db=="pri":
        newdb.init_db()
        database = newdb.get_db()
        p = properties.Properties()
        p.load(open(os.environ["DB_CONFIG_FILE"],"r"))
        dbConfig = p.getPropertyDict()
        
        with open(os.environ["DB_SERVER_CONFIG_FILE"],"r") as file:
            for line in file:
                if line.startswith("datadir"):
                    tokens=line.split("=")
                    datadir=tokens[1].strip()
                    dbConfig["datadir"]=datadir
                    break
                        
    elif args.db=="sec":
        newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
        database = newdb.get_db()
        p = properties.Properties()
        p.load(open(os.environ["SEC_DB_CONFIG_FILE"],"r"))
        dbConfig = p.getPropertyDict()
        
        with open(os.environ["SEC_DB_SERVER_CONFIG_FILE"],"r") as file:
            for line in file:
                if line.startswith("datadir"):
                    tokens=line.split("=")
                    datadir=tokens[1].strip()
                    dbConfig["datadir"]=datadir
                    break
    else:
        util.error("Valid database choices are [pri|sec]")
        sys.exit(1)
    
    locked=False
    try:
        startTime=time.time() #in seconds since epoch
        while not locked:
            if time.time()-startTime>8*60*60: #have been polling for 8 hours
                util.error("db_utils unable to establish lock after {} hours. Aborting...".format(1.0*(time.time()-startTime)/60.0/60.0))
                sys.exit(1)
            time.sleep(1) #poll every 1 second
            locked=database.getProcessedFilesLock()
            
        util.info("Lock established")
        
        if args.optimize:
            util.info("Optimizing")
            optimizeDB()
            util.info("Optimization completed")
        
        if args.raw:
            database.execute("FLUSH TABLES")
        
        if args.backup:
            util.info("Backing up")
            if args.raw:
                rawBackupDB(dbConfig)
            else:
                logicalBackupDB(dbConfig)
            util.info("Back up completed")
            
        if args.rolling:
            util.info("Backing up")
            rollingBackupDB(dbConfig, args.raw)
            util.info("Back up completed")  
    finally:
        if locked: database.releaseProcessedFilesLock()