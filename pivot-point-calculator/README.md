# getpivots (pivot-point-calculator)
=====================================================

Getpivots can be used for identifying areas of support and resistance for the next day's trading session.  Getpivots calculates pivot points for a given ticker symbol using the most recent closing price data, and leverages several different algorithms which include the Floor/Classic formula, Woodie’s Formula, as well as Kirk's formula. 


![getpivots-screencap1](https://cloud.githubusercontent.com/assets/12847315/11052885/6ae05404-872a-11e5-91c1-13bfb17f50d2.jpg)

Install
-------

    pip install getpivots

Usage
-----

    getpivots -t tickersymbol -f -w -k -c

Options
-----
    -h, --help          Print this help text and exit
    -t, --ticker        Specify a ticker symbol to run against (e.g. YHOO)
    -f, --floor         Uses the Floor/Classic calculation
    -w, --woodie		Uses the Woddy calculation
    -k, --kirk			Uses Kirk's calculation (thekirkreport.com)
    -c, --current       Inserts indicator for current price if run during an active session (e.g. -> 123.00)


See Also
--------

For more information: https://pypi.python.org/pypi/getpivots
