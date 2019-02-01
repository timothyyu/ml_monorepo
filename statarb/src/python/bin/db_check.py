#!/usr/bin/env python

import util
import newdb
from collections import Counter
from collections import deque

#Check if two rows have equal values in the keys attributes
def __compare(row1,row2,keys):
    equal=True
    for key in keys:
        if row1[key]!=row2[key]:
            equal=False
            break
    return equal

def __getNextRow(database,command,buffer=deque()):
    if len(buffer)>0:
        return buffer.popleft()
    else:
        rows=database.execute(command).fetchall()
        if len(rows)==0:
            return None
        else:
            buffer.extend(rows)
            return buffer.popleft()

#def __getNextBatchFromCursor(keys,cursor,buffer=[]):
def __getNextBatchFromHandler(keys,database,command,buffer=[]):
    batch=[]
    batch.extend(buffer)
    del buffer[:]
    
    #row=cursor.fetchone()
    #row=database.execute(command).fetchone()
    row=__getNextRow(database, command)
    while row is not None:
        if len(batch)==0:
            batch.append(row)
            #row=cursor.fetchone()
            #row=database.execute(command).fetchone()
            row=__getNextRow(database, command)
        elif __compare(batch[-1], row, keys):
            batch.append(row)
            #row=cursor.fetchone()
            #row=database.execute(command).fetchone()
            row=__getNextRow(database, command)
        else:
            buffer.append(row)
            break
        
    if len(batch)==0:
        return None
    else:
        return batch
    
def __getNextBatchFromCursor(keys,cursor,buffer=[]):
    batch=[]
    batch.extend(buffer)
    del buffer[:]
    
    row=cursor.fetchone()
    #row=database.execute(command).fetchone()
    #row=__getNextRow(database, command)
    while row is not None:
        if len(batch)==0:
            batch.append(row)
            row=cursor.fetchone()
            #row=database.execute(command).fetchone()
            #row=__getNextRow(database, command)
        elif __compare(batch[-1], row, keys):
            batch.append(row)
            row=cursor.fetchone()
            #row=database.execute(command).fetchone()
            #row=__getNextRow(database, command)
        else:
            buffer.append(row)
            break
        
    if len(batch)==0:
        return None
    else:
        return batch
    
#verify that a consecutive slice of rows are nice and consistent
def __verify(rows,start,end,data,warnings,stats):
    #check that born<died for each row. report rows with born=died and born>died
    for i in range(start,end):
        if rows[i]["born"]==rows[i]["died"]:
            if warnings: util.warning("born=died: {}".format(rows[i]))
            stats["row born=died"]=stats["row born=died"]+1
            stats["warnings"]=stats["warnings"]+1
        elif rows[i]["died"] is not None and rows[i]["born"]>rows[i]["died"]:
            util.error("born>died: {}".format(rows[i]))
            stats["row born>died"]=stats["row born>died"]+1
            stats["errors"]=stats["errors"]+1
    #check that each row was born at the point the other died
    #chck if consecutive rows have the same data
    for i in range(start+1,end):
        if rows[i-1]["died"] is None or rows[i-1]["died"]>rows[i]["born"]: #overlapping rows
            util.error("overlapping rows: {} | {}".format(rows[i-1],rows[i]))
            stats["overlapping row"]=stats["overlapping row"]+1
            stats["errors"]=stats["errors"]+1
        elif rows[i-1]["died"]<rows[i]["born"]:
            if warnings: util.warning("gap in the timeline: {} | {}".format(rows[i-1],rows[i])) #timeline gap
            stats["gap"]=stats["gap"]+1
            stats["warnings"]=stats["warnings"]+1
        elif util.dict_fields_eq(rows[i-1], rows[i], data):
            if warnings: util.warning("consecutive rows with same data: {} | {}".format(rows[i-1],rows[i]))
            stats["consecutive with same data"]=stats["consecutive with same data"]+1
            stats["warnings"]=stats["warnings"]+1
            
#verify that a consecutive slice of rows are nice and consistent
def __verifySymbols(rows,start,end,data,warnings,stats):
    #check that born<died for each row. report rows with born=died and born>died
    for i in range(start,end):
        if rows[i]["born"]==rows[i]["died"]:
            if warnings: util.warning("born=died: {}".format(rows[i]))
            stats["row born=died"]=stats["row born=died"]+1
            stats["warnings"]=stats["warnings"]+1
        elif rows[i]["died"] is not None and rows[i]["born"]>rows[i]["died"]:
            util.error("born>died: {}".format(rows[i]))
            stats["row born>died"]=stats["row born>died"]+1
            stats["errors"]=stats["errors"]+1
    #check that each row was born at the point the other died
    #chck if consecutive rows have the same data
    for i in range(start+1,end):
        if rows[i-1]["died"] is None or rows[i-1]["died"]>rows[i]["born"]: #overlapping rows
            #do a more thorough check
            if rows[i-1]["country"]!=rows[i]["country"] or rows[i-1]["coid"]==rows[i]["coid"]:
                if warnings: util.warning("benign overlap: {} | {}".format(rows[i-1],rows[i]))
                stats["benign overlap"]=stats["benign overlap"]+1
                stats["warnings"]=stats["warnings"]+1
            else:
                util.error("overlapping rows: {} | {}".format(rows[i-1],rows[i]))
                stats["overlapping row"]=stats["overlapping row"]+1
                stats["errors"]=stats["errors"]+1
        elif rows[i-1]["died"]<rows[i]["born"]:
            if warnings: util.warning("gap in the timeline: {} | {}".format(rows[i-1],rows[i])) #timeline gap
            stats["gap"]=stats["gap"]+1
            stats["warnings"]=stats["warnings"]+1
        elif util.dict_fields_eq(rows[i-1], rows[i], data):
            if warnings: util.warning("consecutive rows with same data: {} | {}".format(rows[i-1],rows[i]))
            stats["consecutive with same data"]=stats["consecutive with same data"]+1
            stats["warnings"]=stats["warnings"]+1

