import hashlib
import datetime
import pytz
import dateutil.parser
import os
import glob
import sys
import time
import string
import errno
import csv
import signal
import smtplib
import tempfile
from email.mime.text import MIMEText
from lock_file import LockFile, LockError
import paramiko
import subprocess

DEBUG = False
EPOCH = dateutil.parser.parse("1970-01-01 00:00:00.000 UTC")
LOGFILE = sys.stdout
MAX_EMAIL = 100

mailcnt = 0
last_email_time = 0

def check_include():
    if (YYYYMMDD() != os.environ["DATE"]):
        print "Have you sourced inlude.sh lately DATE: {}".format(os.environ["DATE"]) 
        raise 
    
def check_running():
    processes = shellExecute("ps -auxww | grep {}".format(sys.argv[0])) 
    if len(processes) > 2:
        print "Looks like it's already running: "
        print processes
        raise

def set_debug():
    global DEBUG
    DEBUG = True

def set_silent():
    global LOGFILE
    LOGFILE = open('/dev/null', 'w', 0)

def set_log_file(name="",append=False):
    global LOGFILE
    if append:
        LOGFILE = open( "%s/%s.%s.%s.log" % (os.environ["LOG_DIR"], os.path.basename(sys.argv[0]), os.environ["STRAT"], name), 'a', 0 )
        LOGFILE.write("\n###############\n")
        LOGFILE.write("Process {} inited around {}\n\n".format(os.getpid(),str(datetime.datetime.now())))
    else:
        LOGFILE = open( "%s/%s.%s.%s.%d.log" % (os.environ["LOG_DIR"], os.path.basename(sys.argv[0]), os.environ["STRAT"], name, os.getpid()), 'w', 0 )

def debug(message):
    if DEBUG: log(message, "DEBUG")

def info(message):
    log(message, "INFO")

def warning(message):
    log(message, "WARNING")

def error(message):
    log(message, "ERROR")
    if not DEBUG:
        sys.stderr.write(message)
        sys.stderr.write("\n")

def log(message, level="INFO"):
    now = datetime.datetime.utcnow()
    LOGFILE.write( '%s [%s.%03d]: %s\n' % (level, now.strftime('%Y%m%d %H:%M:%S'), now.microsecond, message) )

def flush():
    LOGFILE.flush()

def close_log_file():
    if LOGFILE != sys.stdout:
        LOGFILE.close()

def cat(file):
    f = open(file, 'r')
    for line in f: print line

def email(subj, message):
    global MAX_EMAIL, mailcnt, last_email_time
    if time.time() - last_email_time > 60 * 5:
        mailcnt = 0

    mailcnt += 1
    if mailcnt > MAX_EMAIL: return
    
    msg = MIMEText(message)
    msg['Subject'] = subj
    ase = 'ase@tower-research.com'
    user = os.environ['USER'] + '@tower-research.com'
    msg['To'] = user
    msg['From'] = user
    s = smtplib.SMTP()
    s.connect()
    s.sendmail( user, ase, msg.as_string() )
    s.quit()

    last_email_time = time.time()

def lock(name=""):
    mkdir("%s/lock" % os.environ["SCRAP_DIR"])
    lock_file = "%s/lock/%s.%s.%s" % (os.environ["SCRAP_DIR"], os.path.basename(sys.argv[0]), os.environ["STRAT"], name)
    # Check for previously running instance
    try:
        lock_f = LockFile(lock_file, wait=False, remove=False)
    except LockError:
        error( "Could not create lockfile, previous instance running?" )
        sys.exit(0)
    return lock_f

def mkdir(dir):
    try:
        os.mkdir(dir)
    except OSError, e:
        if e.errno <> errno.EEXIST: raise

def tmpdir():
    return tempfile.mkdtemp(dir=os.environ['TMP_DIR'])

def alarm(signum, frame):
    raise Exception("alarm")

def sleep_or_input(secs):
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(secs)
    try:
        raw_input()
        signal.alarm(0)
    except Exception as e:
        if e[0] == "alarm":
            return

