#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

STOP_TIME=1625
while [ `date +%H%M` -lt $STOP_TIME ]; do
  python $BIN_DIR/exec_report.py
  sleep 60
done

