import util
import httplib
import datetime
import shutil
import os
import re
import hashlib
import cPickle

from file_source import FileSource
import BeautifulSoup

class OliSource(FileSource):
    def __init__(self):
        self.__tmpDirs = []

    def cwd(self, remote_dir):
        if remote_dir is None or remote_dir == "" or remote_dir == "/":
            lastFile = os.environ["SCRAP_DIR"] + "/oli_buybacks.last"
            try:
                lastDataMd5 = cPickle.load(open(lastFile, 'rb'))
            except IOError:
                lastDataMd5 = None
            # Grab data
            data = _getBuybacks2()
            if data is None:
                self._remote_dir = None
                util.error("Failed to load web page")
                return
            
            if len(data) == 0:
                util.error("Failed to read any data. Go and check if the parser is still valid")
    
            m = hashlib.md5()
            m.update(str(data))
            dataMd5 = m.digest()
            if (lastDataMd5 is not None and lastDataMd5 == dataMd5):
                self._remote_dir = None
                return
            # Save data to temp dir
            tempdir = util.tmpdir()
            f = open("%s/%s.txt" % (tempdir, datetime.datetime.now().strftime("%Y%m%d")), "w")
            for row in data:
                try:
                    f.write(("\t".join(row) + "\n").encode('ascii', 'ignore'))
                except:
                    print row
                    raise
            f.close()
            self._remote_dir = tempdir
            self.__tmpDirs.append(tempdir)
            cPickle.dump(dataMd5, open(lastFile, 'wb'))
        else:
             # Grab data
            data = _getBuybacks2(remote_dir)
            if data is None:
                self._remote_dir = None
                return
            # Save data to temp dir
            tempdir = util.tmpdir()
            f = open("%s/%s.txt" % (tempdir, datetime.datetime.now().strftime("%Y%m%d")), "w")
            for row in data:
                try:
                    f.write(("\t".join(row) + "\n").encode('ascii', 'ignore'))
                except:
                    print row
                    raise
            f.close()
            self._remote_dir = tempdir
            self.__tmpDirs.append(tempdir)
            
    def list(self, regex):
        if self._remote_dir is None:
            return []
        try:
            result = os.popen("ls -l %s 2>/dev/null" % (self._remote_dir)).readlines()
        except AttributeError:
            # If self._remote_dir is not set return an empty result
            return []
        if (result[0].find("total ", 0) != -1):
            del result[0]
        return self._parse_ls(result, regex)
            
    def __del__(self):
        for dir in self.__tmpDirs:
            try:
                shutil.rmtree(dir)
            except AttributeError:
                pass
        

def _getBuybackPage(remoteDir=""):
    conn = httplib.HTTPConnection(r"www.theonlineinvestor.com")
    conn.request("GET", r"/buybacks" + remoteDir)
    response = conn.getresponse()
    
    if response.status != 200:
        return None
    else:
        return response.read()
    
