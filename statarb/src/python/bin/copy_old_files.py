#!/usr/bin/env python
import config
from data_sources.sftp_source import SFTPSource
import argparse
import util
import datetime
import os

if __name__=="__main__":
    util.check_include()
    
    parser = argparse.ArgumentParser(description='Generate backoffice reconciliation report')
    parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
    parser.add_argument('--from',action="store",dest="fromDate")
    parser.add_argument('--to',action="store",dest="toDate")
    parser.add_argument('--day',action="store",dest="singleDate")
    parser.add_argument('--today',action="store_const",const=True,dest="today",default=False)
    parser.add_argument("--all",action="store_const",const=True,dest="all",default=False)
    parser.add_argument("--location",action="store",dest="location",default="/apps/ase/run/useq-live")
    parser.add_argument("--fills",action="store_const",const=True,dest="fills",default=False)
    parser.add_argument("--calcres",action="store_const",const=True,dest="calcres",default=False)
    parser.add_argument("--trades",action="store_const",const=True,dest="trades",default=False)
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
    elif args.all is True:
        fromDate=datetime.datetime.strptime("20090910","%Y%m%d")
        toDate=datetime.datetime.utcnow()
        toDate=datetime.datetime.strptime(toDate.strftime("%Y%m%d"),"%Y%m%d") #Get only date
        toDate+=dayDelta
    else:
        parser.print_help(util.LOGFILE)
        exit(1)
        
    #load a relevant config file to get password
    sconfig=config.load_source_config("htb")
    source=SFTPSource(sconfig["host"], sconfig["user"], sconfig["pass"])

    date=fromDate
    while date<toDate:
        try: 
            if args.fills:
                remoteDir="/spare/local/ase/trade/run/live-prod/"+date.strftime("%Y/%m/%d")
                localDir=args.location+"/"+date.strftime("%Y%m%d")
                source.cwd(remoteDir)
                files=source.list(r".*fills.txt")
                for file in files:
                    source.copy(remoteDir+"/"+file[0], localDir+"/"+"old."+file[0])
            if args.calcres:
                remoteDir="/spare/local/ase/trade/run/live-prod/"+date.strftime("%Y/%m/%d")+"/calcres"
                localDir=args.location+"/"+date.strftime("%Y%m%d")+"/oldsystem/calcres"
                source.cwd(remoteDir)
                files=source.list(r".*gz$")
                files=sorted(files,key=lambda x : x[0])
                if len(files)>0:
                    file=files[-1]
                    try:
                        os.makedirs(localDir)
                    except Exception, e:
                        util.warning(e)
                    source.copy(remoteDir+"/"+file[0], localDir+"/"+file[0])
            if args.trades:
                remoteDir="/spare/local/ase/trade/run/live-prod/"+date.strftime("%Y/%m/%d")+"/trade"
                localDir=args.location+"/"+date.strftime("%Y%m%d")+"/oldsystem/trade"
                source.cwd(remoteDir)
                files=source.list(r".*txt$")
                files=sorted(files,key=lambda x : x[0])
                if len(files)>0:
                    file=files[-1]
                    try:
                        os.makedirs(localDir)
                    except Exception, e:
                        util.warning(e)
                    source.copy(remoteDir+"/"+file[0], localDir+"/"+file[0])
        except Exception,e:
            util.warning(e)
            pass
        finally:
            date=date+dayDelta
