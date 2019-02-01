#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

$ROOT_DIR/bin/cronwrapper.sh $ROOT_DIR useq-live $ROOT_DIR/bin/sod_portfolio.sh
$ROOT_DIR/bin/cronwrapper.sh $ROOT_DIR useq-live $ROOT_DIR/bin/redo_reports.sh
$ROOT_DIR/bin/cronwrapper.sh $ROOT_DIR useq-live $ROOT_DIR/bin/reconcile.py --yesterday --file
