import config
import datetime
import os.path
import re
import util
import paramiko
import bisect

#from secIdBimap import SecIdBimap
import newdb
database = newdb.get_db()

class Position:
    def __init__(self, secid, cusip, ticker, isin, size, price):
        self.secid = secid
        self.cusip = cusip
        self.ticker = ticker
        self.isin = isin
        self.size = size
        self.price = price
        
    def __str__(self):
        return "|{}|{}|{}|{}|{}|{}".format(self.secid, self.cusip, self.ticker, self.isin, self.size, self.price)
        

class PositionSourceError(Exception):
    def __init__(self, message):
        self.message = message
        
    def __str__(self):
        return "PositionSourceError: {}".format(self.message)

class PositionSource():
    def getPositions(self, date):
        
        if type(date) is not datetime.datetime:
            raise PositionSourceError("PositionSource argument should be a datetime.date object")
        
        return None

class MorganStanleyPositions(PositionSource):
    def getPositions(self, date):
                
        PositionSource.getPositions(self, date)
                
        #Read from the morgan data source
        source = "morgan_positions"
        sourceConfig = config.load_source_config(source)
        dataPath = "{dataPath}/{localDir}/".format(dataPath=os.environ["DATA_DIR"], localDir=sourceConfig["local_dir"])
        fileRegex = "Tower_Positions\\.{}\\.0000\\.txt".format(date.strftime("%d%m%y"))
        fileRegex += r'\.[a-f0-9]{8}$'
        fileRegex = re.compile(fileRegex)
        
        #get subdirs that could contain the desired file (after the date)
        def candidateSubDir(dir):
            if not os.path.isdir(dataPath + dir):
                return False
            
            try:
                dirDate = datetime.datetime.strptime(dir, "%Y%m%d")
            except ValueError:
                return False
            
            return dirDate > date
                
        candidateSubDirs = filter(candidateSubDir, os.listdir(dataPath))
        candidateSubDirs.sort() #Sort for efficiency
        
        #Find file with positions
        positionFile = None
        for subDir in candidateSubDirs:
            
            if positionFile != None:
                break
            
            path = dataPath + subDir
            for file in os.listdir(path):
                if fileRegex.match(file):
                    positionFile = dataPath + subDir + "/" + file
                    break
        
        if positionFile == None:
            raise PositionSourceError("MorganStanleyPosition found no matching files")
        
        return self._readPositionsFromFile(positionFile)
        
    ###Some morgan files are bad and the sizes for a stock show up as two lines.
    ###Solution: add up the amounts
    def _readPositionsFromFile(self, fileName, date=None):
        positions = {} #cusip -> position
        
        with open(fileName, "r") as file:
                    
            #Valid lines start with a date
            dateReg = re.compile(r'\d{4}-\d{2}-\d{2}')
            cusipReg = re.compile(r'\w{9}')
            #sedolReg=re.compile(r'\w{7}')
            #isinReg=re.compile(r'\w{12}')
                
            for line in file:
                tokens = [token.strip('"') for token in line.strip().split(",")]
                
                try:
                    #Get date
                    if dateReg.match(tokens[0]) == None:
                        continue
        
                    #Get cusip
                    if cusipReg.match(tokens[6]) == None:
                        continue
                    else:
                        cusip = tokens[6]
                        
                    #get other identifiers. don't try too hard to verify them, they are
                    #used as backup
                    ticker = tokens[7]
                    #sedol=tokens[8]
                    isin = tokens[9]
                        
                    #Get size
                    try:
                        size = int(round(float(tokens[27])))
                    except ValueError:
                        raise PositionSourceError("MorganStanleyPosition invalid data line format")
                    
                    #Get price
                    try:
                        price = float(tokens[29])
                    except ValueError:
                        raise PositionSourceError("MorganStanleyPosition invalid data line format")
                    
                #line doesn't parse into enough tokens
                except IndexError:
                    raise PositionSourceError("MorganStanleyPosition invalid data line format")
                
                try:
                    position = positions[cusip]
                    position.size = position.size + size
                except KeyError:
                    positions[cusip] = Position(None, cusip, ticker, isin, size, price)
                        
        return positions.values()
        
