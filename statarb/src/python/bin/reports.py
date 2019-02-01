#!/usr/bin/env python

import os
import datetime
import argparse
import pytz
import util
import newdb
import subprocess
import shutil

database=newdb.get_db()

def xrefChanges2(date1=None,date2=None):
    #read the secids we are interested in. we might want to change the source
    uni=set()
    #with open("/".join((os.environ["ROOT_DIR"],"run",os.environ["STRAT"],"old.secids.txt")),"r) as file:
    with open("/apps/ase/run/useq-live/old.secids.txt","r") as file:
        for line in file:
            tokens=line.strip().split("|")
            uni.add(tokens[2])
            
    if date2 is None:
        date2=util.now()
    if date1 is None:
        date1=util.exchangeTradingOffset(os.environ["PRIMARY_EXCHANGE"], util.convert_millis_to_datetime(date2).strftime("%Y%m%d"), -1)
        date1=util.convert_date_to_millis(str(date1))
    
    tickerChanges=[]
    cusipChanges=[]
    for secid in uni:
        ticker1=database.execute("SELECT value FROM xref WHERE secid={secid} AND xref_type=2 AND source=2 AND born<={date} AND (died IS NULL OR died>{date})".format(secid=secid,date=date1)).fetchone()
        ticker1=ticker1["value"] if ticker1 is not None else None
        
        ticker2=database.execute("SELECT value FROM xref WHERE secid={secid} AND xref_type=2 AND source=2 AND born<={date} AND (died IS NULL OR died>{date})".format(secid=secid,date=date2)).fetchone()
        ticker2=ticker2["value"] if ticker2 is not None else None
        
        cusip1=database.execute("SELECT value FROM xref WHERE secid={secid} AND xref_type=1 AND source=2 AND born<={date} AND (died IS NULL OR died>{date})".format(secid=secid,date=date1)).fetchone()
        cusip1=cusip1["value"] if cusip1 is not None else None
        
        cusip2=database.execute("SELECT value FROM xref WHERE secid={secid} AND xref_type=1 AND source=2 AND born<={date} AND (died IS NULL OR died>{date})".format(secid=secid,date=date2)).fetchone()
        cusip2=cusip2["value"] if cusip2 is not None else None
        
        if ticker1!=ticker2: tickerChanges.append((secid,ticker1,ticker2))
        if cusip1!=cusip2: cusipChanges.append((secid,cusip1,cusip2))
        
    report=[]
    report.append("Xref changes between {} and {}".format(util.convert_millis_to_datetime(date1).strftime("%Y%m%d"),util.convert_millis_to_datetime(date2).strftime("%Y%m%d")))
    for secid,x1,x2 in tickerChanges:
        report.append("{}: {} => {}".format(secid,x1,x2))
    for secid,x1,x2 in cusipChanges:
        report.append("{}: {} => {}".format(secid,x1,x2))
        
    return "\n".join(report) if len(report)>1 else None
    
