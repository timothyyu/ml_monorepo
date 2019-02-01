#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SEC=$1
ATTR=$2
DATE=$3

$JAVA ase.data.widget.SQLEstimateWidget $SEC $ATTR $DATE
