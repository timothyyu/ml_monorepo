import odo.odo
import blaze

from Data import StockManager

dbmgr = StockManager.DBManager()

mongo_uri = dbmgr.get_mongo_uri(database=dbmgr._default_mongo_database,
                                collection=dbmgr._default_mongo_table_stock_daily_price)
csv_uri = "/Users/jianboxue/Projects/Stock_Price_Daily.csv"


## change the dshape of csv, to have a better recognition
csv_dshape = blaze.dshape("var * {'code':string, 'date':string, 'open':float16, 'high':float16, 'low':float16, "
                          "'close':float16, 'volume':int32, 'amount':int32}")
csv_handler = blaze.Data(csv_uri, csv_dshape)

odo.odo(csv_handler, mongo_uri)