def newProcessedFiles():
    sources={}
    for x in database.execute("SELECT code,name FROM {} GROUP BY code".format(database.SOURCE_TYPE)).fetchall():
        sources[x["code"]]=x["name"]
        
    attributes={}
    for x in database.execute("SELECT code,name,source,tableref FROM {}".format(database.ATTRIBUTE_TYPE_TABLE)).fetchall():
        attributes[x["code"]]=(sources[x["source"]],x["name"],x["tableref"])
    
    output=[]
    #get last check timestamp
    lastCheckFilepath="/".join((os.environ["SCRAP_DIR"],"processed.last"))
    try:
        file=open(lastCheckFilepath,"r")
        data=file.read().strip()
        lastTimestamp=long(data)
        dt=util.convert_millis_to_datetime(lastTimestamp)
        dt=dt.astimezone(pytz.timezone("US/Eastern"))
        output.append("Files processed since {}".format(dt.strftime("%Y%m%d %H:%M:%S")))
        file.close()
    except:
        lastTimestamp=util.now()-util.convert_date_to_millis(datetime.timedelta(hours=1))
        output.append("No last check time available. Displaying new files processed within the last 1 hour.")
        
    currentTimestamp=util.now()
    rows=database.execute("SELECT * FROM processed_files WHERE ts>={} ORDER BY ts".format(lastTimestamp)).fetchall()
    
    numOfFiles=len(rows)

    if numOfFiles==0: #if nothing to be printed, print nothing. do not update timestamp
        return None
    
    output.append("")
    processedBySource = {}
    for row in rows:
        dt=util.convert_millis_to_datetime(long(row["ts"]))
        dt=dt.astimezone(pytz.timezone("US/Eastern"))
        source = sources[row["source"]]
        path = row["path"].split("/")[-1]
        secs = float(row["processing_time"])/1000
        
        p = processedBySource.get(source, None)
        if p is None:
            p = []
            processedBySource[source] = p
        p.append((dt, path, secs))
        
    for source in sorted(processedBySource.keys()):
        files = processedBySource[source]
        if len(files) <= 20:
            for dt, path, secs in files:
                output.append("[{}]: {}, {}, {} secs".format(dt.strftime("%Y%m%d %H:%M:%S"),source,path,secs))
        else:
            #print first 10
            for dt, path, secs in files[0:10]:
                output.append("[{}]: {}, {}, {} secs".format(dt.strftime("%Y%m%d %H:%M:%S"),source,path,secs))
            output.append("... ({} more files) ...".format(len(files) - 20))
            #print last 10
            for dt, path, secs in files[-10:]:
                output.append("[{}]: {}, {}, {} secs".format(dt.strftime("%Y%m%d %H:%M:%S"),source,path,secs))
        output.append("")
        
    rows=database.execute("SELECT stats.type AS type, SUM(stats.inserted) AS inserted,SUM(stats.killed) AS killed FROM processed_files AS files, processed_files_att_stats AS stats WHERE files.ts>={} AND files.source=stats.source AND files.path=stats.path GROUP BY stats.type ORDER BY stats.type".format(lastTimestamp)).fetchall()
    output.append("")
    output.append("Database attributes affected (inserted/killed)")
    for row in sorted(rows,key=lambda x:attributes[x["type"]][1]):
        output.append("{}, {}, {}: {} / {}".format(attributes[row["type"]][0],attributes[row["type"]][1],attributes[row["type"]][2],row["inserted"],row["killed"]))

    #save the check time
    file=open(lastCheckFilepath,"w")
    file.write(str(currentTimestamp))
    file.close()
    
    return "\n".join(output)

def qcc():
    rCode=os.environ["R_DIR"]+"/models.R"
    rcommand="Rscript -e \"source('{}'); qccReport();\"".format(rCode) 
    util.log(rcommand)
    p=subprocess.Popen(rcommand,env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    util.info(p.stdout.read())
    util.info(p.stderr.read())
    p.wait()
    try:
        shutil.copy(os.environ["REPORT_DIR"]+"/qcc/qcc.pdf", os.environ["TOMCAT_DIR"]+"/webapps/ROOT/qcc.pdf")
    except:
        pass

if __name__=="__main__":    
    parser = argparse.ArgumentParser(description='Generate reports')

    parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
    parser.add_argument("--xref-changes",action="store_const",const=True,dest="xref_changes",default=False)
    parser.add_argument("--processed-files",action="store_const",const=True,dest="processed_files",default=False)
    parser.add_argument("--qcc",action="store_const",const=True,dest="qcc",default=False)

    args = parser.parse_args()
    
    if not args.debug:
        util.set_log_file("na") 
        
    newdb.init_db()
    database=newdb.get_db()
    
    if args.qcc:
        qcc()
    
    if args.xref_changes:
        report=xrefChanges2()
        if args.debug:
            print report
        elif report is not None:
            util.email("Xref changes", report)
            
    if args.processed_files:
        if args.debug:
            print newProcessedFiles()
        else:
            output=newProcessedFiles()
            if output is not None: util.email("New processed files",output)
