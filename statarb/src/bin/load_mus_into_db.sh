#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/useq-live

$BIN_DIR/load_mus_into_db.py --day $DATE --location $LOCATION $@

exit $?
