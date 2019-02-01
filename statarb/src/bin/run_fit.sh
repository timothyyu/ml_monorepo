#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

SIM_NAME=$1
TRIM=0
if [ $# -gt 1 ]; then
    TRIM=$2
fi
WEIGHTED="TRUE"
WNAME="unweighted"
if [ $# -gt 2 ]; then
    if [ $3 = "TRUE" ]; then 
        WNAME="weigted"
        WEIGHTED=$3
    fi
fi
INTRADAY="FALSE"
INAME="daily"
if [ $# -gt 3 ]; then
    if [ $4 = "TRUE" ]; then
        INAME="intra"
        INTRADAY=$4
    fi
fi

SLIM="FALSE"
if [ $# -gt 4 ]; then
    if [ $5 = "TRUE" ]; then
        SLIM="TRUE"
    fi
fi

SIM_DIR=$ROOT_DIR/research/$STRAT/$SIM_NAME
REPORT_DIR=$ROOT_DIR/reports/$STRAT/$SIM_NAME

FIT_DIR=$SIM_DIR/fit
mkdir -p $FIT_DIR
mkdir -p $FIT_DIR/logs

FIT_LOG=$FIT_DIR/fit.$TRIM.$WNAME.$INAME.log
FIT_REP=$FIT_DIR/fit.$TRIM.$WNAME.$INAME.rep

echo writing to $FIT_LOG
echo Running Weigted: $WEIGHTED Trim: $TRIM Intraday: $INTRADAY

echo Massaging files
$BIN_DIR/fit_massage.py $SIM_DIR $INTRADAY $SLIM > $FIT_LOG

echo Running R portion
Rscript -e "source('fit.R'); fit.sim('$SIM_DIR', $WEIGHTED, $TRIM, $INTRADAY, TRUE, '$FIT_REP'); " >> $FIT_LOG
RES=$?

mkdir -p $REPORT_DIR
if [ $INTRADAY == "TRUE" ]; then
    cp $FIT_REP $REPORT_DIR/fit.intra.txt
    cat $REPORT_DIR/fit.intra.txt
else
    cp $FIT_REP $REPORT_DIR/fit.txt
    cat $REPORT_DIR/fit.txt
fi

exit $RES


