#!/bin/bash

source /q/work/sean/prod/bin/include.sh

START=$1
shift
END=$1
shift
FCAST=$1
shift

REP_FILE=${START}_${END}.rep
/q/work/sean/prod/bin/ssim.py --start $START --end $END --fcast .:$FCAST:1 $* | tee $REP_FILE
