#!/usr/bin/env python
import sys
import dateutil
import datetime

import util
from data_sources import file_source

util.niceme()

#takes YYYYMM and mils

fs = file_source.FileSource('/apps/exec/log/rts1/')
listing = fs.list_recursive('cost.log', sizes=False)
start = dateutil.parser.parse(sys.argv[1] + "01")
end = start + dateutil.relativedelta.relativedelta(months=1)
dt = start
rebates = 0.0
mils = float(sys.argv[2])

while dt < end:
    for row in listing:
        if row[0].find(dt.strftime("%Y%m%d")) == -1: continue
        for line in open(row[0]):
            if line.find("FILL") != -1:
                (date, type, sym, ecn, type, size, price, bid, ask, liq) = line.split()
                date = util.convert_date_to_millis(date)
                type = int(type)
                size = int(size)
                price = float(price)
                bid = float(bid)
                ask = float(ask)

                if liq != 'remove':
                    if ecn == "ISLD":
                        rebates += mils * abs(size)

    dt += datetime.timedelta(days=1)

print start.strftime('%Y%m'), rebates
