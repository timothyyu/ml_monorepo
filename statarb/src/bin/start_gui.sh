#!/bin/bash

NY=1
if [ -n "`echo $HOSTNAME | grep '.newark'`" ]; then NY=0; fi
if [ -n "`echo $HOSTNAME | grep '.jc'`" ]; then NY=0; fi
if [ -n "`echo $HOSTNAME | grep '.waltham'`" ]; then NY=0; fi

#if [ $NY -eq 0 ]; then
#  echo "Sorry, the GUI can only be run in NY right now"
#  exit 1
#fi

SuperGUI --cfg=ase

exit 0
