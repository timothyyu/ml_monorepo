#!/usr/bin/env python

import util
import newdb

def main():
    util.info("Checking Attributes")
    for table in ('co_attr_d', 'co_attr_n', 'co_attr_s', 'sec_attr_s', 'sec_attr_n'):
        print "Looking at %s" % table
        if table.startswith('co'):
            key = 'coid'
        else:
            key = 'secid'
            
        db.execute("SELECT DISTINCT %s, type, date FROM %s" % (key, table))
        rows_read = 0
        for row in db._curs.fetchall():
            rows_read += 1
            if rows_read % 10000 == 0: print "Lines seen: %d" % rows_read

            #skip backfill data once that stuff is worked out...
            db.execute("SELECT type, value, born, died FROM " + table + " WHERE %s=%s AND type=%s AND date=%s ORDER BY born", (key, row[key], row['type'], row['date']))
            attrs = db._curs.fetchall()
            if len(attrs)==1:
                assert attrs[0]['died'] is None or attrs[0]['died'] > attrs[0]['born']
                continue
            for i in range(len(attrs)):
                if i < len(attrs)-1:
                    assert attrs[i]['died'] is not None, attrs[i]
                    assert attrs[i]['died'] > attrs[i]['born'], attrs[i]
                    assert attrs[i]['died'] <= attrs[i+1]['born'], (attrs[i], attrs[i+1])
                    if attrs[i]['died'] == attrs[i+1]['born']:
                        assert attrs[i]['value'] != attrs[i+1]['value'], (attrs[i], attrs[i+1])
                    else:
                        assert attrs[i]['died'] is None or attrs[i]['died'] > attrs[i]['born'], attrs[i]
                        
        print "Top 10 company attribute counts"
        db.execute("SELECT %s, COUNT(*) AS count FROM %s GROUP BY %s ORDER BY count DESC LIMIT 10" % (key, table, key))
        for row in db._curs.fetchall():
            print row

        print "Top 10 attribute counts"
        db.execute("SELECT a.name, COUNT(*) AS count FROM " + table + " JOIN attribute_type a on type = a.code GROUP BY a.name ORDER BY count DESC LIMIT 10")
        for row in db._curs.fetchall():
            print row

if __name__ == "__main__":
    util.set_debug()
    newdb.init_db()
    db = newdb.get_db()
    main()
    
