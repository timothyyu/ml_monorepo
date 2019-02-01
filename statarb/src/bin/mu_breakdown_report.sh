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
LOG_FILE=$LOG_DIR/muret_exp.log

$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --mureport --screen --file --log $LOG_FILE

exit $?
