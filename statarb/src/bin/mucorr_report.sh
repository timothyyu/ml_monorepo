#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

REPDATE=$DATE
if [ $# -gt 0 ]; then
    REPDATE=$1
fi

LOCATION=$ROOT_DIR/run/$STRAT
LOG_FILE=$LOG_DIR/mucorr.log

$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --mucorr --log $LOG_FILE

exit $?
