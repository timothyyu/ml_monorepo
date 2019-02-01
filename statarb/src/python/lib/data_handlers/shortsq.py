import util
import datafiles
import newdb
import newdb.xrefsolve

database = newdb.get_db()

#the boolean variable refers to whether the attribute should be stored for each date, or only for dates with sufficient difference
#from previous dates. False=Every day, True=Only if different
attributeMap={"Total_Short_Interest" : ("TOTAL_SHORT_INTEREST",False),
                  "Days_to_Cover": ("DAYS_TO_COVER",False),
                  #"Short_%_of_Float": ("SHORT_PCT_FLOAT",False),
                  "%_Insider Ownership" : ("PCT_INSIDERS",True),
                  "%_Institutional_Ownership": ("PCT_INSTITUTIONAL",True),
                  #"Short:_Prior_Mo": ("SHORT_INTEREST_PRIOR_MONTH",False),
                  #"%_Change_Mo/Mo": ("PCT_CHANGE_PRIOR_MONTH",False),
                  "Shares:Float" : ("FLOAT",True),
                  #"Avg._Daily_Vol." : ("AVG_VOLUME",False),
                  #"Shares:Outstanding" : ("SHARES",False),
                  "Short_Squeeze_Ranking" : ("SQ_RANK",False)
                  }

THRESHOLD=0.02
def approximatelyEqual(previous,current):
    if current is None and previous is None: #both None 
        return True
    elif current is None or  previous is None: #exactly one None
        return False
    elif current==0 and previous==0: #both are zero
        return True
    elif current*previous<=0: #different signs (+,0,-)
        return False
    elif current/previous<(1+THRESHOLD) and current/previous>(1-THRESHOLD): #equal with _THRESHOLD
        return True
    else:
        return False
    
def process(filepath, source):
    info=datafiles.read_info_file(filepath)

    if info["date_last_absent"] is not None:
        backfill=0
        timestamp=util.convert_date_to_millis(info["date_first_present"])
    else:
        backfill=1
        timestamp=util.convert_date_to_millis(info["date_modified"])

    database.setAttributeAutoCreate(True)
    
    bad=0
    data = util.csvdict(open(filepath))
    for row in data:
        ticker=row["Symbol"]
        secid=database.getSecidFromXref("TIC", ticker, timestamp, "compustat_idhist", newdb.xrefsolve.preferUS)
        if secid is None:
            continue
        
        try:
            date=util.convert_date_to_millis(row["Record_Date"])
        except:
            util.warning("Bad date for row: "+str(row))
            bad+=1    
        if bad>20:
            util.error(str(bad)+" bad lines found. Raising excpeption. Go check file "+filepath)
            raise Exception(str(bad)+" bad lines found. Raising excpeption. Go check file "+filepath)
            
        for sqAtt,ourAtt in attributeMap.iteritems():
            name=ourAtt[0]
            compareWithRecent=ourAtt[1]
            value=row[sqAtt]
            if value=='': value=None
            database.insertAttribute("sec","n", secid, date, source, name, value, timestamp, None, backfill, False, compareWithRecent,approximatelyEqual)


if __name__ == "__main__":
    try:
        newdb.init_db()
        database = newdb.get_db()
        database.setAttributeAutoCreate("true")
        database.start_transaction()
        process("/apps/logs/ase/data/shortsqueeze/sq/2010/09/07/shortint.20100907.txt.6de01a5c","shortsq")
        print 'ey, ok'
        #database.commit()
        database.rollback()
    except Exception, e:
        print e
        database.rollback()
        raise
