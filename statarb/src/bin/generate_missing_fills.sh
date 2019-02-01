#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/useq-live

python $BIN_DIR/process_exec_logs.py -d --day $DATE --location $LOCATION --infraRecon
mv $RUN_DIR/fills.$DATE.txt $RUN_DIR/fills.$DATE.txt.original
mv $RUN_DIR/fills.$DATE.txt.tmp $RUN_DIR/fills.$DATE.txt
