#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOCATION=$ROOT_DIR/run/$STRAT

$JAVA ase.apps.DailyManager --day $DATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --overrides

exit $?
