#!/usr/bin/env python

import backoffice
import argparse
import datetime
import os
import sys
import util
import newdb

def email(report, date):
    subject = "Back office report for {}".format(date)
    body1 = ["Breaks:"]
    body2 = ["Suggested cap adjustments:", "*WARNING* Verify correctness and make sure they are not due to splits or other reason."]
    
    for line in report.split("\n"):
        if len(line) == 0:
            continue
        if line.startswith("#LBAD") or line.startswith("#RBAD"):
            continue
        tokens = line.strip().split("|")
        if tokens[2] != "00":
            body1.append(line)
            body2.append("FILL|{}|{}|{}|ABSOLUTE|{}, missing fill".format(tokens[1], tokens[5], int(tokens[4])-int(tokens[3]), tokens[0]))
            
    body = "\n".join(body1)+"\n\n"+"\n".join(body2)
    util.email(subject, body)
            

parser = argparse.ArgumentParser(description='Generate backoffice reconciliation report')

parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
parser.add_argument('--from',action="store",dest="fromDate")
parser.add_argument('--to',action="store",dest="toDate")
parser.add_argument('--day',action="store",dest="singleDate")
parser.add_argument("--recent",action="store_const",const=True,dest="recent",default=False)
parser.add_argument("--yesterday",action="store_const",const=True,dest="yesterday",default=False)
parser.add_argument("--all",action="store_const",const=True,dest="all",default=False)
parser.add_argument("--file",action="store_const",const=True,dest="report",default=False)
parser.add_argument("--old",action="store_const",const=True,dest="old",default=False)
parser.add_argument("--email",action="store_const",const=True,dest="email",default=False)

args = parser.parse_args()

#Set debug
if args.debug:
    util.set_debug()
else:
    util.set_log_file()

newdb.init_db()
backoffice.database=newdb.get_db()

#Figure out from-to dates
dayDelta=datetime.timedelta(days=1)
if args.singleDate is not None:
    fromDate=datetime.datetime.strptime(args.singleDate,"%Y%m%d")
    toDate=fromDate+dayDelta
elif args.fromDate is not None and  args.toDate is not None:
    fromDate=datetime.datetime.strptime(args.fromDate,"%Y%m%d")
    toDate=datetime.datetime.strptime(args.toDate,"%Y%m%d")
elif args.recent is True:
    toDate=datetime.datetime.utcnow()
    toDate=datetime.datetime.strptime(toDate.strftime("%Y%m%d"),"%Y%m%d") #Get only date
    
    fromDate=toDate-dayDelta
    while (fromDate.weekday()>5): #skip weekends
        fromDate=fromDate-dayDelta
    #go back another day just in case of holidays
    fromDate=fromDate-dayDelta
elif args.all is True:
    fromDate=datetime.datetime(2010,1,1)
    toDate=datetime.datetime.now()
    toDate=datetime.datetime.strptime(toDate.strftime("%Y%m%d"),"%Y%m%d") #Get only date
elif args.yesterday:
    toDate=datetime.datetime.utcnow()
    toDate=datetime.datetime.strptime(toDate.strftime("%Y%m%d"),"%Y%m%d") #Get only date
    fromDate=util.exchangeTradingOffset(os.environ["PRIMARY_EXCHANGE"], toDate.strftime("%Y%m%d"), -1)
    fromDate=datetime.datetime.strptime(str(fromDate),"%Y%m%d")
else:
    parser.print_help(util.LOGFILE)
    exit(1)

#Only single day should be output to screen
if (args.singleDate is None) and (args.report is False):
    parser.print_help(util.LOGFILE)
    exit(1)
    
date=fromDate
while date<toDate:
   
    try: 
        reco=backoffice.singleDayReconcile(date,args.old)
        if args.report:
            output=open(os.environ["REPORT_DIR"]+"/borecon/"+date.strftime("%Y%m%d")+".txt","w")
        else:
            output=sys.stdout
        output.write(reco)
        if output!=sys.stdout:
            output.close()
        if args.email:
            email(reco, date.strftime("%Y%m%d"))
        util.info("Reconciled day {}".format(date.strftime("%Y%m%d")))
    except backoffice.PositionSourceError:
        util.warning("Data to reconcile day not found: {}\n".format(date.strftime("%Y%m%d")))
    finally:
        date=date+dayDelta

    
