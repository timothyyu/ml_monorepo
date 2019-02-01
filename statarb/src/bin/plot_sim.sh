#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi


STATDIR=$1
FORECASTS=$2
DAT_DIR=$ROOT_DIR/tmp
DAT_FILE=$DAT_DIR/simplot.$$
GFILE=/apps/ase/tmp/g.$$.png

rm -f $DAT_DIR/simplot.*
cat $STATDIR/stats.*.txt | grep '^201' | gawk -F' ' '{print $1"|"$8/10.0"|"($4-$6)}' > $DAT_FILE.full
for fcast in $FORECASTS; do
    echo processing $fcast
    cat $STATDIR/fc_$fcast.stats.*.txt | grep '^201' | gawk -F' ' '{print $1"|"$8"|"($4-$6)}' > $DAT_FILE.$fcast
done

MAX=`cat $DAT_DIR/simplot.$$.* | cut -d\| -f 2 | sort -nr | head -1`
echo $MAX

Rscript -e "source('$ROOT_DIR/R/utils.R'); plotfiles('$DAT_DIR', '$GFILE', $MAX);"
display $GFILE

rm -f $DAT_FILE.* $GFILE
