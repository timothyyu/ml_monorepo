#!/usr/bin/env python

import optparse
import sys
import os
import re
import copy

from securityMasterDB import securityMaster
from parseMSPositions import morganPos
from parseMSActivity import morganActivity

def updatePosition(sid, fill, positions):
    if (sid not in positions):
        #print "SID not found: adding %s to positions" %(sid)
        positions[sid] = {} 
        positions[sid]['quantity'] = 0
        positions[sid]['cash'] = 0
        positions[sid]['symbol'] = ""

    positions[sid]['quantity'] += fill['qty']
    positions[sid]['cash']  +=  fill['netAmount']
    positions[sid]['symbol']  =  fill['symbol']

def getOfficialClose(pxdate,adjust,caxEndDate):
    prices = {} 
    tmpOutFile =  "/tmp/tmp.close.%s" % ( pxdate )
    closeType = "close" 
    if ( adjust ): closeType = "adjustedClose" 
        
    closeScriptCmd = "/apps/infra/bin/closePrice.py --region US --outfile %s --tradedate %s --caxEndDate %s --pxfields sid,cusip,%s" % ( tmpOutFile,  pxdate, caxEndDate, closeType )
    rc = os.system( closeScriptCmd )
    if ( rc ):
        sys.stderr.write("Unable to get official closing prices\n")
        sys.exit(1)
    f= open(tmpOutFile , 'r')
    for line in f:
        if ( re.search("^sid,cusip,", line)): continue
        line = line.rstrip()
        (tmpSid, tmpCusip, tmpClose ) = re.split ("," , line)
        prices[tmpSid] = float(tmpClose)
    f.close()
    os.system("/bin/rm %s" % ( tmpOutFile ) )
    return prices

## mark to official eod price; 
def calcPnl (  sodPositions, eodPositions,  sodPrices, eodPrices, sid  ):
    
    dayPnl =  0
    if ( sid not in eodPrices ) or ( sid not in sodPrices) :  return dayPnl
    if ( sid in eodPositions ) :
        dayPnl = ( float(eodPrices[sid]) *  float(eodPositions[sid]['quantity']) ) 
    if ( sid in sodPositions ):
        dayPnl = dayPnl - (  float(sodPrices[sid]) *  float(sodPositions[sid]['quantity'])  )
    if ( 'cash' in eodPositions[sid] ) :
        dayPnl += eodPositions[sid]['cash']
    
    
    return dayPnl





parser = optparse.OptionParser()
parser.add_option('--date', help='date', dest='date', action='store' )
parser.add_option('--prevdate', help='prevdate', dest='prevdate', action='store' )

parser.add_option('--dbhost', help='dbhost', dest='dbhost', action='store', default='infradb1.jc' )
parser.add_option('--dbuser', help='dbuser', dest='dbuser', action='store' , default ='tower')
parser.add_option('--dbname', help='dbname', dest='dbname', action='store', default ='securityMaster' )

parser.add_option('--debugSid', help='debugSid', dest='debugSid', action='store')

(options, args) = parser.parse_args(sys.argv)

## need to get separately since we may get into name where SOD has no position and therefore not in MS position file
sodPrices = getOfficialClose(pxdate=options.prevdate, adjust=1,caxEndDate=options.date)
eodPrices = getOfficialClose(pxdate=options.date, adjust=0,caxEndDate=options.date)

fills = {}

secMasterDB = securityMaster(dbhost=options.dbhost , dbuser=options.dbuser ,  dbname=options.dbname)
(bbCusipSidMap,bbIsinSidMap,bbSedolSidMap) = secMasterDB.getIdentifierSidMap( exchCode =   ['US' ] )

morganPositionsObj = morganPos( tradeDate = options.prevdate,  cusipSidMap = bbCusipSidMap , isinSidMap = bbIsinSidMap, sedolSidMap = bbSedolSidMap)

## really prev eod position and need to apply corp actions
sodPositions = morganPositionsObj.getPositions()
livePositions = copy.deepcopy( sodPositions )


morganActivityObj = morganActivity( tradeDate = options.date,  cusipSidMap = bbCusipSidMap )
fills = morganActivityObj.getActivity()


totalLongFillValue = 0.0 ;
totalShortFillValue = 0.0 ;

for tmpSid in fills: 
    for tmpFill in fills[tmpSid] :
        if ( float(tmpFill['netAmount']) > 0 ): totalLongFillValue += float(tmpFill['netAmount'])
        else :   totalShortFillValue +=  float(tmpFill['netAmount'])

        updatePosition ( sid = tmpSid, fill = tmpFill , positions = livePositions )

print "TOTAL FILLS: %s,%s" %(  totalLongFillValue, totalShortFillValue )

### debug
if ( options.debugSid ):
    if ( options.debugSid in sodPrices ): print sodPrices[ options.debugSid]
    if ( options.debugSid in eodPrices ): print eodPrices[ options.debugSid ]
    if ( options.debugSid in sodPositions ): print sodPositions[ options.debugSid]
    if ( options.debugSid in fills ): print fills[ options.debugSid]
    if ( options.debugSid in livePositions ): print livePositions[ options.debugSid]
    sys.exit(0)
    
totalDailyPnl = 0.0

for tmpSid in livePositions:
    dailyPnl = calcPnl( sodPositions, livePositions,  sodPrices, eodPrices ,tmpSid )
        
    tmpSym = livePositions[tmpSid]['symbol']
    if ( not tmpSym ) or ( tmpSym == "" ): tmpSym = str(tmpSid)
    totalDailyPnl += dailyPnl

    #print "%s\t%s\t\t%.2f" %( livePositions[tmpSid]['symbol'], tmpSid,  dailyPnl)
    print "%s,%.2f" %( livePositions[tmpSid]['symbol'],   dailyPnl)

print "TOTAL DAILY PNL %.2f" % ( totalDailyPnl)

    

