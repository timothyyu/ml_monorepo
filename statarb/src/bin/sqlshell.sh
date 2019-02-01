#! /bin/bash

if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ "$1" = 'sec' ]; then
	if [ "$2" = 'root' ]; then
		$INSTALL_DIR/mysql/bin/mysql -u root -h $SEC_DB_HOSTNAME -P 3309 -D ase -proot1
	else
		$INSTALL_DIR/mysql/bin/mysql -u aseprod -h $SEC_DB_HOSTNAME -P 3309 -D ase -pasepass1
	fi
else
	if [ "$2" = 'root' ]; then
		$INSTALL_DIR/mysql/bin/mysql -u root -h $DB_HOSTNAME -P 3309 -D ase -proot1
	else
		$INSTALL_DIR/mysql/bin/mysql -u aseprod -h $DB_HOSTNAME -P 3309 -D ase -pasepass1
	fi
fi
