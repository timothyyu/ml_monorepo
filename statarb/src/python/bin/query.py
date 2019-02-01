#!/usr/bin/env python
import os
import sys
from time import gmtime, strftime

import util
import db

if __name__ == "__main__":
    convert_dates = True
    util.set_silent()
    
    db.init_db(os.environ['CONFIG_DIR'] + "/db.asereport.cfg")
    db = db.get_db()

    for line in sys.stdin.readlines():
        sql = line
        first = True
        db.execute(sql)
        for row in db._curs.fetchall():
            if first:
                print "|".join(row.keys())
                first = False
                
            s = ""
            for k, v in row.items():
                if convert_dates and (k == 'born' or k == 'died' or k == 'date') and v > 0:
                    v = strftime("%Y%m%d %H:%M:%S", gmtime(v/1000))
                if v is None: v = ''
                s += str(v) + "|"
            print s
            
        
            
        

