#!/bin/bash

cat $1 | gawk -F\| '
{   
    xy+=($1*$2); 
	x+=$1; 
	y+=$2; 
	x2+=($1*$1); 
	y2+=($2*$2);
} 
END { 
	print "NR=" NR; 
	ssx=x2-((x*x)/NR); 
	print "ssx=" ssx; 
	ssy=y2-((y*y)/NR); 
	print "ssy=" ssy; 
	ssxy = xy - ((x*y)/NR); 
	print "ssxy=" ssxy; 
	r=ssxy/sqrt(ssx*ssy); 
	print "r=" r; 
}'


