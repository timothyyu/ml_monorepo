#!/usr/bin/env python

import subprocess
import sys
import os

''' execute in shell and wait for completion '''
os.chdir(os.environ['ASE_GIT_REPO'])

''' run an fsck first '''
shell=subprocess.Popen("git fsck --full",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
shell.wait()

''' run the log command '''
shell=subprocess.Popen("git log --since=yesterday --name-status",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
shell.wait()

''' print output '''
outputMessage="".join(shell.stdout.readlines())
errorMessage="".join(shell.stderr.readlines())

if len(errorMessage)>0:
    sys.stderr.write(errorMessage);
else:
    print outputMessage

