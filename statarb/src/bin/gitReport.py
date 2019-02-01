#!/usr/bin/env python

import subprocess
import sys
import os

os.chdir(os.environ['GIT_REPO_BASE'])
repos = os.listdir('.')

outputMessage = ""
errorMessage = ""
for repo in repos:
    os.chdir(repo)
    ''' run an fsck first '''
    shell=subprocess.Popen("git fsck --full",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    shell.wait()

    ''' run the log command '''
    shell=subprocess.Popen("git log --since=yesterday --name-status",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    shell.wait()

    ''' print output '''
    output = "".join(shell.stdout.readlines())
    error  = "".join(shell.stderr.readlines())
    if len(output) > 0:
        outputMessage += "Changes for repo " + repo + "\n\n" + output + "========================\n\n"
    if len(error) > 0:
        errorMessage += "Errors for repo " + repo + "\n\n" + error + "========================\n\n"
    os.chdir('..')

if len(errorMessage)>0:
    sys.stderr.write(errorMessage);
else:
    print outputMessage

