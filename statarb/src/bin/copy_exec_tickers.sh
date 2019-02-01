#!/bin/sh
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

REMOTE_PARAM_DIR=/spare/local/guillotine/gt-params
SERVER_STR=`cat $CONFIG_DIR/exec.conf | grep servers`
SERVER_LIST=`echo $SERVER_STR | sed 's/.*=[ \t,]*//' | sed 's/:[0-9]*//g'`

cd $RUN_DIR
for server in $SERVER_LIST ; do
  SERVER_NUM=`expr match $server '[^1-9]*\([1-9]*\)'`
  if [ -z $SERVER_NUM ]; then
    echo "ERROR in copying tickers: could not get server number for server: $server"
    continue
  fi
  scp -q ase@$server:$REMOTE_PARAM_DIR/universe.sub$SERVER_NUM universe.$server
  cat universe.$server | sed "s/\(.*\)/\1|$server/" >> exec_tickers.txt
  rm universe.$server
done

exit 0
