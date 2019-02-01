# Quadratic-Sieve
Python code for the single-polynomial version of Quadratic Sieve, no bells or whistles. Factors an integer N, using a chosen factor base of P primes, and a sieve interval.

Todo:
Implement Numpy

Add data analysis tools

Implement Cython

Implement Multiple Polynomials

Implement General Number Field Sieve (eventually...)

This is a self-pursued project. Over time I will further clean up and optimize the algorithm, and I'll probably implement the multiple polynomial version soon.

Integer Factorization is one of those lovely topics which is simple in concept, but notoriously difficult to master. Yet we rely on its security almost constantly, through cryptosystems such as RSA. 
This project was an exploration of that realm, one which took me through a web of number theory, algorithms, cryptography, and linear algebra.
Even the "basic" version of Quadratic Sieve took an embarrasing amount of time to finish, but the experience was well worth it. 
I hope this could help other aspiring students with understanding a little bit about integer factorization. Maybe for identity theft.

Simplified Gaussian Elimination was taken from this source: https://www.cs.umd.edu/~gasarch/TOPICS/factoring/fastgauss.pdf
Tonelli-Shanks for modular square root: https://gist.github.com/LaurentMazare/6745649
