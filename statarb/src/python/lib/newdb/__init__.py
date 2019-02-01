import os
from db_logic_mysql import DBLogicMySQL
from db_logic_base import DBLogicBase

db = None

def get_db():
    global db
    return db

def init_db(config_file=os.environ['DB_CONFIG_FILE']):
    global db
    if db==None:
        db = DBLogicBase(config_file,DBLogicMySQL())
    
def close_db():
    global db
    db.close()
    db=None

