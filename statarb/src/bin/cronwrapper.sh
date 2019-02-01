#!/bin/bash

export ROOT_DIR=$1
export STRAT=$2
shift
shift

. $ROOT_DIR/bin/include.sh

STDOUT_FILE=$TMP_DIR/cron.$$.stdout.tmp
STDERR_FILE=$TMP_DIR/cron.$$.stderr.tmp
MACHINE=`echo $HOSTNAME | tr '[:lower:]' '[:upper:]' | cut -d \. -f 1`

$* >$STDOUT_FILE 2>$STDERR_FILE
RES=$?

if [ -s $STDOUT_FILE ]; then
    cat $STDOUT_FILE | head -1000 | $ROOT_DIR/bin/asemail.sh "$*"
fi

if [ -s $STDERR_FILE ]; then
    cat $STDERR_FILE | head -1000 | $ROOT_DIR/bin/asemail.sh "[ERROR] $*"
fi

rm $STDOUT_FILE
rm $STDERR_FILE

exit $RES
