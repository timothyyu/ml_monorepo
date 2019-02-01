import MySQLdb
import MySQLdb.cursors
import util
import os

class DBLogicMySQL():
            
    def init(self, db_config):
        if 'unix_socket' in db_config and db_config["host"]==os.environ["HOSTNAME"]:
            self.conn = MySQLdb.connect(unix_socket=db_config['unix_socket'], user=db_config['username'], passwd=db_config['password'],
                                         db=db_config['database'], cursorclass=MySQLdb.cursors.DictCursor, charset='utf8')
        else:
            self.conn = MySQLdb.connect(host=db_config['host'], port=int(db_config['port']), user=db_config['username'],
                                         passwd=db_config['password'], db=db_config['database'], cursorclass=MySQLdb.cursors.DictCursor, charset='utf8')
            
        util.debug("Connected to db %s @ %s: %s" % (db_config['username'], db_config['host'], self.conn.get_server_info()))
        self.curs = self.conn.cursor()
        self.execute("SET sql_mode='STRICT_TRANS_TABLES'")
        self.execute("SET autocommit=0")
        #self.execute("SET SESSION query_cache_type=OFF")
        self.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        #self.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")

    def execute(self, sqlstring, args=None):
        if util.DEBUG: util.debug(sqlstring + " : " +  str(args))
        self.curs.execute(sqlstring, args)

    def getParam(self, param = None):
        if param is None:
            return "%s"
        else:
            return "%(" + param + ")s"

    def getQuoted(self, param):
        return "`" + param + "`"

    def start_transaction(self):
        util.info("BEGINNING TRANSACTION")
        self.execute("START TRANSACTION")

    def commit(self):
        util.info("COMMITTING TRANSACTION")
        self.execute("COMMIT")

    def rollback(self):
        util.info("ROLLBACK TRANSACTION")
        self.execute("ROLLBACK")
