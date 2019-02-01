#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

head -2 $REPORT_DIR/pnl/$DATE/pnl.$DATE.txt

exit 0
