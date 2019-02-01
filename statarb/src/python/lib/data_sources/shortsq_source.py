import datetime
import shutil
import os

import util
from file_source import FileSource

class ShortSqSource(FileSource):
    def __init__(self):
        # Save data to temp dir
        tempdir = util.tmpdir()
        filename = "shortint.%s.txt" % datetime.date.today().strftime("%Y%m%d")
        os.system("wget -q http://shortsqueeze.com/userftp106/%s -O%s/%s" % (filename, tempdir, filename))
        if os.path.getsize('%s/%s' % (tempdir, filename)) == 0:
            os.remove('%s/%s' % (tempdir, filename))
        self._remote_dir = tempdir

    def cwd(self, remote_dir):
        pass

    def __del__(self):
        try:
            shutil.rmtree(self._remote_dir)
        except AttributeError:
            pass
