#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

T1=$1
T2=$2
OUTPUT_DIR=$3

$JAVA ase.apps.DailyManager –location /apps/ase/run/useq-live –exchange $PRIMARY_EXCHANGE –t1 $T1 --t2 $T2 --outputdir $OUTPUT_DIR --enh_calc

exit $?

