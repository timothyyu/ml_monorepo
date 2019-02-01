# PythonFactorise
Python implementation of the Self Initialising Quadratic Sieve.

factorise.py factorises a natural number given as a command line parameter into 
its prime factors. It first attempts to use trial division to find very small 
factors, then uses Brent's version of the Pollard rho algorithm [1] to find 
slightly larger factors. If any large factors remain, it uses the 
Self-Initializing Quadratic Sieve (SIQS) [2] to factorise those.

[1] Brent, Richard P. 'An improved Monte Carlo factorization algorithm.'
    BIT Numerical Mathematics 20.2 (1980): 176-184.

[2] Contini, Scott Patrick. 'Factoring integers with the self-
    initializing quadratic sieve.' (1997).

