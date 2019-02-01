#!/bin/bash

MACHINES="asedb1.newark asetrade1.newark asetrade2.newark asestudy1.waltham"
for machine in $MACHINES; do
    ssh $machine "TERM=xterm; xterm -e $machine top" &
done
