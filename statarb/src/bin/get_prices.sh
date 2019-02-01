#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SEC=$1
DATE=$2

$JAVA ase.data.DailyPriceSource $SEC $DATE $PRIMARY_EXCHANGE


