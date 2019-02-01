#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

BACKUP_MACHINE=asestudy1.waltham
BARS_DIR=$DATA_DIR/bars

rsync -avuzb $BARS_DIR/$DATE $BACKUP_MACHINE:$BARS_DIR

exit $?
