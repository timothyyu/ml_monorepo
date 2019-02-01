#!/usr/bin/env python
import config
from data_sources.sftp_source import SFTPSource
import argparse
import util
import datetime
import os
import shutil
import re
import pytz
import sys
import time

MAX_TIMESTAMP_DIFF = 25 # in milliseconds

def getTicker2secid(file):
    res = dict()
    with open(file, "r") as f:
        for line in f:
            tokens = line.strip().split("|")
            secid = tokens[1]
            ticker = tokens[0]
            res[ticker] = secid
    return res

def getLogs(day, pattern):
    tmpDir = util.tmpdir()
    tmpFilepath = tmpDir + "/temp.temp"
    data = []
    #parse the config file to get the exec servers
    cfg = config.load_trade_config(os.environ['CONFIG_DIR'] + '/exec.conf')
    for host, port in cfg["servers"]:
        src = SFTPSource(host, "ase", None)
        try:
            if day <= "20110802":
                #get the exec number
                m = re.match(r"exectrade(\d).jc", host)
                if m is None:
                    raise Exception("Failed to parse host name to get its number for historical data. host={}".format(host))
                else:
                    number = m.group(1)
                remoteDir = os.path.join("/spare/local/guillotine_old.20110802", "log", "rts1_{}.{}".format(number, day))
            else:
                remoteDir = os.path.join(os.environ["EXEC_ROOT_DIR"], "log", day)
            src.cwd(remoteDir)
            files = src.list(pattern)
            if len(files) != 1:
                raise Exception("Found {} {} files in {}:{}".format(len(files), pattern, host, remoteDir))
            src.copy(remoteDir + "/" + files[0][0], tmpFilepath)
            with open(tmpFilepath, "r") as file:
                for line in file:
                    data.append(line.strip())
        except Exception, e:
            util.warning(str(e))
    
    shutil.rmtree(tmpDir)
    return data

def parseCostLog(data):
    res = []
    eastern =  pytz.timezone('US/Eastern')
    for line in data:
        tokens = line.strip().split()
        if tokens[3] != "REQ": continue
        long_ts = (tokens[0]+" "+tokens[1])[0:-7]
        long_ts = datetime.datetime.strptime(long_ts, "%Y/%m/%d %H:%M:%S")
        long_ts = eastern.localize(long_ts)
        ts = util.convert_date_to_millis(long_ts)
        
        m = re.match(r"\[orderID: (.*?)\]", tokens[-2]+" "+tokens[-1])
        if m is None:
            util.warning("Failed to parse REQ line: {}".format(line))
            continue
        orderid = long(m.group(1))
        if orderid > 0:
            res.append(str(orderid) +"|"+ str(ts))
            
    return res
            
def parseFills(ticker2secid, data):
    res = ["type|date|strat|seqnum|secid|ticker|ts_received|ts_exchange|shares|price|exchange|liquidity|orderID|tactic"]
    seqnum = 0
    for line in data:
        tokens = line.strip().split("|")
        if tokens[0] != "F": continue
        seqnum += 1
        d={}
        d["date"]=tokens[1]
        d["seqnum"] = str(seqnum)
        d["ticker"] = tokens[2]
        d["secid"] = ticker2secid[d["ticker"]]
        d["ts"] = tokens[3]
        d["shares"] = tokens[4]
        d["price"] =tokens[5]
        d["exch"]=tokens[6]
        d["liq"]=tokens[7]
        d["orderid"]=tokens[8]
        d["tactic"]=tokens[9]
        
        #UNKNOWN('K'), JOIN_QUEUE('J'), FLW_LEADER('L'), STEP_UP_L1('T'), CROSS('X'), TAKE_INVISIBLE('I'), 
        #FLW_SOB('S'), MKT_ON_CLOSE('M'), EXEC_UNKNOWN('U');
        d["tactic"] = getTacticChar(d["tactic"])
        res.append("F|{date}|1|{seqnum}|{secid}|{ticker}|{ts}|{ts}|{shares}|{price}|{exch}|{liq}|{orderid}".format(**d))
        
    return res

def getTacticChar(tactic):
    if tactic == "UNKNOWN": retVal="K"
    elif tactic == "JOIN_QUEUE": retVal ="J"
    elif tactic == "FLW_LEADER": retVal ="L"
    elif tactic == "STEP_UP_L1": retVal ="T"
    elif tactic == "CROSS": retVal ="X"
    elif tactic == "TAKE_INVISIBLE": retVal ="I"
    elif tactic == "FLW_SOB": retVal ="S"
    elif tactic == "MKT_ON_CLOSE": retVal ="M"
    elif tactic == "EXEC_UNKNOWN": retVal ="U"
    else: raise Exception("We should have never reached this line. Tactic responsible is {}".format(tactic))
    return retVal

