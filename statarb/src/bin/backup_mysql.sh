#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

FILE=$ROOT_DIR/logs/mysql_backup/$DATE.bak
echo Backing up MySQL to $FILE
$INSTALL_DIR/mysql/bin/mysqldump --opt --host=$DB_HOSTNAME --port=3309 --user=root --password=root1 --databases ase> $FILE.$$
RET=$?

if [ $RET = "0" ]; then
    chmod -f 440 $FILE
    cat $FILE.$$ | gzip > $FILE
    rm -f $FILE.$$
    ls -l $FILE
else
    echo "Failed to backup DB"
    exit $?
fi

##should purge old binary logs as well...
#$INSTALL_DIR/mysql/bin/mysql --host=asedb1.jc.tower-research.com --port=3309 --user=root --password=root1 -e "PURGE BINARY LOGS BEFORE '2010-10-01 00:00:00';"

$INSTALL_DIR/mysql/bin/mysqlcheck --host=$DB_HOSTNAME --port=3309 --auto-repair --check --user=root --password=root1 --optimize ase 

exit 0

