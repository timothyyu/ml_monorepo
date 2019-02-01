#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

SIM_NAME=$1
shift #take the remainder of parameters to be intra related parameters 

INTRADAY=""
LOG_SUFFIX="log"
HORIZONS="1,2,3,5,10,20,30"
if [ $# -gt 1 ]; then
    echo Running intraday fit
    INTRADAY="$*"
    HORIZONS="10,20,30,60,120"
    LOG_SUFFIX="intraday.log"
fi

SIM_DIR=$ROOT_DIR/research/$STRAT/$SIM_NAME
FIT_DIR=$SIM_DIR/fit
FIT_LOG=$FIT_DIR/logs/fit.generator.$LOG_SUFFIX

mkdir -p $FIT_DIR/logs
echo writing to $FIT_LOG

$JAVA ase.apps.Fit --location $SIM_DIR --horizons $HORIZONS --exchange $PRIMARY_EXCHANGE $INTRADAY $* 2> $FIT_LOG
if [ $? -ne 0 ]; then
    echo Failed Fit
    tail -20 $FIT_LOG
    exit $?
fi

exit 0