def xrefsOK():
    #get the database
    database = newdb.get_db()
    
    warnings=0
    errors=0
        
    ###############################
    
    util.info("\nChecking xrefs based on SecIds")    
    cursor=database.execute("SELECT * FROM {} ORDER BY source,secid,xref_type,born".format(database.XREF_TABLE))
    #database.execute("SELECT * FROM {} ORDER BY source,secid,xref_type,born".format("xref"))
    #cursor=database._curs
    buffer=[]
    keys=("secid","xref_type","source")
    stats=Counter()
    while True:
        batch=__getNextBatchFromCursor(keys, cursor, buffer)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("value",), False,stats)
    warnings=warnings+stats["warnings"]
    errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
    
    ###################################
    
    util.info("\nChecking xrefs based on Values")
    cursor=database.execute("SELECT xf.secid,xf.xref_type,xf.value,xf.source,cs.coid,cs.issueid,cs.country,xf.born,xf.died FROM {} as xf, {} as cs WHERE xf.secid=cs.secid ORDER BY xf.source,xf.xref_type,xf.value,xf.born".format(database.XREF_TABLE,database.STOCK_TABLE))
    #database.execute("SELECT xf.secid,xf.xref_type,xf.value,xf.source,cs.coid,cs.issueid,cs.country,xf.born,xf.died FROM {} as xf, {} as cs WHERE xf.secid=cs.secid ORDER BY xf.source,xf.xref_type,xf.value,xf.born".format("xref","stock"))
    #cursor=database._curs
    buffer=[]
    keys=("value","xref_type","source")
    stats=Counter()
    while True:
        batch=__getNextBatchFromCursor(keys, cursor, buffer)
        if batch is None:
            break
        __verifySymbols(batch, 0, len(batch), ("secid",), False,stats)
    warnings=warnings+stats["warnings"]
    errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
    
    return (errors==0)

def attrOK(target,datatype,warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+target+database.ATTR_TABLE+datatype)
    database.execute("HANDLER {} OPEN AS foobar".format(target+database.ATTR_TABLE+datatype))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=(target+"id","type","date")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("value","backfill"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)

def splitOK(warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+database.SPLIT)
    database.execute("HANDLER {} OPEN AS foobar".format(database.SPLIT))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=("secid","date")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("rate","backfill"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)

def dividendOK(warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+database.DIVIDEND)
    database.execute("HANDLER {} OPEN AS foobar".format(database.DIVIDEND))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=("secid","date")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("dividend","casheq","backfill","currency"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)

def priceOK(warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+database.PRICE_FULL_TABLE)
    database.execute("HANDLER {} OPEN AS foobar".format(database.PRICE_FULL_TABLE))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=("secid","date")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("open","high","low","close","volume","adj","adrrc","cond","backfill","currency"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)

def actualsOK(datatype,warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+database.CO_ACTUALS+datatype)
    database.execute("HANDLER {} OPEN AS foobar".format(database.CO_ACTUALS+datatype))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=("coid","type","date")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("value","backfill","currency"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)
    
def estimatesOK(datatype,warn,stepSize=100000):
    #get the database
    database = newdb.get_db()
    warnings=0
    errors=0
    
    ###############################
    
    util.info("\nChecking "+database.CO_ESTIMATES+datatype)
    database.execute("HANDLER {} OPEN AS foobar".format(database.CO_ESTIMATES+datatype))
    command="HANDLER foobar READ `PRIMARY` NEXT LIMIT {}".format(stepSize)
    keys=("coid","type","date","brokerid","orig")
    stats=Counter()
    while True:
        batch=__getNextBatchFromHandler(keys, database, command)
        if batch is None:
            break
        __verify(batch, 0, len(batch), ("value","backfill","currency"), warn,stats)
        warnings=warnings+stats["warnings"]
        errors=errors+stats["errors"]
    
    util.info("Errors={}, Warnings={}".format(stats["errors"],stats["warnings"]))
    del stats["warnings"]
    del stats["errors"]
    for k,v in stats.iteritems():
        util.info("{} = {}".format(k,v))
        
    database.execute("HANDLER foobar CLOSE")
            
    return (warnings,errors)

#add command line options
if __name__ == "__main__":
    newdb.init_db()
    #dbLocal=db.get_db();
    #util.DEBUG=True
    #xrefsOK()
    #attrOK("sec","n",False)
    #attrOK("sec","d",False)
    #attrOK("sec","s",False)
    #attrOK("co","n",False)
    #attrOK("co","d",False)
    #attrOK("co","s",False)
    #dividendOK(False)
    #priceOK(False)
    #splitOK(False)
    #estimatesOK("n", False)
    #estimatesOK("b", False)
    #actualsOK("n", False)
    #actualsOK("d", False)