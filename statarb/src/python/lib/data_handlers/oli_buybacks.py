import datafiles
import util
import newdb
import newdb.xrefsolve

database=newdb.get_db()

#def __datePlusOne(date,delta=datetime.timedelta(days=1)):
#    return datetime.datetime.strptime(date,"%Y%m%d")+delta

def process(filepath, source):
    sourceNameInDatabase="onlineinvestor"
    info=datafiles.read_info_file(filepath)
    
    if "hist" in source:
        backfill=1
        #timestamp will be data dependent
    else:
        backfill=0
        timestamp=util.convert_date_to_millis(info["date_modified"])

    database.setAttributeAutoCreate(True)
    
    with open(filepath,"r") as file:
        for line in file:
            tokens=line.split("\t")
            date=util.convert_date_to_millis(tokens[0])
            ticker=tokens[1]
            notes=tokens[2]
            if backfill==1:
                born=date
            else:
                born=timestamp
 
            secid=database.getSecidFromXref("TIC", ticker, date, "compustat", newdb.xrefsolve.preferUS)
            if secid is None:
                util.warning("Failed to map ticker {},{}".format(ticker,tokens[0]))
                return
            
            coid,issueid=database.getCsidFromSecid(secid)
            assert coid is not None
            
            database.insertAttribute("co", "s", coid, date,sourceNameInDatabase , "BUYBACK", notes, born, None, backfill)
            
if __name__ == "__main__":
    try:
        newdb.init_db()
        database = newdb.get_db()
        database.setAttributeAutoCreate("true")
        database.start_transaction()
        database.rollback()
    except Exception, e:
        print e
        database.rollback()
        raise