def parseValue(input):
    if util.isInteger(input):
        return int(input)
    elif util.isFloat(input):
        return float(input)
    elif input[0] == '(':
        temp = input[1:-1].split(',')
        values = map(lambda x: parseValue(x), temp)
        return values
    else:
        return input

def parseExecLine(line):
    retVal = {}
    for item in line:
        fields = str(item).split(":")
        if len(fields) > 1:
            retVal[fields[0]] = parseValue(fields[1])
    return retVal

def getOrderidTacticInExecLine(seqnum, seqnum2Info, execLineValues):
    if seqnum not in seqnum2Info:
        util.warning('Did not find an entry in seqnum2Info for seqnum {}'.format(seqnum))
        return (-1,'K')

    for item in seqnum2Info[seqnum]:
        if item['ticker'] == execLineValues['sec']:
            return (item['orderid'], item['tactic'])

    util.warning('Did not find any orderid for the seqnum {}. Perhaps a manual order?'.format(seqnum))
    return (-1,'K')

def getLiquidity(fee, exchange):
    retVal = 'O'
    if fee == 65: retVal = 'A'
    elif fee == 82: retVal = 'R'
    elif fee == 50: retVal = 'A'
    elif fee == 49: retVal = 'R'
    elif fee == 78: retVal = 'R'
    # Currently we associate ARCA (X) => O, NYSE 0 (routed) => O, NYSE 54 (MOC) => O
    return retVal

def getSeqnumOrderidMaps(datestr):
    # report.log: 2011/08/11 10:51:58.243778 INFO RF JOIN_QUEUE:-100 NYSE 53159918007837 TS seqnum: 577009417
    data = getLogs(datestr, r"report\.log")
    seqnum2Info = {}
    orderid2Info = {}
    for line in data:
        tokens = line.strip().split()
        ticker = tokens[3]
        tacticChar = getTacticChar(tokens[4].split(':')[0])
        exchField = 5
        if len(tokens[4].split(':')) == 1:
            exchField = 6
#        tactic = tokens[qtyField].split(':')[0]
#        tacticChar = getTacticChar(tactic)
        exch = tokens[exchField]
        try:
            orderid = long(tokens[exchField+1])
        except ValueError:
            print line
            sys.exit(-1)
        try:
            seqnum = int(tokens[exchField+4])
        except ValueError:
            print line
            sys.exit(-1)
        if orderid not in orderid2Info:
            orderid2Info[orderid] = []
        orderid2Info[orderid].append({'ticker':ticker, 'tactic':tacticChar, 'exch':exch, 'seqnum':seqnum})
        if seqnum not in seqnum2Info:
            seqnum2Info[seqnum] = []
        seqnum2Info[seqnum].append({'ticker':ticker, 'tactic':tacticChar, 'exch':exch, 'orderid':orderid})
#    util.info('Returning from getSeqnumOrderidMaps')
    return (seqnum2Info, orderid2Info)

def readInfraExecLogs(datestr):
    infraLogDir = os.environ['RUN_DIR'] + '/../' + datestr + '/infraExecs'
    (out,err) = util.shellExecute('scp -r infrarack1.jc:/spare/local/ase/' + datestr + ' ' + infraLogDir)
    (out,err) = util.shellExecute('gunzip ' + infraLogDir + '/*')   
    files = os.listdir(infraLogDir)
    if len(files) < 4:
        raise Exception("There are less than 4 files for executions in " + infraLogDir)

    execFills = []
    for file in files:
        fileObj = open(infraLogDir + '/' + file, 'r')
        execFills += [line.strip().split() for line in fileObj]
        fileObj.close()

    for item in execFills:
        execTime = datetime.datetime.strptime(datestr + ' ' + item[0], "%Y%m%d %H:%M:%S.%f")
        item[0] = long(time.mktime(execTime.timetuple())*1000 + round(execTime.microsecond/1000.0))

    execFills.sort(key=lambda x:x[0])
#    util.info('Returning from readInfraExecLogs')
    return execFills

