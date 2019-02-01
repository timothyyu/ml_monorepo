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

LOCATION=$ROOT_DIR/run/$STRAT
LOG_FILE1=$LOG_DIR/slip.log
LOG_FILE2=$LOG_DIR/tslip.log

JAVA_ARGS="-Xmx8000m -XX:+UseCompressedOops" 
$JAVA $JAVA_ARGS ase.apps.DailyManager --day $REPDATE --exchange $PRIMARY_EXCHANGE --location $LOCATION --slip --screen --file --log $LOG_FILE1

# Adding a break line to separate things broken by orders and those broken by fills
sed -i "s/tactic_CROSS/\ntactic_CROSS/" $REPORT_DIR/slippage/$DATE/slip.$DATE.txt 

exit $?
