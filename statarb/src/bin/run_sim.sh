#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

SIMNAME=$1
TYPE=$2
DELAY=$3

if [ $# -lt 3 ]; then
    echo need more arguments!
    exit 1
fi

RITYPE="eod"
if [ $# -gt 3 ]; then
    RITYPE=$4
fi

MARGINALS=""
REPORT_TYPE="--pnl"

`echo "$*" | grep -q 'marginal'`
if [ $? == 0 ]; then
    MARGINALS="$MARGINALS -marginals -threads 3"
    REPORT_TYPE="--marginals_pnl"
fi
`echo "$*" | grep -q 'singles'`
if [ $? == 0 ]; then
    MARGINALS="$MARGINALS -singles -threads 3"
    REPORT_TYPE="--singles_pnl"
fi

SIMDIR=$ROOT_DIR/research/$STRAT/$SIMNAME
mkdir -p $SIMDIR
rm -Rf $SIMDIR/stats/*
rm -Rf $SIMDIR/positions/*
rm -Rf $SIMDIR/orders/*
rm -Rf $SIMDIR/mus/*
rm -Rf $SIMDIR/fills/*
rm -f $SIMDIR/scrap/*
rm -f $SIMDIR/pnl.txt
rm -Rf $SIMDIR/pnl_reports
REPORTDIR=$ROOT_DIR/reports/$STRAT/$SIMNAME

SIMLOGFILE=$SIMDIR/sim.log
REPLOGFILE=$SIMDIR/rep.log

OPT_CFG_FILE=$SIMDIR/opt.cfg

if [ $TYPE == "prod" ]; then
    CFILE=$CONFIG_DIR/opt.prod.cfg
    echo Using prod cfg files: $CFILE
    cp $CFILE $OPT_CFG_FILE
elif [ $TYPE == "sim" ]; then
    CFILE=$CONFIG_DIR/opt.prod.cfg
    SOURCE=msglobal
    MAX_ITER=3000
    MICRO=false
    sed -i "s/\(^borrow_source:\)\(..*$\)/\1${SOURCE}/" $CFILE
    sed -i "s/\(^max_iter:\)\(..*$\)/\1${MAX_ITER}/" $CFILE
    sed -i "s/\(^microopt:\)\(..*$\)/\1${MICRO}/" $CFILE
    echo Using sim cfg files: $CFILE
    cp $CFILE $OPT_CFG_FILE
else 
    echo Using custom cfg files
    if [ ! -f $OPT_CFG_FILE ]; then
        exit "No cfg files found!!"
    fi
fi

$JAVA ase.apps.SimOpt -location $SIMDIR $MARGINALS -muportfolios -fill_delay_mins $DELAY 2> $SIMLOGFILE
if [ $? -ne 0 ]; then
    echo Failed Simulation
    tail $SIMLOGFILE
    exit 1
fi
$JAVA ase.apps.SimManager --simdir $SIMDIR --reportdir $SIMDIR --log $REPLOGFILE $REPORT_TYPE --rtype $RITYPE
if [ $? -ne 0 ]; then
    echo Failed Reporting
    exit 1
fi

mkdir -p $REPORTDIR
cp $SIMDIR/pnl.txt $REPORTDIR/pnl.txt

cat $SIMDIR/pnl.txt | $BIN_DIR/asemail.sh "sim result: $SIMNAME"
cat $SIMDIR/pnl.txt

exit 0

