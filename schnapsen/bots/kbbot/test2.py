import sys
from kb import KB, Boolean, Integer, Constant

# Define our integer symbols
x = Integer('x')
y = Integer('y')
z = Integer('z')

sum = x + y
print(sum)

constraint = x + y + z > 1
print(constraint)

constraint = 1 < x + y + z
print(constraint)

constraint = x - (z + y) < x - (y - z)
print(constraint)

q = 15
constraint = q * x  == x - (y - q * z)
print(constraint)
