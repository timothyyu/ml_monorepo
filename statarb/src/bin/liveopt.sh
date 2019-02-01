#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

TMPFILE=$RUN_DIR/scrap/liveopt.running
if [ -e $TMPFILE ]; then
    echo LiveOpt may already be running!
    exit 1
fi
touch $TMPFILE

cp $CONFIG_DIR/opt.prod.cfg $RUN_DIR/opt.cfg
cp $ROOT_DIR/run/$STRAT/overrides.txt $RUN_DIR/overrides.txt

if [ $STRAT = "useq-test" ]; then
    CALCRES_DIR=$RUN_DIR/calcres
    LIVE_DIR=$ROOT_DIR/run/useq-live/$DATE
    mkdir -p $CALCRES_DIR
    cp $LIVE_DIR/* $RUN_DIR
    cp $LIVE_DIR/calcres/* $CALCRES_DIR
fi

LOGFILE=$LOG_DIR/liveopt.$STRAT.$$.log

JAVA_ARGS="-Xmx1500m -XX:+AggressiveOpts"

$JAVA $JAVA_ARGS ase.apps.LiveOpt -location $RUN_DIR -log $LOGFILE -exchange $PRIMARY_EXCHANGE

rm -f $TMPFILE

exit $?
