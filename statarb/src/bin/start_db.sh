#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

#make sure it's not already running first!

if [ "$USER" != "ase" ]; then
	exit "NEED TO START DB AS ASE"
fi

if [ "$HOSTNAME" = "$DB_HOSTNAME" ]; then
	cd $INSTALL_DIR/mysql; nohup ./bin/mysqld_safe --defaults-file=$DB_SERVER_CONFIG_FILE >/dev/null 2>/dev/null &
elif [ "$HOSTNAME" = "$SEC_DB_HOSTNAME" ]; then
	cd $INSTALL_DIR/mysql; nohup ./bin/mysqld_safe --defaults-file=$SEC_DB_SERVER_CONFIG_FILE >/dev/null 2>/dev/null &
else
	exit "YOU SHOULD TRY TO START A DB SERVER ON THE APPROPRIATE MACHINE"
fi

# root/root1
# asereport/asereport1
# sean/sean1
# aseprod/asepass1
