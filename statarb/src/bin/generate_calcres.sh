#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ $# == 0 ]; then
    echo "Error: Not enough arguments"
    echo "Usage: ./generate_calcres <name> [<directory>] [<cfg file name>]"
    exit 1
fi

SIMNAME=$1
STARTDATE=$2
ENDDATE=$3
TYPE=$4

SIMDIR=$ROOT_DIR/research/$STRAT/$SIMNAME
mkdir -p $SIMDIR

CALCLOGFILE=$SIMDIR/calc.log
CALC_CFG_FILE=$SIMDIR/calc.cfg

if [ $TYPE == "prod" ]; then
    echo Using prod cfg files
    cp $CONFIG_DIR/calc.prod.cfg $CALC_CFG_FILE
elif [ $TYPE == "sim" ]; then
    #daily calcres calculated at 3:30 (should be traded at 4:00!)
    cp $CONFIG_DIR/calc.sim.cfg $CALC_CFG_FILE
    UNI_DATE=`$BIN_DIR/exchange_date_add $PRIMARY_EXCHANGE $STARTDATE -90`
    START=30
    END=30
    STEPSIZE=1440
    echo Using sim cfg files with date $UNI_DATE
    sed -i "s/\(^uni_date:\)\(..*$\)/\1${UNI_DATE}/" $CALC_CFG_FILE
    sed -i "s/\(^start_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^end_mins_before_close:\)\(..*$\)/\1${END}/" $CALC_CFG_FILE
    sed -i "s/\(^stepsize:\)\(..*$\)/\1${STEPSIZE}/" $CALC_CFG_FILE
elif [ $TYPE == "oneday" ]; then
    #prod calculated at close
    echo Using prod cfg files calculated once
    cp $CONFIG_DIR/calc.prod.cfg $CALC_CFG_FILE
    START=30
    STEPSIZE=1440
    sed -i "s/\(^start_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^end_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^stepsize:\)\(..*$\)/\1${STEPSIZE}/" $CALC_CFG_FILE
elif [ $TYPE == "onedaysim" ]; then
    #prod calculated at close
    echo Using prod cfg files calculated once
    cp $CONFIG_DIR/calc.sim.cfg $CALC_CFG_FILE
    START=30
    STEPSIZE=1440
    UNI_DATE=`$BIN_DIR/exchange_date_add $PRIMARY_EXCHANGE $STARTDATE -90`
    sed -i "s/\(^uni_date:\)\(..*$\)/\1${UNI_DATE}/" $CALC_CFG_FILE
    sed -i "s/\(^start_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^end_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^stepsize:\)\(..*$\)/\1${STEPSIZE}/" $CALC_CFG_FILE
elif [ $TYPE == "hourly" ]; then
    echo Using sim cfg files for hourly calcres
    cp $CONFIG_DIR/calc.sim.cfg $CALC_CFG_FILE
    UNI_DATE=`$BIN_DIR/exchange_date_add $PRIMARY_EXCHANGE $STARTDATE -90`
    START=360
    END=0
    STEPSIZE=60
    echo Using sim cfg files with date $UNI_DATE
    sed -i "s/\(^uni_date:\)\(..*$\)/\1${UNI_DATE}/" $CALC_CFG_FILE
    sed -i "s/\(^start_mins_before_close:\)\(..*$\)/\1${START}/" $CALC_CFG_FILE
    sed -i "s/\(^end_mins_before_close:\)\(..*$\)/\1${END}/" $CALC_CFG_FILE
    sed -i "s/\(^stepsize:\)\(..*$\)/\1${STEPSIZE}/" $CALC_CFG_FILE    
else 
    echo Using custom cfg files
    if [ ! -f $CALC_CFG_FILE ]; then
        exit "No cfg files found!!"
    fi
fi

sed -i "s/\(^startdate:\)\(..*$\)/\1${STARTDATE}/" $CALC_CFG_FILE
sed -i "s/\(^enddate:\)\(..*$\)/\1${ENDDATE}/" $CALC_CFG_FILE

rm -f $SIMDIR/calcres/*

JAVA_ARGS="-XX:+AggressiveOpts -XX:+UseCompressedOops -XX:+OptimizeStringConcat"
$JAVA $JAVA_ARGS ase.apps.SimCalc -location $SIMDIR 2> $CALCLOGFILE
if [ $? -ne 0 ]; then
    echo Failed Calculation
    tail $CALCLOGFILE
    exit 1
fi

exit $?
