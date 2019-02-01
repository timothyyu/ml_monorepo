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
TYPE="--risk_attr"
if [ $# -gt 1 ]; then
    TYPE=$2
fi

LOCATION=$ROOT_DIR/run/$STRAT
LOG_FILE=$LOG_DIR/risk_attr.log

$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION $TYPE --file --log $LOG_FILE

exit $?
