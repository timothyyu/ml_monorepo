import urllib2
import datetime
import dateutil.parser
import util
import time
from BeautifulSoup import BeautifulSoup

NUM_DAYS = 30
ALL_OR_NOTHING=True
MAX_ATTEMPTS=5

def get_yearn(date):
    result = []
    for i in range(NUM_DAYS):
        attempt=0
        err=None
        while attempt<MAX_ATTEMPTS:            
            try:
                res=scrape_yearn(date)
                break
            except urllib2.URLError,e:
                res=None
                err=e
                time.sleep(3) #sleep for 3 seconds
                attempt+=1
                
        if res is None:
            raise err
        
        result += scrape_yearn(date)
        date += datetime.timedelta(days=1)

    return result

def get_yearn_archive():
    result = []
    date1 = dateutil.parser.parse("20060101")
    date2 = dateutil.parser.parse("20090315")
    date = date1
    while date <= date2:
        result += scrape_yearn(date)
        date += datetime.timedelta(days=1)
    return result

def scrape_yearn(date):
    result = []
    datestr = date.strftime('%Y%m%d')
    url = "http://biz.yahoo.com/research/earncal/%s.html" % (datestr)
    try:
        data = urllib2.urlopen(url,timeout=30)
    except urllib2.HTTPError, e:
        if e.code==404:
            data=""
        else:
            util.error("Error on url: "+url)
            util.error(str(e))
            raise

    soup = BeautifulSoup(data)
    parsing = False
    for tr in soup.findAll('tr'):
        if str(tr.contents[0]).find('Company') != -1 and str(tr.contents[1]).find('Symbol') != -1:
            parsing = True
            if str(tr.contents[2]).find('Time') != -1:
                time_idx = 2
            elif str(tr.contents[3]).find('Time') != -1:
                time_idx = 3
            else:
                raise Exception('Couldn\'t find time column')
            value_idx = None
            if str(tr.contents[2]).find('EPS Estimate') != -1:
                value_idx = 2
            continue
        if parsing:
            tds = tr.findAll('td')
            if len(tds) < 4:
                break
            name = ''.join(tds[0].findAll(text=True))
            symbol = ''.join(tds[1].findAll(text=True))
            if value_idx is not None:
                value = ''.join(tds[value_idx].findAll(text=True))
            else:
                value = 'N/A'
            time = ''.join(tds[time_idx].findAll(text=True))
            result.append((datestr, name, symbol, value, time))
    return result

def test():
    result = scrape_yearn(datetime.datetime.strptime("20110814","%Y%m%d"))
    print result

if __name__=="__main__":
    test()