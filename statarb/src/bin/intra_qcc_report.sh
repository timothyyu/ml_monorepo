#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOG_FILE=$LOG_DIR/intra_qcc_report.$$.log

mkdir -p $RUN_DIR/mus

Rscript -e  "source('models.R'); qccReport(mode=1);" >$LOG_FILE 2>$LOG_FILE
cp $REPORT_DIR/qcc/intra_qcc.pdf $TOMCAT_DIR/webapps/ROOT/intra_qcc.pdf

exit $?