def niceme():
    result = os.system("renice 10 -p %d &>/dev/null" % os.getpid())
    if result != 0:
        raise Exception('Failed to renice self')

def csvdict(fileobj):
    dialect = csv.Sniffer().sniff(fileobj.read(4096))
    fileobj.seek(0)
    return csv.DictReader(fileobj, dialect=dialect)

def dict_fields_eq(dict1, dict2, fields):
    """
    Test if specific fields in two dicts are equal

    >>> dict_fields_eq({'a':1, 'b':2, 'c':4}, {'a':1, 'b':3, 'c':5}, ['a'])
    True
    >>> dict_fields_eq({'a':1, 'b':2, 'c':4}, {'a':1, 'b':3, 'c':5}, ['a', 'b'])
    False
    """
    for field in fields:
        if dict1[field] != dict2[field]:
            return False
    return True

def dict_fields_eq_num_stable(dict1, dict2, fields,EPS=1e-6):
    """
    Test if specific fields in two dicts are equal

    >>> dict_fields_eq({'a':1, 'b':2, 'c':4}, {'a':1, 'b':3, 'c':5}, ['a'])
    True
    >>> dict_fields_eq({'a':1, 'b':2, 'c':4}, {'a':1, 'b':3, 'c':5}, ['a', 'b'])
    False
    """
    for field in fields:
        a=dict1[field]
        b=dict2[field]
        if isinstance(a,float) and isinstance(b,float):
            if b!=0 and abs(a/b-1)>EPS:
                return False
            elif b==0 and abs(a)>EPS:
                return False
        elif dict1[field] != dict2[field]:
            return False
    return True

def calc_md5sum_of_fh(f):
    hash = hashlib.md5()
    while True:
        data = f.read(8096)
        if not data:
            break
        hash.update(data)
    return hash.hexdigest()

def cusip8to9(cusip):
    """
    Calculate and append cusip check digit (9th digit)

    >>> cusip8to9('68401P10')
    '68401P106'
    """
    cusip = cusip[0:8].upper()
    sum = 0
    for i in range(8):
        c = cusip[i]
        if c in string.digits:
            v = int(c)
        elif c in string.ascii_uppercase:
            v = ord(c)-ord('A') + 10
        elif c == '*':
            v = 36
        elif c == '@':
            v = 37
        elif c == '#':
            v = 38
        else:
            assert False
        if (i+1)%2 == 0:
            v *= 2
        sum += v/10 + v%10
    return cusip + str((10 - sum % 10)%10)

#XXX need to make sure this stuff runs quickly
def now():
    ts = datetime.datetime.utcnow()
    return convert_date_to_millis(ts)

def convert_date_to_millis(adate):
    """
    Convert a date to a long representing mills since epoch

    >>> convert_date_to_millis(10000000000L)
    10000000000L
    >>> convert_date_to_millis("19000101")
    -2208988800000L
    >>> convert_date_to_millis(datetime.datetime(2008, 10, 10, 01, 01, 01, 0, pytz.utc))
    1223600461000L
    """
    if adate is None:
        return None

    # Shortcut return if it's already a bigint usec
    if adate.__class__ is long:
        return adate

    # Intermediate conversions
    if adate.__class__ is str or adate.__class__ is unicode:
        adate = dateutil.parser.parse(adate)
        if adate.tzinfo is None:
            adate = adate.replace(tzinfo=pytz.utc)
    elif adate.__class__ is datetime.date:
        adate = datetime.datetime(adate.year, adate.month, adate.day, 0, 0, 0, 0, pytz.utc)

    # Final conversion from datetime to bigint millis
    if adate.__class__ is datetime.datetime:
        if adate.tzinfo is None:
            adate = adate.replace(tzinfo=pytz.utc)
        adate = adate - EPOCH
    if adate.__class__ is datetime.timedelta:
        dt = adate.days*86400000L + adate.seconds*1000 + adate.microseconds/1000
        return dt
    raise TypeError("Unknown date type for conversion")

def convert_millis_to_datetime(millis):
    if millis is None:
        return millis
    return EPOCH + datetime.timedelta(milliseconds=millis)

