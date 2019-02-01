#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SIM_DIR=$1
LOG_FILE=$SIM_DIR/qcc.log

Rscript -e  "source('models.R'); qccReport('$SIM_DIR');" >$LOG_FILE 2>$LOG_FILE

exit $?
