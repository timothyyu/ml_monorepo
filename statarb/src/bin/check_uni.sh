#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

cd $RUN_DIR
PREV_DAY=`$BIN_DIR/exchange_date_add $PRIMARY_EXCHANGE $DATE -1`

#CR1 = previous trading day's last calcres
CR1=`ls -t ../$PREV_DAY/calcres | head -1`
#CR2 = current day's first calcres
CR2=`ls -tr calcres | head -1`

TMP1=$TMP_DIR/cr1.tmp

echo 'cheching UNIVERSE'
zcat ../$PREV_DAY/calcres/$CR1 | cut -d\| -f1 | sort -u > $TMP1
zcat calcres/$CR2 | cut -d\| -f1 | sort -u | diff - $TMP1 | awk '/[<>]/' | sed 's/>/Leaving: /' | sed 's/</Entering: /'

for item in "EXPANDABLE" "TRADEABLE" "PRICE_FORECASTABLE" "FUND_FORECASTABLE"; do
    echo checking $item
    zgrep $item ../$PREV_DAY/calcres/$CR1 | cut -d\| -f1 | sort -u > $TMP1
    zgrep $item calcres/$CR2 | cut -d\| -f1 | sort -u | diff - $TMP1 | awk '/[<>]/' | sed 's/>/Leaving: /' | sed 's/</Entering: /'
done
rm $TMP1