class MorganStanleyPositionsTEST(PositionSource):
    def getPositions(self, date):
        PositionSource.getPositions(self, date)
                
        #Read from the morgan data source
        source = "morgan_positions"
        sourceConfig = config.load_source_config(source)
        dataPath = "{dataPath}/{localDir}/".format(dataPath=os.environ["DATA_DIR"], localDir=sourceConfig["local_dir"])
        fileRegex = "TowerResearch-NonPositionExtract\\.{}\\.{}\\.0000\\.txt".format(date.strftime("%Y%m%d"), date.strftime("%d%m%y"))
        fileRegex += r'\.[a-f0-9]{8}$'
        fileRegex = re.compile(fileRegex)
        
        #get subdirs that could contain the desired file (after the date)
        def candidateSubDir(dir):
            if not os.path.isdir(dataPath + dir):
                return False
            
            try:
                dirDate = datetime.datetime.strptime(dir, "%Y%m%d")
            except ValueError:
                return False
            
            return dirDate > date
                
        candidateSubDirs = filter(candidateSubDir, os.listdir(dataPath))
        candidateSubDirs.sort() #Sort for efficiency
        
        #Find file with positions
        positionFile = None
        for subDir in candidateSubDirs:
            
            if positionFile != None:
                break
            
            path = dataPath + subDir
            for file in os.listdir(path):
                if fileRegex.match(file):
                    positionFile = dataPath + subDir + "/" + file
                    break
        
        if positionFile == None:
            raise PositionSourceError("MorganStanleyPosition found no matching files")
        
        return self._readPositionsFromFile(positionFile)
        
    ###Some morgan files are bad and the sizes for a stock show up as two lines.
    ###Solution: add up the amounts
    def _readPositionsFromFile(self, fileName, date=None):
        positions = {} #cusip -> position
        
        with open(fileName, "r") as file:
                    
            cusipReg = re.compile(r'\w{9}')
            #sedolReg=re.compile(r'\w{7}')
            #isinReg=re.compile(r'\w{12}')
                
            for line in file:
                tokens = [token.strip(' "') for token in line.strip().split(",")]
                
                try:
                    if len(tokens) < 60:
                        continue
                            
                    #Get cusip
                    if cusipReg.match(tokens[1]) == None:
                        continue
                    else:
                        cusip = tokens[1]
                        
                    if tokens[47] != "Cash Equity":
                        continue
                        
                    #get other identifiers. don't try too hard to verify them, they are
                    #used as backup
                    ticker = tokens[2]
                    #sedol=tokens[8]
                    isin = tokens[22]
                        
                    #Get size
                    try:
                        size = int(round(float(tokens[4])))
                    except ValueError:
                        raise PositionSourceError("MorganStanleyPosition invalid data line format")
                    
                    #Get price
                    try:
                        price = float(tokens[5])
                    except ValueError:
                        raise PositionSourceError("MorganStanleyPosition invalid data line format")
                    
                #line doesn't parse into enough tokens
                except IndexError:
                    raise PositionSourceError("MorganStanleyPosition invalid data line format")
                
                try:
                    position = positions[cusip]
                    position.size = position.size + size
                except KeyError:
                    positions[cusip] = Position(None, cusip, ticker, isin, size, price)
                        
        return positions.values()
  
