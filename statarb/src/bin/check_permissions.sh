#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

TEMP_FILE=/tmp/perm.$$
cd $ROOT_DIR

find . -path './bkup/homedirs' -prune -o -perm +007 -print | 
grep -v "./install/" | 
grep -v "run/useq-live/uni.txt" |
grep -v "git/src.git/hooks/commit-msg" |
grep -v "git/src.git/hooks/pre-commit" |
grep -v "filters/filter" |
grep -v "exec/client-lite/headers/Configurable.h" > $TEMP_FILE

if [ -s $TEMP_FILE ]; then
    echo "The following files have some permissions granted to other as well:"
    cat $TEMP_FILE
    echo ""
fi

find . -path './bkup/homedirs' -prune -o ! -perm -440 -print |
grep -v "nohup.out"  > $TEMP_FILE
if [ -s $TEMP_FILE ]; then
    echo "The following files do not have read permission for user and/or group:"
    cat $TEMP_FILE
    echo ""
fi

find . -path './bkup/homedirs' -prune -o ! -group ase -print > $TEMP_FILE
if [ -s $TEMP_FILE ]; then
    echo "The following files are owned by a group other than ase:"
    cat $TEMP_FILE
    echo ""
fi

rm $TEMP_FILE

exit 0