def readOurFillsFile(datestr):
    ourFillsFilename = os.environ['RUN_DIR'] + '/../' + datestr + '/fills.' + datestr + '.txt'
    ourFillsFile = open(ourFillsFilename, 'r')
    fillsLines = util.csvdict(ourFillsFile)
    orderid2fills = {}
    for line in fillsLines:
        # type|date|strat|seqnum|secid|ticker|ts_received|ts_exchange|shares|price|exchange|liquidity|orderID|tactic
        orderid = long(line['orderID'])
        fillIndex = int(line['seqnum'])
        ts_exchange = long(line['ts_exchange'])
        if orderid not in orderid2fills:
            orderid2fills[orderid] = []
        orderid2fills[orderid].append({'fillIndex': fillIndex, 'secid': int(line['secid']), 'ticker': line['ticker'], 
            'ts_received': long(line['ts_received']), 'ts_exchange': ts_exchange, 'qty': int(line['shares']), 
            'price': float(line['price']), 'exch': line['exchange'], 'liq': line['liquidity'], 'orderid':orderid,
            'tactic': line['tactic'].strip(), 'matched': False})
    
#    util.info('Returning from readOurFillsFile')
    return orderid2fills

def getOrderid2exec(execFills, seqnum2Info):
    # GVNOTE: Check what happens when we get a fill for an orderid = -1/-2
    orderid2exec = {}
    count = 0
    for item in execFills:
        count += 1
        item.append(count)
        if item[1] != 'EXEC':
            util.warning('Found line in infra exec log that does not correspond to execution: ' + str(item))
            continue
        values = parseExecLine(item)
        seqnum = values['ref'][1]
        (orderid, tactic) = getOrderidTacticInExecLine(seqnum, seqnum2Info, values)
        if orderid == -1:
            continue
        qty = values['qty']
        if values['way'] != 'BUY': 
            qty = -1*qty
        if orderid not in orderid2exec:
            orderid2exec[orderid] = []
        liq = getLiquidity(values['fee'], values['ven'])
        orderid2exec[orderid].append({'timestamp':item[0], 'seqnum':seqnum, 'ticker':values['sec'], 'qty':qty, 
            'price':values['prc'], 'exch':values['ven'], 'liq':liq, 'index':count, 'tactic':tactic})

#    util.info("Returning from getOrderid2exec")
    return orderid2exec

def associateOrderidToExecFills(execFills, seqnum2Info):
    processedExecFills = []
    count = 0
    for item in execFills:
        count += 1
        if item[1] != 'EXEC':
            util.warning('Found line in infra exec log that does not correspond to execution: ' + str(item))
            continue
        values = parseExecLine(item)
        seqnum = values['ref'][1]
        (orderid,tactic) = getOrderidTacticInExecLine(seqnum, seqnum2Info, values)
        qty = values['qty']
        if values['way'] != 'BUY': 
            qty = -1*qty
        liq = getLiquidity(values['fee'], values['ven'])
        if values['ven'] == 'LIME_NYSE':
            values['ven'] = 'NYSE'
        if values['ref'][0] == 'RTSBOS':
            values['ven'] = 'BX'
        processedExecFills.append({'timestamp':item[0], 'seqnum':seqnum, 'ticker':values['sec'], 'qty':qty, 
            'price':values['prc'], 'exch':values['ven'], 'liq':liq, 'index':count, 'orderid':orderid, 'tactic':tactic})

#    util.info("Returning from associateOrderidToExecFills")
    return processedExecFills

def matchFill(execFill, ourOrderidFills, maxTimestampDiff):
    for ii in range(len(ourOrderidFills)):
        if ourOrderidFills[ii]['matched']: continue
        if ourOrderidFills[ii]['ticker'] != execFill['ticker']: continue
        if ourOrderidFills[ii]['qty'] != execFill['qty']: continue
        if abs(ourOrderidFills[ii]['price'] - execFill['price']) > 0.001: continue
        if ourOrderidFills[ii]['exch'] != execFill['exch']: continue
        if ourOrderidFills[ii]['liq'] != execFill['liq']: continue
        if abs(ourOrderidFills[ii]['ts_exchange'] - execFill['timestamp']) > maxTimestampDiff: 
            continue
        ourOrderidFills[ii]['matched'] = True
        return ii

    return -1