class OldSystemPositions(PositionSource):
    
    def getPositions(self, date):
        PositionSource.getPositions(self, date)
        sshCommand = "cd /spare/local/ase/trade; . ./env.sh; liveportfolio.py prod {}".format(date.strftime("%Y%m%d"))
        
        #connect
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(util.ParamikoIgnorePolicy())
        client.connect("asetrade1.jc", 22, "ase", "d0lemite")
        stdin, stdout, stderr = client.exec_command(sshCommand)
        data = stdout.read()
        error = stderr.read()
                
        if error != "":
            raise PositionSourceError("OldSystemPositions error finding data")
        
        return self._readPositionsFromString(data)
        
    def _readPositionsFromString(self, data, date=None):
        positions = list()
        
        tickerReg = re.compile(r"[A-Z][A-Z0-9\.]{0,4}")
        
        for line in data.split("\n"):
            tokens = line.split()
            
            if len(tokens) == 0 or not tickerReg.match(line):
                continue
                        
            ticker = tokens[0]
            
            #Get size
            try:
                size = int(tokens[3])
            except ValueError:
                raise PositionSourceError("OldSYstemPositions invalid data line format")
            
            #Get price
            try:
                price = float(tokens[4])
            except ValueError:
                raise PositionSourceError("OldSYstemPositions invalid data line format")
            
            if (size == 0):
                continue
            
            position = Position(None, "", ticker, "", size, price)
            positions.append(position)
            
        return positions
    

class NewSystemPositions(PositionSource):
    
    def getPositions(self, date):
        #for date the sod positions are in date+1
        #sodPortPath = os.environ["ROOT_DIR"] + "/run/" + os.environ["STRAT"] + "/" + str(util.exchangeTradingOffset(os.environ["PRIMARY_EXCHANGE"], date.strftime("%Y%m%d"), 1)) + "/sodPort.txt"
        sodPortPath="/apps/ase/run/useq-live/"+str(util.exchangeTradingOffset(os.environ["PRIMARY_EXCHANGE"], date.strftime("%Y%m%d"), 1)) + "/sodPort.txt"
        
        if not os.path.isfile(sodPortPath):
            raise PositionSourceError("NewSystemPositions failed to locate sodPort.txt")
        
        positions = list()
        with open(sodPortPath, "r") as file:
            #skip header
            file.readline()
            for line in file:
                if len(line) == 0: continue
                tokens = line.strip().split("|")
                secid = int(tokens[1])
                size = int(tokens[2])
                price = float(tokens[3])
                cusip = database.getXrefFromSecid("CUSIP", secid, util.convert_date_to_millis(date), "compustat_idhist")
                ticker = database.getXrefFromSecid("TIC", secid, util.convert_date_to_millis(date), "compustat_idhist")
                isin = database.getXrefFromSecid("ISIN", secid, util.convert_date_to_millis(date), "compustat_g_idhist")
                
                position = Position(secid, cusip, ticker, isin, size, price)
                positions.append(position)

                
        return positions

#Assign secIds to positions. In order of priority use (if available) CUSIP, TIC,ISIN
#Return a tuple: list of "good" positions with secids and "bad" positions without
def __assignSecIds(positions, timestamp):
    good = []
    bad = []
    for position in positions:
                       
        secid = position.secid
        if secid is None:
            secid = database.getSecidFromXref("CUSIP", position.cusip, timestamp, "compustat_idhist")
        if secid is None:
            secid = database.getSecidFromXref("TIC", position.ticker, timestamp, "compustat_idhist")
        if secid is None:
            secid = database.getSecidFromXref("ISIN", position.isin, timestamp, "compustat_idhist")
         
        if secid is not None:
            position.secid = secid
            good.append(position)
        else:
            bad.append(position)
        
    return good, bad

def reconcile(leftPositions, rightPositions, timestamp):
    
    #associate positions with secIds. Set aside positions for 
    #which no secId was found
    leftGood, leftBad = __assignSecIds(leftPositions, timestamp)
    rightGood, rightBad = __assignSecIds(rightPositions, timestamp)
    
    #sort good positions and get keys in preperation for lookups
    leftGood.sort(key=lambda x: x.secid)
    leftKeys = [x.secid for x in leftGood]
    rightGood.sort(key=lambda x: x.secid)
    rightKeys = [x.secid for x in rightGood]
    
    #prepare for lookups
    agree = [] #list of position pairs
    disagree = []#list of position pairs
    leftOnly = [] #list of positions
    rightOnly = [] #list of positions
    
    #boolean array of rightsecids successfully probed
    rightProbed = [False] * len(rightKeys)
    
    #probe right with left
    for l, secid in enumerate(leftKeys):
                
        r = bisect.bisect_left(rightKeys, secid)
        if r < len(rightKeys) and secid == rightKeys[r]: #found
            rightProbed[r] = True
            
            if leftGood[l].size == rightGood[r].size:
                agree.append((leftGood[l], rightGood[r]))
            else:
                disagree.append((leftGood[l], rightGood[r]))
            
        else: #not found
            leftOnly.append(leftGood[l])
            
    #get unprobbed on right
    for b, p in zip(rightProbed, rightGood):
        if not b:
            rightOnly.append(p)

    return agree, disagree, leftOnly, rightOnly, leftBad, rightBad

