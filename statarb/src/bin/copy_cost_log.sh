#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

LOG_DIR=/spare/local/guillotine/log
REMOTE_DIR=/apps/ase/data/trading/useq-live/exec/$DATE

cd $LOG_DIR
for dir in rts1_?.$DATE* ; do
  cd $dir
  if [ -e cost.log ]; then
    SERVER=${dir:0:6}
    ssh ase@asetrade1.newark "mkdir -p $REMOTE_DIR"
    gzip -c cost.log > /tmp/cost.$$.log.gz
    scp /tmp/cost.$$.log.gz ase@asetrade1.newark:$REMOTE_DIR/cost.$SERVER.log.gz
    rm /tmp/cost.$$.log.gz
  fi
  cd ..
done

