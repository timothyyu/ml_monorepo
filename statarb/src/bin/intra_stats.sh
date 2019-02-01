#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/useq-live

$JAVA ase.apps.DailyManager --day $DATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --log $LOG_DIR/intra_stats.log --intra_stats

exit $?
