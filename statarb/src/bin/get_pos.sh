#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

if [ $# -gt 0 ]; then
   $JAVA ase.portfolio.PortfolioUtils
else
   $JAVA ase.portfolio.PortfolioUtils $1
fi
