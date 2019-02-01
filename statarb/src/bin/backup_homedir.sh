#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

BACKUP_MACHINE=asetrade1.newark
BACKUP_BASE_DIR=/apps/ase/bkup/homedirs/

rsync -avuzb --delete ~ $BACKUP_MACHINE:$BACKUP_BASE_DIR

exit $?
