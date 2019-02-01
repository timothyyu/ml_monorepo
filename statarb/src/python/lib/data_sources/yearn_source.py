import datetime
import shutil
import tempfile
import hashlib
import os
import cPickle

import yearn_scrape
from file_source import FileSource

class YEarnSource(FileSource):
    def __init__(self):
        yearn_file = "%s/yearn.last" % (os.environ["SCRAP_DIR"])
        try:
            yearn_last = cPickle.load(open(yearn_file, 'rb'))
        except IOError:
            yearn_last = None
        # Grab data
        date = datetime.date.today()
        result = yearn_scrape.get_yearn(date)
        if len(result) == 0:
            return
        m = hashlib.md5()
        m.update(str(result))
        result_md5 = m.digest()
        if (yearn_last is not None and yearn_last == result_md5):
            return
        # Save data to temp dir
        tempdir = tempfile.mkdtemp(dir="/spare/local")
        f = open("%s/%s.txt" % (tempdir, date.strftime("%Y%m%d")), "w")
        for row in result:
            try:
                f.write(("\t".join(row) + "\n").encode('ascii', 'ignore'))
            except:
                print row
                raise
        f.close()
        self._remote_dir = tempdir
        cPickle.dump(result_md5, open(yearn_file, 'wb'))

    def cwd(self, remote_dir):
        pass

    def __del__(self):
        try:
            shutil.rmtree(self._remote_dir)
        except AttributeError:
            pass
