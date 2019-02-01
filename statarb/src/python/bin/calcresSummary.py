#!/usr/bin/env python
import os
import os.path
import subprocess
import argparse
import util

def calcresStats(infile,outfile,oldSystem):
    print "Processing {} into {}".format(infile, outfile)
    rCode=os.environ["R_DIR"]+"/models.R"
    rcommand="Rscript -e \"source('{}'); calcres<-load.calcres{}('{}'); calcstats<-calcres.stats(calcres); write.table(calcstats,file='{}',sep='|',col.names=FALSE,row.names=FALSE,quote=FALSE)\"".format(rCode,".old" if oldSystem is True else "",infile,outfile)
    util.log(rcommand)
    p=subprocess.Popen(rcommand,env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    util.info(p.stdout.read())
    util.info(p.stderr.read())
    p.wait()
    
def forecastStats(infile,outfile,configfile):
    print "Processing {} into {}".format(infile, outfile)
    rCode=os.environ["R_DIR"]+"/models.R"
    rcommand="Rscript -e \"source('{}'); forecasts<-load.forecasts('{}','{}'); stats<-forecast.stats(forecasts); write.table(stats,file='{}',sep='|',col.names=TRUE,row.names=FALSE,quote=FALSE)\"".format(rCode,configfile,infile,outfile)
    util.log(rcommand)
    p=subprocess.Popen(rcommand,env=os.environ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    util.info(p.stdout.read())
    util.info(p.stderr.read())
    p.wait()
    
if __name__=="__main__":
    util.check_include()
    
    parser = argparse.ArgumentParser(description='G')
    parser.add_argument("--calcresStats",action="store_const",const=True,dest="calcresStats",default=False)
    parser.add_argument("--forecastStats",action="store_const",const=True,dest="forecastStats",default=False)
    parser.add_argument("--mode",action="store",dest="mode")        
    parser.add_argument("--strat",action="store",dest="strat",default=os.environ["STRAT"])
    parser.add_argument("--date",action="store",dest="date",default=os.environ["DATE"])
    parser.add_argument("--infile",action="store",dest="infile",default=None)
    parser.add_argument("--outfile",action="store",dest="outfile",default=None)
    parser.add_argument("--configfile",action="store",dest="configfile",default="/".join((os.environ["CONFIG_DIR"],"opt.prod.cfg")))
    parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
    
    args = parser.parse_args()
    if args.debug:
        util.set_debug()
    else:
        util.set_log_file()
    
    if args.calcresStats:
        if args.infile is not None and args.outfile is not None:
            calcresStats(args.infile,args.outfile,True if args.mode=="old" else False)
            exit(0)

        if args.mode == "dailysim":
            inpath="/".join((os.environ["ROOT_DIR"],"research",args.strat,"dailysim",args.date,"calcres"))
            outpath="/".join((os.environ["ROOT_DIR"],"reports",args.strat,"dailysim",args.date))
        elif args.mode == "live":
            inpath="/".join((os.environ["RUN_DIR"],"calcres"))
            outpath="/".join((os.environ["ROOT_DIR"],"reports",args.strat,"dailylive",args.date))
        elif args.mode == "old":
            inpath="/".join((os.environ["RUN_DIR"],"oldsystem","calcres"))
            outpath="/".join((os.environ["ROOT_DIR"],"reports",args.strat,"dailylive",args.date))
        else:
            print "Unknown mode!"
            exit(1)
        
        #create the outpath if it doesn't exist
        try:
            os.makedirs(outpath)
        except:
            pass
        
        util.info("Looking for calcres files in {}".format(inpath))
        infiles = os.popen("ls -rt {}/calcres.*.txt.gz | tail -1".format(inpath)).readlines()
        for infile in [x.strip() for x in infiles]:
            outfile = infile[infile.rindex("/"):].split(".")
            if args.mode != "old": outfile.insert(1,"stats")
            else: outfile.insert(1,"old.stats")
            outfile=".".join(outfile[:-1])
            outfile = outpath+"/"+outfile
            calcresStats(infile, outfile,True if args.mode=="old" else False)
            util.cat(outfile)
    
    if args.forecastStats:
        if args.infile is not None and args.outfile is not None:
            forecastStats(args.infile,args.outfile,args.configfile)
            exit(0)

        if args.mode == "dailysim":
            inpath="/".join((os.environ["ROOT_DIR"],"research",args.strat,"dailysim",args.date,"calcres"))
            outpath="/".join((os.environ["ROOT_DIR"],"reports",args.strat,"dailysim",args.date))
        elif args.mode == "live":
            inpath="/".join((os.environ["RUN_DIR"],"calcres"))
            outpath="/".join((os.environ["ROOT_DIR"],"reports",args.strat,"dailylive",args.date))
        else:
            print "Unknown mode!"
            exit(1)

        #create the outpath if it doesn't exist
        try:
            os.makedirs(outpath)
        except:
            pass

        util.info("Looking for calcres files in {}".format(inpath))
        infiles = os.popen("ls -rt {}/calcres.*.txt.gz | tail -1".format(inpath)).readlines()
        for infile in [x.strip() for x in infiles]:
            outfile = infile[infile.rindex("/"):].split(".")
            outfile[0:1] = ["forecast","stats"]
            outfile=".".join(outfile[:-1])
            outfile = outpath+"/"+outfile
            forecastStats(infile, outfile, args.configfile)
            util.cat(outfile)
