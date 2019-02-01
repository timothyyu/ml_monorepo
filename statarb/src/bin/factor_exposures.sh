#!/bin/bash
if [ "$ROOT_DIR" = "" ]; then
    exit "Must set ROOT_DIR!"
else
    . $ROOT_DIR/src/bin/include.sh
fi

EXP_FILE1=$1
EXP_FILE2=$TMP_DIR/fac.tmp
zgrep '|F:' $EXP_FILE1 > $EXP_FILE2

gawk -F\| -v expfile=$EXP_FILE2 '
function abs(x) {
  return x >= 0 ? x : -x
}
BEGIN {
  while ( getline < expfile > 0 ) {
    sec=$1
    fact=$2
    xpos[$1"~"$2] = $5
    factors[$2] = 1
  }
}
$1 ~ /^T/ {
  totnot += abs($4)
  for (fac in factors) {  
    exps[fac] += $4 * xpos[$3"~"fac]    
  }
}
$1 ~ /^POS/ {
  totnot += abs($3*$4)
  for (fac in factors) {
    exps[fac] += $3*$4 * xpos[$2"~"fac]
  }
}
NF == 6 {
  totnot += abs($2)
  for (fac in factors) {
    exps[fac] += $2 * xpos[$1"~"fac]
  }
}
END {
  for (fac in factors) {
    print fac"|"exps[fac]"|"100.0*exps[fac]/totnot"|"totnot
  }
}
' | sort -t\| -nr -k3,3

