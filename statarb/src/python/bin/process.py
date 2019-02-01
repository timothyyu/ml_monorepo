#!/usr/bin/env python
import sys
import os
import os.path
import config
import traceback
import datetime
from optparse import OptionParser

import util
import datafiles
import newdb

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--source", dest="source")
    parser.add_option("-m", "--maxfiles", dest="maxfiles", type=int, default=1000)
    parser.add_option("-d", "--debug", default=False, action="store_true", dest="debug")
    parser.add_option("-p", "--print", default=False, action="store_true", dest="stdout")
    parser.add_option("-f", "--files", dest="files")
    parser.add_option("-b","--database",dest="db",default="pri")
    parser.add_option("-i","--ignore_mod_time",dest="ignore_mod_time",type=int,default=0)
    parser.add_option("-l","--process_lag",dest="lag",type=float)
    (options, args) = parser.parse_args()

    assert options.ignore_mod_time in (0,1,2)

    if options.debug:
        util.set_debug()
    else:
        util.set_log_file("all",True)

    if options.db=="pri":
        newdb.init_db()
        database = newdb.get_db()
    elif options.db=="sec":
        newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
        database = newdb.get_db()
    else:
        util.error("Valid database choices are [pri|sec]")
        sys.exit(1)

    # Check for previously running instance
    if not database.getProcessedFilesLock():
        util.warning("Not processing, previous instance running")
        sys.exit(1)

        #XXX may want to precache seen files for speed in loading
    try:
        for source in options.source.split("+"):
            util.info("Processing source %s" % source)    
            from data_sources.file_source import FileSource
    
            util.info("Indexing new files for %s" % source)
            fs = FileSource()
            files = []
            sconfig = config.load_source_config(source)
        
            # List files
            fs.cwd("%s/%s" % (os.environ['DATA_DIR'], sconfig['local_dir']))
            if (options.files is not None):
                files_regex = options.files
            elif sconfig["exec_regex"] is not None:
                files_regex = sconfig["exec_regex"]
            else:
                files_regex = sconfig["local_regex"]
            listing = fs.list_recursive(files_regex + "\.info", sizes=False)
        
            # Load set of seen files
            util.info("Fetching processed files for %s" % source)
            seen = database.getProcessedFiles(source)
            
            util.info("Intersecting...")
            for row in listing:
                util.debug("Looking at info: %s" % row[0]);
                file_path_info = row[0]
                file_path = os.path.normpath(file_path_info[0:-5])
                #file_path_rel = file_path.replace("%s/%s/" % (os.environ["DATA_DIR"], sconfig['local_dir']), "")
                file_path_rel = os.path.relpath(file_path, "/".join((os.environ["DATA_DIR"], sconfig["local_dir"])))
                if file_path_rel not in seen:
                    info = datafiles.read_info_file(file_path)
                    # If we don't have reliable acquisition times (first fetch), use modified timestamp
                    if info['date_last_absent'] is None:
                        date_released = info['date_modified']
                    else:
                        date_released = info['date_first_present']
                    
                    #if we are processing using lag, do not add file
                    if options.lag is not None and (util.now()-util.convert_date_to_millis(datetime.timedelta(days=options.lag))<util.convert_date_to_millis(date_released)):
                        continue
                    
                    util.info("Found new file:< %s" % file_path)
                    files.append({'path': file_path, 'path_rel': file_path_rel, 'date': (date_released, info['date_modified'])})

            util.info("Found %d files" % len(files))
            if len(files) == 0:
                util.warning("Done indexing, no files found")
                continue

            #XXX should sort by filename i think for closely timed files
            files.sort(key=lambda x: (x['date'],x['path']))

            util.info("Done indexing, starting processing")
            numfiles = 1
            for file in files:                
                if numfiles > options.maxfiles:
                    util.warning("Max files reached!")
                    break
                numfiles += 1

                database.start_transaction()
                try:
                    util.info("[{}]: Processing {}".format(datetime.datetime.now(), file['path']))
                    if options.stdout:
                        print "[{}]: Processing {}".format(datetime.datetime.now(), file['path'])
                        
                    ###############
                    #code to handle files with mod time less than already processed files. signifies a potential problem
                    previousFile=database.getLastProcessedFileTuple(source)
                    previousModTime=previousFile["date_modified"] if previousFile is not None else None
                    
                    if previousModTime is not None and util.convert_date_to_millis(file["date"][1])<previousModTime-util.convert_date_to_millis(datetime.timedelta(minutes=45)):
                        util.error("Encountered file {} has mod_time {} before most recently processed file's mod time {}".format(file["path"],file["date"][1],util.convert_millis_to_datetime(previousModTime)))
                        if options.ignore_mod_time==2:
                            util.error("Fake processing file {}".format(file["path"]))
                            database.addProcessedFiles(source,file["path_rel"],None,file["date"][1],False)
                            database.commit()
                            continue
                        elif options.ignore_mod_time==1:
                            util.error("Proceeding with processing file {}".format(file["path"]))
                            pass
                        else:
                            util.error("Not proceeding with processing due to {} mod_time".format(file["path"]))
                            database.rollback()
                            break
                    ###############
                    
                    #rowStats1=database.getRowStats()
                    attStats1=database.cloneAttributeStats()
                    processingStart = util.now()
                    exec "import data_handlers." + sconfig["format"]
                    exec "data_handlers." + sconfig['format'] + ".process(file['path'], source)"
                except:
                    util.error("Failed loading %s, rolling back transaction!" % file['path'])
                    traceback.print_exc(util.LOGFILE)
                    database.rollback()
                    break
                else:
                    #database.print_changes()
                    if util.DEBUG:
                        database.rollback()                 
                    else:
                        # Update source seen file
                        processingEnd = util.now()
                        attStats2=database.cloneAttributeStats()
                        #rowStats2=database.getRowStats()
                        try:
                            database.addProcessedFiles(source, file['path_rel'], processingEnd - processingStart,util.convert_date_to_millis(file["date"][1]),True)
                            database.addProcessedFileAttributeStats(source, file['path_rel'], attStats1, attStats2)
                        except:
                            util.error("Failed finalizing %s after loading, rolling back transaction!" % file['path'])
                            traceback.print_exc(util.LOGFILE)
                            database.rollback()
                            break
                        else:
                            database.commit()
    finally:
        database.releaseProcessedFilesLock()
        util.close_log_file()
