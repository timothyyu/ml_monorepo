#! /bin/bash

if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ "$1" = 'sec' ]; then
	$INSTALL_DIR/mysql/bin/mysqladmin -u root -h $SEC_DB_HOSTNAME -P 3309 -p $2
elif [ "$1" = 'pri' ]; then
	$INSTALL_DIR/mysql/bin/mysqladmin -u root -h $DB_HOSTNAME -P 3309 -p $2
else
	exit "Please select a database [pri|sec]"
fi
