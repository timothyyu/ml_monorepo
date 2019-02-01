#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

SIMNAME=$1
INTERVAL=$2
SIMDIR=$RESEARCH_DIR/$SIMNAME
LOGFILE=$SIMDIR/intraday.log

#JAVA_ARGS="-Xmx1500m"
JAVA_ARGS=""

rm -f $SIMDIR/calcres_intraday/*

$JAVA $JAVA_ARGS ase.apps.IntradayCalcresGenerator $SIMDIR $INTERVAL 2> $LOGFILE

exit $?
