#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

egrep '(SEVERE|ERROR)' $LOG_DIR/*.log

exit 0
