#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SEC=$1

grep "|$SEC|" $TICKER_FILE

CALCRES_DIR=$RUN_DIR/calcres/
CALCRES_FILE=`ls -rt $CALCRES_DIR | tail -1`
CALCRES_FILE=$CALCRES_DIR/$CALCRES_FILE

echo Looking at $CALCRES_FILE

zgrep "^$1|" $CALCRES_FILE | sort -t\| -k2,2 | $BIN_DIR/m2d.py | $BIN_DIR/align.pl

exit 1
