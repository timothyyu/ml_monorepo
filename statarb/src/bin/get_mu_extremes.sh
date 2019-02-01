#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

FORECAST=$1
LIMIT=$2

MUS_DIR=$RUN_DIR/mus/
MUS_FILE=`ls -rt $MUS_DIR | tail -1`
MUS_FILE=$MUS_DIR/$MUS_FILE

echo Looking at $MUS_FILE

FORECASTS=$FORECAST
if [ $FORECAST == "all" ]; then
    FORECASTS="fc_cestd5 fc_cestd10 fc_crtg5 fc_crtg10 fc_ctgd5 fc_ctgd10 fc_ctrb fc_destd5 fc_destd10 fc_drtg10 fc_dtgd5 fc_dtgd10 fc_dtrb fc_flyrating fc_flyearn fc_flyhot fc_hlB fc_hlS fc_o2cBtB fc_o2cBtS fc_o2cvadj_new fc_earndate fc_flyticker fc_noflyticker fc_e2p fc_s2p fc_c2a fc_ee2p fc_qhlB fc_qhlS fc_bb fc_c2o_b fc_c2o_s fc_mhtb fc_si fc_bsz fc_bd fc_bsz1 fc_bd1 fc_pca1"
fi

for fc in $FORECASTS; do
    echo "FORECAST: $fc"
    SIGMA=`grep "$fc" $MUS_FILE | gawk -F '|' 'BEGIN{cnt=0; sum=0; sum2=0;} {cnt+=1; sum+=$3; sum2+=$3*$3;} END{print sqrt(sum2/cnt-sum*sum/cnt/cnt)}'`
    grep $fc $MUS_FILE | gawk -F '|' -v 'LIMIT'=$LIMIT -v 'SIGMA'=$SIGMA '{if ($3<-LIMIT*SIGMA || $3>LIMIT*SIGMA) print $0}' | gawk -F\| '{print $1"|"$2"|"$3*10000.0}' | sort -n -r -t\| -k3,3 | $BIN_DIR/align.pl
    echo ""
done

exit 1