def convert_usec_to_datetime(usec):
    return convert_millis_to_datetime(usec/1000)

def YYYYMMDD():
    return datetime.datetime.utcnow().strftime("%Y%m%d")

#remove non printable characters that can have creeped in name
def printableString(name):
    #check first if it is printable
    printable=reduce(lambda x,y: x and (y in string.printable),name,True)
    if printable:
        return name
    else:
        newName=[c for c in name if c in string.printable]
        newName=''.join(newName).strip()
        return newName


class ParamikoIgnorePolicy (paramiko.MissingHostKeyPolicy):
    """
    Policy for logging a python-style warning for an unknown host key, but
    accepting it. This is used by L{SSHClient}.
    """
    def missing_host_key(self, client, hostname, key):
        pass
    
class Node(object):
    __slots__ = ['prev', 'next', 'me']
    def __init__(self, prev, me):
        self.prev = prev
        self.me = me
        self.next = None

class LRU:
    """
    Implementation of a length-limited O(1) LRU queue.
    Built for and used by PyPE:
    http://pype.sourceforge.net
    Copyright 2003 Josiah Carlson.
    """
    def __init__(self, count, pairs=[]):
        self.count = max(count, 1)
        self.d = {}
        self.first = None
        self.last = None
        for key, value in pairs:
            self[key] = value
    def __contains__(self, obj):
        return obj in self.d
    def get(self,obj,default=None):
        if obj in self.d:
            return self[obj]
        else:
            return default
    def __getitem__(self, obj):
        a = self.d[obj].me
        self[a[0]] = a[1] #probably doint a __setitem__ to put item in front
        return a[1]
    def __setitem__(self, obj, val):
        if obj in self.d:
            del self[obj]
        nobj = Node(self.last, (obj, val))
        if self.first is None:
            self.first = nobj
        if self.last:
            self.last.next = nobj
        self.last = nobj
        self.d[obj] = nobj
        if len(self.d) > self.count:
            if self.first == self.last:
                self.first = None
                self.last = None
                return
            a = self.first
            a.next.prev = None
            self.first = a.next
            a.next = None
            del self.d[a.me[0]]
            del a
    def __delitem__(self, obj):
        nobj = self.d[obj]
        if nobj.prev:
            nobj.prev.next = nobj.next
        else:
            self.first = nobj.next
        if nobj.next:
            nobj.next.prev = nobj.prev
        else:
            self.last = nobj.prev
        del self.d[obj]
    def __iter__(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me[1]
            cur = cur2
    def iteritems(self):
        cur = self.first
        while cur != None:
            cur2 = cur.next
            yield cur.me
            cur = cur2
    def iterkeys(self):
        return iter(self.d)
    def itervalues(self):
        for i,j in self.iteritems():
            yield j
    def keys(self):
        return self.d.keys()
    def clear(self):
        self.d.clear()
        self.first=self.last=None
        
        
        
def mtime(filename):
    return os.stat(filename).st_mtime

def getfiles(path):
    return sorted(glob.glob(path+"/*"), key=mtime)
    
def shellExecute(command):
    p=subprocess.Popen(command,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out=p.stdout.read()
    err=p.stderr.read()
    p.wait()
        
    return out,err

#check for errors...
def exchangeOpenClose(exchange=os.environ['PRIMARY_EXCHANGE'],date=os.environ['DATE']):    
    message,dummy=shellExecute("$JAVA ase.data.Exchange oc {} {}".format(exchange,date))
    
    open,close=message.strip().split("|")
    return long(open),long(close)

#check for errors...
def exchangeTradingOffset(exchange,date,offset):    
    message,dummy=shellExecute("$JAVA ase.data.Exchange tda {} {} {}".format(exchange,date,offset))
    
    date=message.strip()
    return int(date)

def loadDictFromFile(filepath):
    d={}
    with open(filepath,"r") as file:
        d = eval(file.read())
    return d

def isInteger(strInput):
    try:
        int(strInput)
        return True
    except ValueError:
        return False

def isFloat(strInput):
    try:
        float(strInput)
        return True
    except ValueError:
        return False

