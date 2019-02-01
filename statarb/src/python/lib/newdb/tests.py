from nose.tools import assert_raises

import util
import db

mdb = None

def setup():
    util.set_debug()
    db.init_db()
    
    global mdb
    mdb = db.get_db()
    mdb.execute("CREATE TEMPORARY TABLE test (coid mediumint unsigned not null, type smallint unsigned not null, value double not null, born bigint not null, died bigint, PRIMARY KEY(coid, type, born))")

def test_insert_delete_row():
    mdb.execute("TRUNCATE test")
    assert_raises(AssertionError, mdb.insert_row, 'test', {'coid': 1}, {'value': 1.0}, 1L)
    mdb.insert_checks(next = True, prev = False)
    assert_raises(mdb._conn.OperationalError, mdb.insert_row, 'test', {'coid': 1}, {'value': 1.0}, 1L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 1L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 2L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 3.0}, 3L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 0L)
    assert res is None
    res = mdb.get_prev_row('test', {'coid': 1, 'type': 1}, ['value'], 1L)
    assert res is None
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 1L)
    assert res['value'] == 1.0
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L)
    assert res['value'] == 1.0
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 3L)
    assert res['value'] == 3.0
    
    mdb.delete_row('test', {'coid': 1, 'type': 1}, 0L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 1L)
    assert res['value'] == 1.0
    mdb.delete_row('test', {'coid': 1, 'type': 1}, 1L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 1L)
    assert res is None
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L)
    assert res is None
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 3L)
    assert res['value'] == 3.0
    mdb.delete_row('test', {'coid': 1, 'type': 1}, 3L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 3L)
    assert res is None

def test_insert_row_reverse():
    mdb._curs.execute("TRUNCATE test")
    mdb.insert_checks(next = False, prev = False)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 2.0}, 2L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 1L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L, all_rows = True)
    assert len(res) == 2
 
def test_insert_row_check_next():
    mdb._curs.execute("TRUNCATE test")
    mdb.insert_checks(next = True, prev = False)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 2.0}, 2L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 1L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L, all_rows = True)
    assert len(res) == 1
    assert res[0]['value'] == 2.0
    res = mdb.get_prev_row('test', {'coid': 1, 'type': 1}, ['value'], 2L)
    assert res['value'] == 1.0
    assert res['died'] == 2.0

def test_insert_row_check_prev():
    mdb._curs.execute("TRUNCATE test")
    mdb.insert_checks(next = True, prev = True)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 1L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 2.0}, 2L)
    mdb.insert_row('test', {'coid': 1, 'type': 1}, {'value': 1.0}, 2L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L)
    assert res['value'] == 1.0
    mdb.delete_row('test', {'coid': 1, 'type': 1}, 1L)
    res = mdb.get_row_as_of('test', {'coid': 1, 'type': 1}, ['value'], 2L)
    assert res is None
