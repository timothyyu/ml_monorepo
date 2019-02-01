#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ "$USER" != "ase" ]; then
	exit "NEED TO RUN AS ASE"
fi

MACHINE=`echo $HOSTNAME | cut -d \. -f 1-2`
CRONFILE=$ROOT_DIR/cron/$MACHINE.cron
OLD_CRON=$TMP_DIR/cron.tmp

if [ -e "$CRONFILE" ]; then
   crontab -l > $OLD_CRON
   echo Installing $CRONFILE
   crontab $CRONFILE
   crontab -l | diff - $OLD_CRON
   rm -f $OLD_CRON
else
   exit "File $CRONFILE does not exist"
fi
