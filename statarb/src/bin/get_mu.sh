#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

SEC=$1

MUS_DIR=$RUN_DIR/mus/
MUS_FILE=`ls -rt $MUS_DIR/mus.2* | tail -1`

if [ $# -gt 1 ]; then
    TYPE=$2
    MUS_FILE=`ls -rt $MUS_DIR/mus.$TYPE.2* | tail -1`
fi

echo Looking at $MUS_FILE

grep "^$1|" $MUS_FILE | gawk -F\| '{print $1"|"$2"|"$3*10000.0}' | sort -n -r -t\| -k3,3 | $BIN_DIR/align.pl

exit 0
