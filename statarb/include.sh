#!/bin/sh

EMAIL_ADDRESS=sean@xxx.com
export EMAIL_ADDRESS

DATE=`date -u +%Y%m%d`
export DATE

export PATH=/usr/lib64/qt-3.3/bin:/usr/NX/bin:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin:/tools/git/redhat/x_64/1.7.4.2/bin

##Python Stuff
ROOT_DIR=/q/work/sean/prod/
PYTHONUNBUFFERED=1
PYTHON_DIR=$ROOT_DIR/install/penv
PYTHONPATH=$ROOT_DIR/bin:$PYTHON_DIR/lib/python2.7/site-packages
export PYTHONUNBUFFERED PYTHONPATH PYTHON_BIN PYTHON_DIR

TOOLS_DIR=/tools

##NUMERIC
export ATLAS=$TOOLS_DIR/atlas/redhat/x_64/3.10.1
export LAPACK=$TOOLS_DIR/atlas/redhat/x_64/3.10.1
export BLAS=$TOOLS_DIR/atlas/redhat/x_64/3.10.1

PATH=$TOOLS_DIR/gcc/redhat/x_64/4.8.1_RH6/bin:$TOOLS_DIR/mysql/redhat/x_64/5.6.16/bin:$TOOLS_DIR/git/redhat/x_64/1.8.5.2/bin:$PYTHON_DIR/bin:$INSTALL_DIR/jdk/bin:$TOOLS_DIR/R/redhat/x_64/2.15.3/bin:/usr/bin:/bin:/usr/local/bin:/usr/lib64/qt-3.3/bin:/usr/NX/bin:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin:$TOOLS_DIR/ack-grep/redhat/x_64/1.0
LD_LIBRARY_PATH=$INSTALL_DIR/lib:$TOOLS_DIR/gcc/redhat/x_64/4.8.1_RH6/lib64:$TOOLS_DIR/boost/redhat/x_64/1_43_0/lib:$TOOLS_DIR/mysql/redhat/x_64/5.6.16/lib:$TOOLS_DIR/atlas/redhat/x_64/3.10.1:/usr/lib:/usr/lib64:$TOOLS_DIR/hdf5/redhat/x_64/1.8.4/lib/
export PATH LD_LIBRARY_PATH

export HOSTNAME=`echo $HOSTNAME | cut -d. -f1`

export CACHE_DIR=$ROOT_DIR/cache
