#!/usr/bin/env python
import time
import os
import sys
import util
import re

util.niceme()

sizes = dict()

if __name__ == "__main__":    
    first_loop = True
    start = time.time()
    while 1:
        lines_to_mail = ""
        filenames = os.popen("ls {}/*.log".format(os.environ["LOG_DIR"])).readlines()
        for filename in filenames:
            filename = filename[0:-1]
            if os.path.basename(filename).startswith("."):
                continue
            new_size = os.path.getsize(filename)
            if not sizes.has_key(filename):
                if first_loop:
                    sizes[filename] = new_size
                else:
                    sizes[filename] = 0
            if new_size != sizes[filename]:
                f = file(filename)
                f.seek(sizes[filename])
                found_errors = False
                for line in f:
                    if re.search("SEVERE", line):
                        lines_to_mail += filename+": "+line
                        found_errors = True
                f.close()
                sizes[filename] = new_size
                if found_errors:
                    lines_to_mail += "\n"
        if len(lines_to_mail) > 0: 
            util.email("Log Checker", lines_to_mail)
        lines_to_mail= ""
        time.sleep(5 * 60)
        first_loop = False
        if time.time() - start > 60*60*12: sys.exit();
