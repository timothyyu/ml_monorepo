import datetime
import shutil
import tempfile
import cPickle
import os

import util
import flyscrape
from file_source import FileSource

class FlySource(FileSource):
    def __init__(self):
        fly_file = "%s/fly.last" % (os.environ["SCRAP_DIR"])
        try:
            fly_last = cPickle.load(open(fly_file, 'rb'))
        except IOError:
            fly_last = None
        if (fly_last is None or fly_last[0] != datetime.date.today()):
            fly_last = [datetime.date.today(), 0]
        # Grab data
        stories = flyscrape.get_stories('bdkearns', 'd0lemite', fly_last[1])
        util.info("Found %d stories on flyonthewall" % len(stories))
        if len(stories) == 0:
            return
        first = int(stories[0].split("|")[1])
        last = int(stories[len(stories)-1].split("|")[1])
        assert (last-first+1) == len(stories)
        # Save data to temp dir
        tempdir = tempfile.mkdtemp(dir=os.environ['TMP_DIR'])
        f = open("%s/fly-%s.%d-%d.txt" % (tempdir, datetime.date.today().strftime("%Y%m%d"), first, last), "w")
        f.write("\n".join(stories))
        f.close()
        self._remote_dir = tempdir
        fly_last[1] = last
        cPickle.dump(fly_last, open(fly_file, 'wb'))

    def cwd(self, remote_dir):
        pass

    def __del__(self):
        try:
            shutil.rmtree(self._remote_dir)
        except AttributeError:
            pass
