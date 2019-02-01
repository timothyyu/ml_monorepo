#!/usr/bin/env python
import subprocess
import util
import datetime
import os
import argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bars",action="store_const",const=True,dest="bars",default=False)
    parser.add_argument("--superbars",action="store_const",const=True,dest="superbars",default=False)
    args = parser.parse_args()
    
    assert (args.bars != args.superbars) and (args.bars or args.superbars) 
    
    #get exchange open-close
    nowMillis=util.now()
    nowDate=datetime.datetime.utcnow().strftime("%Y%m%d")
    command="{}/get_exch_open_close.sh NYSE {}".format(os.environ["BIN_DIR"],nowDate)
    p=subprocess.Popen(command,env=os.environ,shell=True,stdout=subprocess.PIPE)
    output=p.stdout.read()
    p.wait()
    
    ex_open=long(output.split("|")[0])
    ex_close=long(output.split("|")[1])
    
    #exchange is closed, or before 9.36am
    if ex_open==0 or ex_close==0 or nowMillis<ex_open+6L*60L*1000L or nowMillis>=ex_close:
        exit(0)
    
    #read the bar file
    fname = "all.txt.live" if args.bars else "bars_v2.txt.live"
    file=open("{}/bars/{}/{}".format(os.environ["DATA_DIR"],nowDate, fname),"r")
    bars=file.readlines()
    file.close()
    
    close_ts=0L;
    for bar in bars:
        tokens=bar.strip().split("|")
        ts=long(tokens[2])
        close_ts=max(close_ts,ts)
    
    lag=(nowMillis-close_ts)
    
    if lag>6*60*1000:
        if close_ts>0:
            msg="WARNING: We have not received new {} in {:.1f} minutes!".format("bars" if args.bars else "superbars", lag/60.0/1000.0)
        else:
            msg="WARNING: We have not received new {} in, like, forever!".format("bars" if args.bars else "superbars")
        util.email(msg, "You heard me. Go fix this!")
    
