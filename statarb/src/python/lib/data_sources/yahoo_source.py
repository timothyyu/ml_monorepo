import csv
import datetime
import shutil
import tempfile
import os
import re

import util
import ystockquote
#import db
import newdb
from file_source import FileSource, DataSourceError

class YahooSource(FileSource):
    def __init__(self):
        newdb.init_db()
        database = newdb.get_db()
        
        rows=database.execute("SELECT value FROM {} WHERE xref_type=%(type)s AND source=%(source)s AND born<=%(now)s AND (died>%(now)s OR died is NULL)".format(database.XREF_TABLE), {"type":database.getXrefType("TIC"), "now":util.now(),"source":database.getSourceType("compustat_idhist")}).fetchall()
        tickers = [row['value'] for row in rows if re.match("[0-9].+", row["value"])==None]
        util.info("Retrieving info on %d tickers" % len(tickers))
        database.close()
        
        fields = [
            "symbol",
            "name",
            "exchange",
            "error_flag",

            "market_cap",
            "avg_daily_volume",

            "ex_dividend_date",
            "dividend_pay_date",
            "dividend_share_ratio",
            "dividend_yield",

            #"ebitda",
            "earnings_share_ratio",
            "eps_est_cur_year",
            "eps_est_next_qtr",
            "eps_est_next_year",
            "pe_ratio",
            "peg_ratio",
            "price_book_ratio",
            "price_eps_est_cur_year_ratio",
            "price_eps_est_next_year_ratio",
            "price_sales_ratio",
            "short_ratio",
        ]
        # Grab data
        data = ystockquote.get_symbols(tickers, fields)
        # Save data to temp dir
        tempdir = tempfile.mkdtemp(dir=os.environ['TMP_DIR'])
        f = open("%s/yahoo.csv" % tempdir, "w")
        writer = csv.DictWriter(f, fields)
        rows = [dict(zip(fields, fields))]
        rows.extend(data.values())
        writer.writerows(rows)
        f.close()
        # Zip file
        result = os.system("zip -j %s/yahoo-%s.csv.zip %s/yahoo.csv 1>/dev/null" % (tempdir, datetime.datetime.now().strftime("%Y%m%d%H%M"), tempdir))
        if (result != 0):
            shutil.rmtree(tempdir)
            raise DataSourceError("Could not zip file")
        os.remove("%s/yahoo.csv" % tempdir)
        self._remote_dir = tempdir

    def cwd(self, remote_dir):
        pass

    def __del__(self):
        try:
            shutil.rmtree(self._remote_dir)
        except AttributeError:
            pass
