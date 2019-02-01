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
LOG_FILE=$LOG_DIR/live_pnl.$$.log

REPORT_DIR=$REPORT_DIR/pnl/$REPDATE/
mkdir -p $REPORT_DIR
REPORT_FILE=$REPORT_DIR/pnl.$REPDATE.txt

$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --livepnl --log $LOG_FILE --file 

exit $?

