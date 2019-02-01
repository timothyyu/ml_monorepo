#!/usr/bin/env python
import sys
import os
import datetime
import dateutil
import pytz
import cPickle
import hashlib
import random
import time
import re
from optparse import OptionParser

import config
import util
from data_sources.data_source import DataSourceError

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--source", dest="source")
    parser.add_option("-m", "--maxfiles", default=100, dest="maxfiles")
    parser.add_option("-a", "--maxage", default=5, dest="maxage")
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug")
    (options, args) = parser.parse_args()

    if options.debug:
        util.set_debug()
    else:
        util.set_log_file(options.source,True)

    lock_f = util.lock(options.source) #Create a lock
    config = config.load_source_config(options.source) #Load config file for source 
    time_file = "%s/%s/%s.time" % (os.environ["DATA_DIR"], config["local_dir"], options.source)

    util.info("Acquiring data from %s" % options.source)

    try:
        # Read last check time
        try:
            last_time = cPickle.load(open(time_file, 'rb'))
        except IOError:
            last_time = ""

        t = random.random()*15
        time.sleep(t)
        util.info( "Checking (after waiting %ds)" % t)

        # Connect
        if (config["method"] == "ftp"):
            from data_sources.ftp_source import FTPSource
            source = FTPSource(config["host"], config["user"], config["pass"], config["tz"])
        elif (config["method"] == "sftp"):
            from data_sources.sftp_source import SFTPSource
            source = SFTPSource(config["host"], config["user"], config["pass"])
        elif (config["method"] == "file"):
            from data_sources.file_source import FileSource
            source = FileSource()
        elif (config["method"] == "yahoo"):
            from data_sources.yahoo_source import YahooSource
            source = YahooSource()
        elif (config["method"] == "fly"):
            from data_sources.fly_source import FlySource
            source = FlySource()
        elif (config["method"] == "yearn"):
            from data_sources.yearn_source import YEarnSource
            source = YEarnSource()
        elif (config["method"] == "shortsq"):
            from data_sources.shortsq_source import ShortSqSource
            source = ShortSqSource()
        elif (config["method"] == "oli_buybacks"):
            from data_sources.oli_source import OliSource
            source = OliSource()
        elif (config["method"] == "newsscope_sftp"):
            from data_sources.newsscope_source import NewsScopeSFTPSource
            source = NewsScopeSFTPSource(config["host"], config["user"], config["pass"], options.maxage)
        else:
            raise ValueError("Unknown method in config file: %s" % config['method'])

        this_time = datetime.datetime.now(pytz.timezone("UTC"))

        # List files
        for sub_dir in config["sub_dirs"]:
            sdir = config["remote_dir"] + "/" + sub_dir
            util.info( "Looking in %s" % sdir )
            source.cwd(sdir)
            listing = source.list(config["regex"])
            filecnt=0
            
            for info in listing:
                filename = info[0]
                size = info[1]
                util.info( "Looking at file: %s" % filename )
                
                # Ingore exceptions because sometimes FTP mod time failed when new files were being uploaded
                mod_time = source.modtime(filename)
                if mod_time is None:
                    util.warning( "Could not get mod time of %s, skipping file" % filename)
                    continue

                local_filename = mod_time.strftime(config["prefix"])
                local_filename += filename if options.source != "newsscope" else filename.split("/")[-1] + ".xml.gz"
                if options.source == "bberg2" and filename.count(".enc")>0:
                    local_filename = local_filename.replace(".enc","")
                # Add a hash of the timestamp for uniqueness/detecting modified files
                hash = hashlib.md5()
                hash.update(mod_time.__str__())
                hash.update(size.__str__())
                local_filename += ".%s" % hash.hexdigest()[0:8]
                local_path = "%s/%s/%s/%s/%s" % (os.environ["DATA_DIR"], config["local_dir"], mod_time.strftime("%Y%m%d"), sub_dir, local_filename)
                
                # If we don't have the file or it is incomplete
                util.info("Looking for local file %s" % local_path)
                if options.source == "bberg2" and os.path.isfile(local_path) and abs(os.path.getsize(local_path) - size) < 50:
                    util.info("We already have file %s" % local_path)
                    continue
                if options.source == "newsscope" and os.path.isfile(local_path): #fuckup is a possibility if Sanjay fuck's up
                    util.info("We already have file %s" % local_path)
                    continue
                if os.path.isfile(local_path) and os.path.getsize(local_path) == size:
                    util.info("We already have file %s" % local_path)
                    continue
                
                if config["flag"] != "":
                    # Check for flag file if necessary
                    flag = config["flag"].split(":")
                    if (len(flag) == 1):
                        flag_files = source.list(re.escape(filename + flag[0]))
                    elif (len(flag) == 2):
                        flag_files = source.list(re.escape(filename.replace(flag[0], flag[1])))
                    else:
                        raise ValueError("Invalid flag field in config file")

                    if (len(flag_files) == 0):
                        util.warning( "Not acquiring %s (flag file doesn't exist)" % filename)
                        continue

                if mod_time + dateutil.relativedelta.relativedelta(days=int(options.maxage)) < this_time:
                    util.warning("File too old to retrieve...")
                    continue

                if config["modtime_grace"] >= 0:
                    # Sanity check that mod_time is between last_time and this_time
                    # with a configurable grace period -- we are looking for localtime/UTC mixups (4-5 hour shifts)
                    if (last_time != "" and mod_time < (last_time - dateutil.relativedelta.relativedelta(hours=config["modtime_grace"]))) or mod_time > (this_time + dateutil.relativedelta.relativedelta(hours=config["modtime_grace"])):
                        util.error( "filename: %s" % filename )
                        util.error( "last acquire time: %s" % last_time )
                        util.error( "now: %s" % this_time )
                        util.error( "File mod time: %s" % mod_time )
                        continue
#                        raise ValueError("mod_time was not between last_time and this_time (remote server's timezone shifted unexpectedly?)")

                if (filecnt > options.maxfiles):
                    util.error("Not acquiring file, hit max of %d" % options.maxfiles)
                    continue

                #ok, let's get it
                sts = "Acquiring %s -> %s" % (filename, local_filename) 
                util.info( sts )
                #print sts

                if options.debug: continue

                delayed_raise = False
                if (os.path.isfile(local_path)):
                    rest = os.path.getsize(local_path)
                else:
                    rest = None

                try:
                    source.copy(filename, local_path, rest)
                    filecnt += 1
                except DataSourceError:
                    if (not os.path.isfile(local_path)) or (os.path.getsize(local_path) != size):
                        raise
                    else:
                        delayed_raise = True
                
                if options.source == "bberg2" and filename.count(".enc")>0:
                    util.shellExecute('/apps/hyp2/src2/BoBB/des/des -D -k "7RV.K(,1" {} $TMP_DIR/bb.temp; mv $TMP_DIR/bb.temp {}'.format(local_path, local_path))
                
                open(local_path + '.info', 'w').write("%s\n%s\n%s\n%s\n%s\n" % (last_time, this_time, mod_time, size.__str__(), util.calc_md5sum_of_fh(open(local_path, 'rb'))))
                os.system("chmod 440 %s %s.info" % (local_path, local_path))

                if delayed_raise:
                    util.warning( "Received a data source error, exiting (but gracefully, as we got the whole file)" )
                    sys.exit(0)

        # Save last check time
        cPickle.dump(this_time, open(time_file, 'wb'))
    
    finally:
        lock_f.release()
