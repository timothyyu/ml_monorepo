#!/usr/bin/env python

import os

print "Data directory disk usage:"
os.system('df -h %s' % os.environ['DATA_DIR'])
print ''
os.system('du -sh %s/*' % os.environ['DATA_DIR'])

print ''

print "Files acquired since last report:"
#TODO
# report_run = "%s/report.run" % os.environ['RUN_DIR']
# result = os.popen('find %s -newer %s -type f -regex ".*\.[0-9a-f]+"' % (os.environ['DATA_DIR'], report_run)).readlines()
# if len(result): print "".join(sorted(result))
# os.system('touch ' + report_run)
