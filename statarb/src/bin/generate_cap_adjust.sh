#!/bin/sh
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

$JAVA ase.apps.CapAdjustmentGenerator --to $DATE --from $DATE --exchange $PRIMARY_EXCHANGE --location $RUN_DIR

return $?

