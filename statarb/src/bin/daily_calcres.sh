#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/bin/include.sh
fi

SIMDATE=`$ROOT_DIR/bin/exchange_date_add $PRIMARY_EXCHANGE $DATE -1`
DAILY_SIM_DIR=$ROOT_DIR/run/$STRAT/$SIMDATE
LOGFILE=$LOG_DIR/simcalc.$$.log
ERRFILE=$LOG_DIR/simcalc.$$.err

ORIG_CFG_FILE=$CONFIG_DIR/calc.cfg
CFG_FILE=$DAILY_SIM_DIR/calc.cfg

OLD_UNI_FILE_HOST=asetrade1.jc
OLD_UNI_FILE=/spare/local/ase/trade/run/uni/uni.txt.20100318.evan
UNI_FILE=$DAILY_SIM_DIR/uni.txt.20100318.evan

mkdir -p $DAILY_SIM_DIR

# Setting startdate and enddate to current date in calc_$DATE.cfg file ensures 
#   that we calculate for just one day
STEP=480
STARTMINS=0
ENDMINS=0

cp $ORIG_CFG_FILE $CFG_FILE
sed -i "s/\(^startdate:\)\(..*$\)/\1${SIMDATE}/" $CFG_FILE
sed -i "s/\(^enddate:\)\(..*$\)/\1${SIMDATE}/" $CFG_FILE
sed -i "s/\(^stepsize:\)\(..*$\)/\1${STEP}/" $CFG_FILE
sed -i "s/\(^start_mins_before_close:\)\(..*$\)/\1${STARTMINS}/" $CFG_FILE
sed -i "s/\(^end_mins_before_close:\)\(..*$\)/\1${ENDMINS}/" $CFG_FILE

scp ase@$OLD_UNI_FILE_HOST:$OLD_UNI_FILE $UNI_FILE
sed -i "s;^#universe;#universe\nold_unifile: ${UNI_FILE};" $CFG_FILE

$JAVA ase.apps.SimCalc -location $DAILY_SIM_DIR 2> $LOGFILE
RES=$?

ls -l $LOGFILE
tail $LOGFILE

exit $RES

exit $?
