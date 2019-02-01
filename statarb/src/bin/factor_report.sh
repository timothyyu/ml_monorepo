#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

REPDATE=$DATE
if [ $# -gt 0 ]; then
    REPDATE=$1
fi
TYPE="--factor"
if [ $# -gt 1 ]; then
    TYPE=$2
fi

LOCATION=$ROOT_DIR/run/$STRAT
LOG_FILE=$LOG_DIR/factor_exp.log
#OUTPUT=$TMP_DIR/factor.$$.tmp
#REPORT_DIR=$REPORT_DIR/factors/$REPDATE/
#mkdir -p $REPORT_DIR
#REPORT_FILE=$REPORT_DIR/factors.$REPDATE.txt

#echo "factor|notional exposure|% exposure|day pnl|week pnl|month pnl|total pnl|since|" > $OUTPUT
#$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --factor --screen --log $LOG_FILE 2> /dev/null | grep -v factor | sort -t\| -n -r -k4,4 >> $OUTPUT
#cat $OUTPUT | $BIN_DIR/align.pl | tee $REPORT_FILE
#rm -f $OUTPUT

$JAVA ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION $TYPE --screen --file --log $LOG_FILE

exit $?
