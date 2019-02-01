#!/bin/bash

YYYYMMDD=$1
destDir=$2
if [ "$YYYYMMDD" == "" ] ;then
    echo "usage: $0 YYYYMMDD required"
    exit 1
fi


YYYY=`echo $YYYYMMDD| cut -c1-4`
YY=`echo $YYYYMMDD| cut -c3-4`
MM=`echo $YYYYMMDD| cut -c5-6`
DD=`echo $YYYYMMDD| cut -c7-8`

DDMMYY="$DD$MM$YY"

if [ "$destDir" == "" ] ;then
    destDir="/apps/logs/ase/data/morgan/positions/$YYYY"
fi


lftp -e "lcd $destDir; set ftp:ssl-protect-fxp true;set ftp:ssl-protect-data true;mget *$YYYYMMDD* ; mget *$DDMMYY* ; quit" -uvaygcoco,OAcXL4iUG48dBRrh sftp://sftp.morganstanley.com 