def __beautify(agree, disagree, leftOnly, rightOnly, leftBad, rightBad, timestamp):        
    grandResult = []
    
    for pair in agree + disagree:
        left = pair[0]
        right = pair[1]
        
        secid = left.secid
        
        #ticker=maps["ticker"].fromSecId(secid)
        #Temporary fix for missing tickers: trust morgans (existing ticker)
        ticker = database.getXrefFromSecid("TIC", secid, timestamp, "compustat_idhist")
        if ticker is None:
            ticker = left.ticker
        
        lsize = left.size
        rsize = right.size
        lprice = left.price
        rprice = right.price
        
        grandResult.append((ticker, secid, lsize, rsize, lprice, rprice))
        
    for unit in leftOnly:
        secid = unit.secid
        
        #ticker=maps["ticker"].fromSecId(secid)
        #Temporary fix for missing tickers: trust morgans (existing ticker)
        ticker = database.getXrefFromSecid("TIC", secid, timestamp, "compustat_idhist")
        if ticker is None:
            ticker = unit.ticker
        
        lsize = unit.size
        rsize = 0
        lprice = unit.price
        rprice = 0
        
        grandResult.append((ticker, secid, lsize, rsize, lprice, rprice))
        
    for unit in rightOnly:
        secid = unit.secid
        
        #ticker=maps["ticker"].fromSecId(secid)
        #Temporary fix for missing tickers: trust morgans (existing ticker)
        ticker = database.getXrefFromSecid("TIC", secid, timestamp, "compustat_idhist")
        if ticker is None:
            ticker = unit.ticker
        
        lsize = 0
        rsize = unit.size
        lprice = 0
        rprice = unit.price
        
        grandResult.append((ticker, secid, lsize, rsize, lprice, rprice))
        
        #sort by ticker
    grandResult.sort(key=lambda x : x[0])
    
    #minus signs 
    beauty = "\n".join(["{}|{}|{}|{}|{}|{}|{}".format(x[0], x[1], __determineDiffSign(x[2], x[3]), x[2], x[3], x[4], x[5]) for x in grandResult])
    
    for p in leftBad:
        beauty += "\n{}|{}".format("#LBAD", p)
    for p in rightBad:
        beauty += ("\n{}|{}".format("#RBAD", p))
        
    return beauty

def __determineDiffSign(left, right):
    
    minus = "--"
    plus = "++"
    zero = "00"
    
    if (left - right) < 0:
        return minus
    elif left - right > 0:
        return plus
    else:
        return zero
    
#    if left*right>=0:
#        if abs(left)<abs(right):
#            return minus
#        elif abs(left)>abs(right):
#            return plus
#        else:
#            return zero
#    elif left*right<0:
#        if left<0:
#            return minus
#        else:
#            return plus


#def getIdMaps(date):
#    maps={}
#    maps["cusip"]=SecIdBimap(1,util.convert_date_to_millis(date))
#    maps["ticker"]=SecIdBimap(2,util.convert_date_to_millis(date))
#    maps["isin"]=SecIdBimap(4,util.convert_date_to_millis(date))
#    
#    return maps

def singleDayReconcile(date, old):
    morgan = MorganStanleyPositions()
    morganPositions = morgan.getPositions(date)
    
    if old: us = OldSystemPositions()
    else: us = NewSystemPositions()
    usPositions = us.getPositions(date)
    
    #maps=getIdMaps(date)
    result = reconcile(usPositions, morganPositions, util.convert_date_to_millis(date))

    return __beautify(*result, timestamp=util.convert_date_to_millis(date))
    
    
