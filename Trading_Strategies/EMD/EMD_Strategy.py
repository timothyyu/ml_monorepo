

import Data.StockDataManager as sm
import Data.TimeSeries as ts

settings = sm.Settings()
tmgr = sm.TaskManager(settings)

data = ts.TimeSeries(settings).get_stock_series(['000001'], start='2012-01-01', fields=['close'])
price = data['close']


import pyhht.emd as emd
import numpy as np
imfs = emd.EMD(np.array(price))