def _getBuybacks1(remoteDir=""):
    dateRegex = re.compile(r'<td colspan="4" bgcolor="#cccccc">.*?<font face="sans-serif, Arial, Helvetica" size="2">.*?(?P<dayName>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?: |&nbsp;)(?P<month>\d+?)/(?P<day>\d+?)</font>')
    #bbRegex=re.compile(r'<tr><td><p><font size="2">(.*?)</font></p></td><td>(?:<font size="2">)?(?:<p align="left">)?(?:<font size="2">)?(?P<ticker>.*?)(?:</font>)?(?:</p>)?(?:</font>)?</td><td><font size="2">(.*?)</font></td><td><font size="2">(.*?)</font></td></tr>')
    bbRegex = re.compile(r'<tr><td>(?:.*?)<font size="2">(?P<name>.*?)</font>(?:.*?)</td><td>(?:.*?)<font size="2">(?P<ticker>.*?)</font>(?:.*?)</td><td>(?:.*?)<font size="2">(?P<amount>.*?)</font>(?:.*?)</td>(<td>(?:.*?)<font size="2">(?P<notes>.*?)</font>(?:.*?)</td>)?</tr>')
    now = datetime.datetime.now()
    
    #split at -. first part is the remotedir, second the year associated with it
    remoteDirTokens = remoteDir.split("-")
    if len(remoteDirTokens) == 1:
        year = now.strftime("%Y")
    else:
        year = remoteDirTokens[1]
    
    page = _getBuybackPage(remoteDirTokens[0])
    if page is None:
        return None
    
    data = []
    dateMatches = []
    dateMatches.extend(dateRegex.finditer(page))        
    n = len(dateMatches)
    for i in range(0, n):
        start = dateMatches[i].start(0)
        end = dateMatches[i + 1].start(0) if i < n - 1 else len(page)
                
        #assemble date
        month = dateMatches[i].group("month")
        if len(month) == 1: month = "0" + month
        day = dateMatches[i].group("day")
        if len(day) == 1: day = "0" + day
        date = year + month + day
        
        #I expect problems around new years, in case the website does not update their current webpage prompty, i.e.,
        #last years results will be on the page, but we will use the current year (e.g. 2011). As a sanity check
        #make sure that the date is not a future date.
        if (datetime.datetime.strptime(date, "%Y%m%d") - now) > datetime.timedelta(days=1):
            continue
        
        bbs = []
        bbs.extend(bbRegex.finditer(page[start:end]))
        for bb in bbs:
            ticker = re.sub("<.*?>|&nbsp;", "", bb.group("ticker"))
            
            amount = re.sub("<.*?>", "", bb.group("amount"))
            amount = re.sub("&nbsp;", " ", amount)
            amount = re.sub("&amp;", "&", amount)
            
            notes = bb.group("notes")
            if notes is None:
                notes = ""
            else:
                notes = re.sub("<.*?>", "", notes)
                notes = re.sub("&nbsp;", " ", notes)
                notes = re.sub("&quot;", '"', notes)
                notes = re.sub("&amp;", '"', notes)
                
            data.append((date, ticker, amount + " | " + notes))
            
    return data

def _getBuybacks2(remoteDir=""):
    #split at -. first part is the remotedir, second the year associated with it
    remoteDirTokens = remoteDir.split("-")    
    page = _getBuybackPage(remoteDirTokens[0])
    if page is None:
        return None
    
    soup = BeautifulSoup.BeautifulSoup(page)    
    #print soup.prettify();
    #find table header
    header = soup.find('tr', style=re.compile(r"background-color.*ccccff.*height.*20px"))
    if header is None:
        return []
    
    data=[]
    for row in header.findNextSiblings('tr'):
        cells = row.findAll('font', size="2")
        if len(cells) < 4:
            continue
        
        #get date
        try:
            date = cells[0].string.strip()
            date = datetime.datetime.strptime(date, "%m/%d/%Y")
            date = date.strftime("%Y%m%d")
        except:
            continue
        
        ticker = cells[2].string.strip()
        ammount = cells[3].string.strip()
        notes = "" if (len(cells) <= 4 or cells[4].string is None) else cells[4].string.strip()
        ammount = ammount + " | " + notes if len(notes) > 0 else ammount
        ammount = ammount.replace(r"&nbsp;", "")
        
        data.append((date, ticker, ammount))
    
    return data

def _getBuybacks3(remoteDir=""):
    #split at -. first part is the remotedir, second the year associated with it
    remoteDirTokens = remoteDir.split("-")    
    page = _getBuybackPage(remoteDirTokens[0])
    if page is None:
        return None
    
    soup = BeautifulSoup.BeautifulSoup(page)    
    print soup.prettify();
    #find table header
    header = soup.find('tr', style=re.compile(r"background-color.*ccccff.*height.*20px"))
    if header is None:
        return []
    
    #back off one level and get the next table
    table = header.parent.parent.nextSibling
    
    data=[]
    for row in table.findAll('tr'):
        cells = row.findAll('font', size="2")
        if len(cells) < 4:
            continue
        
        #get date
        try:
            date = cells[0].string.strip()
            date = date.replace(r"&nbsp;", "")
            date = datetime.datetime.strptime(date, "%m/%d/%Y")
            date = date.strftime("%Y%m%d")
        except:
            continue
        
        ticker = cells[2].string.strip().replace(r"&nbsp;", "")
        ammount = cells[3].string.strip().replace(r"&nbsp;", "")
        notes = "" if (len(cells) <= 4 or cells[4].string is None) else cells[4].string.strip()
        ammount = ammount + " | " + notes if len(notes) > 0 else ammount
        ammount = ammount.replace(r"&nbsp;", "")
        
        data.append((date, ticker, ammount))
    
    return data

if __name__ == "__main__":
    data = _getBuybacks2("")
    for line in data:
        print line
    print len(data)
