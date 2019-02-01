#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

TMPFILE=$RUN_DIR/scrap/livecalc.running
if [ -e $TMPFILE ]; then
    echo LiveCalc may already be running!
    exit 1
fi
touch $TMPFILE

cp $CONFIG_DIR/calc.prod.cfg $RUN_DIR/calc.cfg

LOGFILE=$LOG_DIR/livecalc.$STRAT.$$.log

JAVA_ARGS="-Xmx6000m -XX:+AggressiveOpts -XX:+UseCompressedOops"
$JAVA $JAVA_ARGS ase.apps.LiveCalc -location $RUN_DIR -log $LOGFILE

rm -f $TMPFILE

exit $?
