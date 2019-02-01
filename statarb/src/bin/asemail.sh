#!/bin/bash
subj=$@
user=`id -un`
cat - | mail -s "${subj}" $user
