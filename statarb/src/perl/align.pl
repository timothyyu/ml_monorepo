#!/usr/bin/perl 
use strict;

my $delimiter = '\|';
my $line;
my @words;
my @width;
my $idx;
my $kdx;

my @lines = <STDIN>;

for $line ( @lines ) { 
    chomp( $line ); 
    @words = split( $delimiter, $line ); 
    for ($idx = 0 ; $idx <= $#words ; $idx++)  { 
        if ( !defined $width[$idx] || $width[$idx] < length($words[$idx])) { 
            $width[$idx] = length( $words[$idx] ); 
        } 
    } 
} 

for $line (@lines) { 
    chomp( $line ); 
    @words = split( $delimiter, $line ); 
    for ($idx = 0 ; $idx <= $#words ; $idx++)  { 
        print( "$words[$idx]" );
        for ($kdx = length($words[$idx]) ; $kdx < $width[$idx] ; $kdx++) { 
            printf " "; 
        } 
        printf "|"; 
    } 
    printf "\n"; 
} 

