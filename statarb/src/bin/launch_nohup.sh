#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

NM=`basename $1`
OUT=$TMP_DIR/$NM.$$.nohup.out
ERR=$TMP_DIR/$NM.$$.nohup.err

echo Running $* to $OUT and $ERR

/usr/bin/nohup $* 1>> $OUT 2>> $ERR  &

exit 0
