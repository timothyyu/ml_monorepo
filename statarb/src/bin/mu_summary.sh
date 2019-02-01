#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

FORECAST=$1
MU_FILE=`ls $RUN_DIR/mus/mus.FULL.${DATE}_*.txt | tail -1`
if [ $# -gt 1 ]; then
    MU_FILE=$2
fi

TMPFILE=$TMP_DIR/musum.$$.tmp
FULLFILE=$TMP_DIR/fullsum.$$.tmp
GFILE=$TMP_DIR/g.$$.png

echo Looking at $MU_FILE

grep $FORECAST $MU_FILE | gawk -F\| '{print $3*10000}' > $TMPFILE
grep FULL $MU_FILE | gawk -F\| '{print $1"|"$3*10000}' > $FULLFILE

Rscript -e "png('$GFILE'); d <- scan('$TMPFILE'); hist(d);"
display $GFILE

if [ $FORECAST = "all" ]; then
    cat $MU_FILE | gawk -F\| '{ sum[$2]+=$3; cnt[$2]++; if ($3 > max[$2]) {max[$2]=$3} if ($3 < min[$2]) {min[$2]=$3} } END { for (cst in sum) {print cst, cnt[cst], sum[cst]/cnt[cst], max[cst], min[cst] } } '
else
    echo "avg min max (bps) frac"
    cat $TMPFILE | gawk -F\| '{ sum+=$1; cnt++; if ($1 > max) {max=$1} if ($1 < min) {min=$1} } END { print sum/cnt, min, max} '
fi

rm -f $TMPFILE 
rm -f $GFILE

exit 0
