#!/usr/bin/env python

import sys
import gzip
from BeautifulSoup import BeautifulSoup

filename = sys.argv[1]
if ".gz" in filename:
    file = gzip.open(filename, 'r')
else:
    file = open(filename, 'r')

data = file.read()
soup = BeautifulSoup(data)
print soup.prettify()

