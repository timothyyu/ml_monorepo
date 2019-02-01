#!/usr/bin/env python
import argparse
import newdb
import util
import sys
import os

database = None

def createView(table):    
    try:
        fields = database.execute("DESCRIBE " + table).fetchall()
    except Exception, e:
        print e
        return
    
    definition = ""
    for field in fields:
        name = field["Field"]
        type = field["Type"]
        if type.startswith("bigint"):
            definition += "m2d({name}) as {name}".format(name=name)
        else:
            definition += name
        definition += ","
    definition = "CREATE VIEW {} AS SELECT {} FROM {}".format(table + "v", definition[0:-1], table)
    print definition
    try:
        database.execute(definition)
    except Exception, e:
        print e
        return
    else:
        print "done!"
        
def dropView(table):    
   
    try:
        database.execute("DROP VIEW IF EXISTS {}".format(table + "v"))
        print "done!"
    except Exception, e:
        print e
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DB utils')
    
    parser.add_argument("--drop", action="store_false", dest="op", default=True)
    parser.add_argument("--create", action="store_true", dest="op", default=True)
    parser.add_argument("--table", action="store", dest="table")
    parser.add_argument("--database", action="store", dest="db", default="pri")
    args = parser.parse_args()
    
    dbConfig = None
    if args.db == "pri":
        newdb.init_db(os.environ["DB_CONFIG_FILE"])
        database = newdb.get_db()
    elif args.db == "sec":
        newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
        database = newdb.get_db()
    else:
        util.error("Valid database choices are [pri|sec]")
        sys.exit(1)
        
    if args.table is None:
        util.error("Specify table")
        sys.exit(1)
        
    if args.op:
        createView(args.table)
    else:
        dropView(args.table)
