#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

HORIZON=5

#get first calcres of day and generate mus
FIRST_CALCRES=`ls -tr $RUN_DIR/calcres/calcres.*_13[345]* | head -1`
FIRST_CALCRES=$RUN_DIR/calcres/$FIRST_CALCRES
LOG_FILE=$LOG_DIR/qcc_report.$$.log

mkdir -p $RUN_DIR/mus

$JAVA ase.calculator.Forecast $FIRST_CALCRES $CONFIG_DIR/opt.prod.cfg $HORIZON 2>$LOG_FILE
Rscript -e  "source('models.R'); qccReport();" >$LOG_FILE 2>$LOG_FILE
cp $REPORT_DIR/qcc/qcc.pdf $TOMCAT_DIR/webapps/ROOT/qcc.pdf

exit $?
