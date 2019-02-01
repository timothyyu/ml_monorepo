#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ $USER != 'ase' ]; then
    echo "Upload requests as user ase"
    exit 1
fi

#assumes that it runs after utc change
DUMP_DATE=`$JAVA ase.data.Exchange tda $PRIMARY_EXCHANGE $DATE -1`

#generate dump file
#$BIN_DIR/req_borrow.py
#
#if [ $? -ne 0 ]; then
#    echo "Failed generating borrow requests"
#    exit $?
#fi

DUMP_FILE=$ROOT_DIR/run/$STRAT/$DUMP_DATE/locate_requests.txt

if [ ! -e "$DUMP_FILE" ]; then
    echo "File $DUMP_FILE is missing"
    exit 1
fi

MORGAN_FORMATTED_FILE=$TMP_DIR/locate_requests.$DUMP_DATE.$$.txt

cat $DUMP_FILE | awk -F '|' 'BEGIN{OFS=","} {print $1,gensub(/\./,"","g",$1),$2}' > $MORGAN_FORMATTED_FILE

if [ ! -e "$MORGAN_FORMATTED_FILE" ]; then
    echo "File $MORGAN_FORMATED_FILE is missing"
    exit 1
fi

$BIN_DIR/data_source_put.py morgan_positions $MORGAN_FORMATTED_FILE /upload/locate_auto_request.txt
rm $MORGAN_FORMATTED_FILE

