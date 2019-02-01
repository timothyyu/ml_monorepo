#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

if [ $# -gt 0 ]; then
    DATE=$1
fi

SIM_NAME=weeklysim/$DATE

$BIN_DIR/generate_intraday_data.sh $SIM_NAME 30
$BIN_DIR/generate_fitres.sh $SIM_NAME
$BIN_DIR/generate_fitres.sh $SIM_NAME -intraday -slim
$BIN_DIR/run_fit.sh $SIM_NAME 0 TRUE FALSE FALSE
$BIN_DIR/run_fit.sh $SIM_NAME 0 TRUE TRUE TRUE

exit $?
