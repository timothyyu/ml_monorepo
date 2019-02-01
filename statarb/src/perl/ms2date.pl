#!/usr/bin/perl

# XXX TODO: MAKE THIS WORK FOR DATES BEFORE 2001

use strict;
use Getopt::Long;

my $datefields = "1";
my $delim = '\|';
my $header = 0;

GetOptions("f=s" => \$datefields,
            "d=s" => \$delim,
            "h" => \$header);

# is there a header row?
my $start = 0;
if ($header == 1) {
   $start = 1;
} 

if ( !defined $datefields ) {
    die "no date fields defined to convert";
}
my @convertindices = split(",", $datefields);
my %isdate = ();
my $i;
foreach $i(@convertindices) {
    $isdate{$i}=1;
}

my $linenum = 1;
while (<>) {
    my $line = $_;
    chomp($line);
    my @fields = split($delim, $line);
    my $field;
    $i = 1;

    foreach $field(@fields) {
        if ( defined $isdate{$i} && $linenum > $start ) { 
            my $field1 = $field;
            my $field2 = $field;
            my $df = gmtime(substr($field,0,10));
            print "$df|";
        }
        else { print "$field|"; }
        $i++;
    }
    $linenum++;
    print "\n";
}
 
