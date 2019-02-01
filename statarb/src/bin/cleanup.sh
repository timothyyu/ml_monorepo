#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

TMPFILE=$TMP_DIR/cleanup.$$.tmp

find $LOG_DIR -name *.log -ctime +5 >> $TMPFILE

if [ -s $TMPFILE ]; then
    echo Deleting Files
    cat $TMPFILE
    cat $TMPFILE | xargs rm -f
fi

exit 0

