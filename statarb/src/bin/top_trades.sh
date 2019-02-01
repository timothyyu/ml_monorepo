#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

ORDER_DIR=$RUN_DIR/orders/
ORDER_FILE=`ls -tr $ORDER_DIR/orders.2* | tail -1`
if [ $# -gt 0 ]; then
    TYPE=$1
    ORDER_FILE=`ls -tr $ORDER_DIR/orders.$TYPE.2* | tail -1`
fi

OUTPUT=$TMP_DIR/toptrades.tmp

echo Looking at $ORDER_FILE
head -1 $ORDER_FILE | cut -d\| -f 3,5,6,7,8,9,10 > $OUTPUT
grep -v secid $ORDER_FILE | sort -nr -t\| -k6,6 | cut -d\| -f 3,5,6,7,8,9,10 | head -10 >> $OUTPUT

cat $OUTPUT | $BIN_DIR/align.pl

rm -f $OUTPUT

exit 1
