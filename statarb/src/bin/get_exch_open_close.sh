#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

EXPECTED_ARGS=2

if [ $# -ne $EXPECTED_ARGS ]; then
  echo "Error: Not enough arguments"
  echo "Usage: ./get_exch_open_close.sh <exchange name> <date>"
  exit 1
fi

$JAVA ase.data.Exchange oc $1 $2

exit $?


