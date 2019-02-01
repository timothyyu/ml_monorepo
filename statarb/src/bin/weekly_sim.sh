#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

if [ $# -gt 0 ]; then
    DATE=$1
fi

#Assume that we run it on a saturday. why on earth do americans consider sunday as the start of the week?
STARTDATE=`$JAVA ase.data.Exchange sow $PRIMARY_EXCHANGE $DATE`
ENDDATE=`$JAVA ase.data.Exchange eow $PRIMARY_EXCHANGE $DATE`
SIMNAME=weeklysim/$DATE

WEEKLY_SIM_DIR=$ROOT_DIR/research/$STRAT/$SIMNAME
ORIG_START_PORT_FILE=/apps/ase/run/$STRAT/$STARTDATE/sodPort.txt
START_PORT_FILE=$WEEKLY_SIM_DIR/sodPort.txt

mkdir -p $WEEKLY_SIM_DIR
cp $ORIG_START_PORT_FILE $START_PORT_FILE

$BIN_DIR/generate_calcres.sh $SIMNAME $STARTDATE $ENDDATE oneday
$BIN_DIR/run_sim.sh $SIMNAME prod eod eod marginals
RES=$?
exit $RES
