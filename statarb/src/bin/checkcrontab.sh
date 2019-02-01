#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

TMPFILE=$TMP_DIR/checkcrontab.$$.tmp
MACHINE=`echo $HOSTNAME | cut -d \. -f 1-2`
crontab -l | diff -u - $ROOT_DIR/cron/$MACHINE.cron > $TMPFILE
RESULT=$?

if [ -s $TMPFILE ]
then
    echo "crontab not up to date on $MACHINE:"
    cat $TMPFILE
    RESULT=1
fi

rm -f $TMPFILE
exit $RESULT
