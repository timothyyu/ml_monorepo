#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

FILLS_FILE=$1
PRICES_FILE=$2

gawk -F\| -v fills=$FILLS_FILE -v prices=$PRICES_FILE '
BEGIN {
    while( getline < prices > 0 ) {
        price[$1"|"$2]=($4+$3)/2
    }
}
{
    pnli=(price[$4"|"$5] - $7) * $6
    pnl[$4"|"$5] = pnli
    tot+=pnli
}
END {
    print tot
}
'
