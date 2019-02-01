#!/bin/sh
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

cp -v $RUN_DIR/fills.* $DATA_DIR/trading/$STRAT/fills/
cp -v $RUN_DIR/locate_requests.txt $DATA_DIR/trading/$STRAT/borrow/locate_requests.$DATE.txt

TRADE_LOG_DIR=$DATA_DIR/trading/$STRAT/exec/$DATE
SERVER_STR=`cat $CONFIG_DIR/exec.conf | grep servers`
SERVER_LIST=`echo $SERVER_STR | sed 's/.*=[ \t,]*//' | sed 's/:[0-9]*//g'`
MOC_SERVER_STR=`cat $CONFIG_DIR/exec.moc.conf | grep servers`
MOC_SERVER_LIST=`echo $MOC_SERVER_STR | sed 's/.*=[ \t,]*//' | sed 's/:[0-9]*//g'`
SERVER_LIST="$SERVER_LIST $MOC_SERVER_LIST"

mkdir -p $TRADE_LOG_DIR
cd $TRADE_LOG_DIR
for SERVER in $SERVER_LIST ; do
  SERVER_NUM=`expr match $SERVER '[^1-9]*\([1-9]*\)'`
  if [ -z $SERVER_NUM ]; then
    SERVER_NUM=$SERVER
  fi
  ssh $SERVER "chmod -R o= $EXEC_LOG_DIR; gzip -r $EXEC_LOG_DIR"
  rsync -auzb $SERVER:$EXEC_LOG_DIR/ rts1_$SERVER_NUM
#  ssh ase@$SERVER "gzip -c $EXEC_LOG_DIR/cost.log" > cost.rts1_$SERVER_NUM.log.gz
done

# pricetracker stuff
#ssh execd@exectrade1.jc "gzip /spare/local/price_data/price.$DATE/*"
#scp execd@exectrade1.jc:/spare/local/price_data/price.$DATE/data.* .

exit 0
