# Generate test data in FDAX datafile format
# Hack as needed

from math import sin, pi

price_anchor = 9000.0
price_swing = 200.0
period = 1000

with open('FDAX_19700101.csv', 'w') as f:
    for i in range(10000):
        price = price_anchor + price_swing * sin(2*pi*i/period)
        f.write('{} {} {} {} {} {} {} {}\n'.format(i, price, 1, 0, price-0.5, 1, price+0.5, 1))

