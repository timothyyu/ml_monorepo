#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

if [ $# -gt 0 ]; then
    DATE=$1
else
    DATE=`$JAVA ase.data.Exchange tda $PRIMARY_EXCHANGE $DATE -1`
fi
NO_CALCRES="F"
if [ $# -gt 1 ]; then
    NO_CALCRES=$2
fi

SIMNAME=daily_comp/$DATE

SIM_DIR=$ROOT_DIR/research/$STRAT/$SIMNAME
LOGFILE=$LOG_DIR/onedaysim.$$.log
ORIG_START_PORT_FILE=/apps/ase/run/$STRAT/$DATE/sodPort.txt
START_PORT_FILE=$SIM_DIR/sodPort.txt

mkdir -p $SIM_DIR
cp $ORIG_START_PORT_FILE $START_PORT_FILE

if [ $NO_CALCRES = "F" ]; then
    $BIN_DIR/generate_calcres.sh $SIMNAME $DATE $DATE prod > $LOGFILE
fi
#cp $ROOT_DIR/config/opt.intra.cfg $SIM_DIR/opt.cfg
$BIN_DIR/run_sim.sh $SIMNAME prod 9 15

if [ $? -ne 0 ]; then
    cat $LOGILE
    exit 1
fi

cat $SIM_DIR/pnl.txt

SIM_ORDER_FILE=$TMP_DIR/orders.$$.ttmp
cat $SIM_DIR/orders/orders.20* | grep secid | head -1 > $SIM_ORDER_FILE
cat $SIM_DIR/orders/orders.20* | grep -v secid >> $SIM_ORDER_FILE

LIVE_FILLS_FILE=/apps/ase/run/$STRAT/$DATE/fills.$DATE.txt
PERF_FILE=$ROOT_DIR/reports/$STRAT/various/perf.txt
PNL=`grep "^$DATE" $PERF_FILE | cut -d\| -f5`
TPNL=`grep "^$DATE" $PERF_FILE | cut -d\| -f8`
$BIN_DIR/compare_sim_orders.py $SIM_ORDER_FILE $LIVE_FILLS_FILE $SIM_DIR/pnl.txt $PNL $TPNL | tee $SIM_DIR/sim_comp.txt 
RES=$?

mkdir -p $REPORT_DIR/$SIMNAME
REPORT_FILE=$REPORT_DIR/$SIMNAME/sim_comp.txt
cat $SIM_DIR/pnl.txt > $REPORT_FILE
echo >> $REPORT_FILE 
cat $SIM_DIR/sim_comp.txt >> $REPORT_FILE

exit $RES
