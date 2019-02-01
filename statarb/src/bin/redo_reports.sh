#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/useq-live

$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --pnl --file
$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --intra_stats
$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --factor --file
$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --risk_attr --file
$JAVA ase.apps.DailyManager --yesterday --exchange $PRIMARY_EXCHANGE --location $LOCATION --mureport --file

exit $?