def doInfraRecon(ticker2secid, datestr):
    (seqnum2Info, orderid2Info) = getSeqnumOrderidMaps(datestr)
    execFills = readInfraExecLogs(datestr)
    processedExecFills = associateOrderidToExecFills(execFills, seqnum2Info)
    orderid2fills = readOurFillsFile(datestr)

    retVal = ["type|date|strat|seqnum|secid|ticker|ts_received|ts_exchange|shares|price|exchange|liquidity|orderID|tactic"]
    seqnum = 0
    missingFills = []
    for eFill in processedExecFills:
        seqnum += 1
        orderid = eFill['orderid']
        if orderid not in orderid2fills:
            matchIndex = -1
        else:
            matchIndex = matchFill(eFill, orderid2fills[orderid], MAX_TIMESTAMP_DIFF)
        if matchIndex < 0:
            #util.warning('Did not find a match. Creating missing fill: ' + str(eFill))
            missingFills.append(eFill)
            # add the fill
            retVal.append("F|{date}|1|{seqnum}|{secid}|{ticker}|{ts}|{ts}|{qty}|{price}|{exch}|{liq}|{orderid}|{tactic}".format(
              date=datestr, seqnum=seqnum, secid=ticker2secid[eFill['ticker']], ticker=eFill['ticker'], 
              ts=eFill['timestamp'], qty=eFill['qty'], price=eFill['price'], exch=eFill['exch'], liq=eFill['liq'], 
              orderid=eFill['orderid'], tactic=eFill['tactic']))
            continue
        matchedFill = orderid2fills[orderid][matchIndex]
        matchedFill['date'] = datestr
        matchedFill['seqnum'] = seqnum
        retVal.append("F|{date}|1|{seqnum}|{secid}|{ticker}|{ts_received}|{ts_exchange}|{qty}|{price}|{exch}|{liq}|{orderid}|{tactic}".format(**matchedFill))

    nDelayedFills = 0
    leftOverMissingFills = []
    for eFill in missingFills:
        orderid = eFill['orderid']
        if orderid not in orderid2fills:
            matchIndex = -1
        else:
            matchIndex = matchFill(eFill, orderid2fills[orderid], 1000)
        if matchIndex < 0:
            #util.warning('Did not find a match. Creating missing fill: ' + str(eFill))
            leftOverMissingFills.append(eFill)
        else:
            nDelayedFills += 1
 
    util.info('Substituted timestamps for {} fills, since they had a delayed timestamp.'.format(nDelayedFills))

    nSuperDelayedFills = 0
    actualMissingFills = 0
    for eFill in leftOverMissingFills:
        orderid = eFill['orderid']
        if orderid not in orderid2fills:
            matchIndex = -1
        else:
            matchIndex = matchFill(eFill, orderid2fills[orderid], 3000)
        if matchIndex < 0:
            util.warning('Did not find a match. Creating missing fill: ' + str(eFill))
            actualMissingFills += 1
        else:
            nSuperDelayedFills += 1
 
    util.info('Substituted timestamps for {} fills, since they had a delayed timestamp of over 1 second.'.format(nSuperDelayedFills))
    util.info('Actual missing fills = {}'.format(actualMissingFills))

    for orderid in orderid2fills:
        for fill in orderid2fills[orderid]:
            if fill['matched'] != True:
                util.warning("Could not match fill: " + str(fill))
    return retVal

if __name__=="__main__":
    util.check_include()
    
    parser = argparse.ArgumentParser(description='Generate missing fills')
    parser.add_argument('-d',action="store_const",const=True,dest="debug",default=False)
    parser.add_argument('--from',action="store",dest="fromDate")
    parser.add_argument('--to',action="store",dest="toDate")
    parser.add_argument('--day',action="store",dest="singleDate")
    parser.add_argument('--today',action="store_const",const=True,dest="today",default=False)
    parser.add_argument("--location",action="store",dest="location",default=os.path.join(os.environ["ROOT_DIR"], "run", os.environ["STRAT"]))
    parser.add_argument("--costlog",action="store_const",const=True,dest="costlog",default=False)
    parser.add_argument("--fills",action="store_const",const=True,dest="fills",default=False)
    parser.add_argument("--infraRecon",action="store_const",const=True,dest="infraRecon",default=False)
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
        
    date=fromDate
    while date<toDate:
        datestr = date.strftime("%Y%m%d")
        try: 
            if args.costlog:
                data = getLogs(datestr, r"cost\.log")
                res = parseCostLog(data)
                if len(res) == 0: continue
                with open(os.path.join(args.location, datestr, "exec_order_ts.txt"), "w") as outfile:
                    outfile.write("\n".join(res))
                    outfile.write("\n")
            if args.fills:
                data = getLogs(datestr, r"fills\.txt")
                ticker2secid = getTicker2secid(os.path.join(args.location, datestr, "tickers.txt"))
                res = parseFills(ticker2secid, data)
                with open(os.path.join(args.location, datestr, "fills.{}.txt.tmp".format(datestr)), "w") as outfile:
                    outfile.write("\n".join(res))
                    outfile.write("\n")
            if args.infraRecon:
                ticker2secid = getTicker2secid(os.path.join(args.location, datestr, "tickers.txt"))
                res = doInfraRecon(ticker2secid, datestr)
                with open(os.path.join(args.location, datestr, "fills.{}.txt.tmp".format(datestr)), "w") as outfile:
                    outfile.write("\n".join(res))
                    outfile.write("\n")
        except Exception,e:
            util.warning(e)
            pass
        finally:
            date=date+dayDelta
