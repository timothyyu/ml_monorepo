#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/useq-live

$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --pstats
$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --mupstats
$JAVA ase.apps.DailyManager --all --exchange $PRIMARY_EXCHANGE --location $LOCATION --perf --file
$JAVA ase.apps.DailyManager --all --exchange $PRIMARY_EXCHANGE --location $LOCATION --muperf --file

exit $?
