#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SEC=$1

MUS_DIR=$RUN_DIR/calcres/
MUS_FILE=`ls -rt $MUS_DIR | tail -1`
MUS_FILE=$MUS_DIR/$MUS_FILE

echo Looking at $MUS_FILE

zgrep "^"$1"|" $MUS_FILE | grep 'F:' | sort -n -r -t\| -k5,5 | $BIN_DIR/align.pl

exit 1
