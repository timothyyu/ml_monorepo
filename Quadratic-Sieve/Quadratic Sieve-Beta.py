from math import sqrt, exp, log, log2
import random
from Factor import brent
from MillerRabin import is_probable_prime
from itertools import chain, combinations
import sys


def gcd(a, b):  # Euclid's algorithm
    if b == 0:
        return a
    elif a >= b:
        return gcd(b, a % b)
    else:
        return gcd(b, a)


def isqrt(n):  # Newton's method, returns exact int for large squares
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x


def nroot(A, n): # nth root algorithm
    x = A
    delta = 1
    while abs(delta) > .01:
        # x = (1/n)*(((n-1)*x)+(A/pow(x,n-1)))
        delta = (A / pow(x, n - 1) - x) / n
        x += delta
    return x


def nroot2(A, n, i):  # f = x^n - A = 0, f' = nx^(n-1)

    x = n
    k = 0
    for k in range(i):
        x = (1 / n) * (((n - 1) * x) + (A / pow(x, n - 1)))

    return x


def mprint(M):  # prints a matrix in readable form
    for row in M:
        print(row)

def latexprint(M):  # prints a matrix in latex form
    for row in M:
        for n in row:
            print(str(n) + '&', end='')
        print('\\\\')


def semi(x):  # generate a random semiprime

    n = random.randint(1, x)
    k = 0
    p = 1
    while k < 2:
        if is_probable_prime(n):
            p *= n
            k += 1
        n = random.randint(1, x)
    print('size {}'.format(len(str(p))))
    return p


def factor(N): # completely factors N using Pollard Rho
    
    def pollard(N, factors):  

        rem = N
        while True:
            if is_probable_prime(rem):
                factors.append(rem)
                break

            f = brent(rem)
            while f == rem:  # ensures pollard rho returns a smaller factor
                f = brent(rem)

            if f and f < rem:  # found a factor
                if is_probable_prime(f):  # ensure f is prime
                    # print("Pollard rho (Brent): Prime factor found: %s" % f)
                    factors.append(f)
                    rem = rem // f  # other factor
                else:  # factor is composite
                    # print("Pollard rho (Brent): Non-prime factor found: %s" % f)
                    rem_f = pollard(f, factors)  # recursive part
                    rem = (rem // f) * rem_f  # combines the two remainders
                    factors.remove(rem_f)  # removes tricky duplicate that got appended in 1st if stmt
            else:  # no more factors found, rem is prime
                # print("No (more) small factors found.")
                break

        return rem

    factors = []
    pollard(N, factors)
    return factors


def prime_gen(n):  # sieve of Eratosthenes

    isPrime = [False, False]

    for i in range(2, n + 1):  # list of markers at each index n
        isPrime.append(True)

    for j in range(2, int(n / 2)):  # tries gap sizes up to n/2
        if isPrime[j] == True:
            for k in range(2 * j, n + 1, j):  # every multiple of j is composite
                isPrime[k] = False

    return [i for i in range(n + 1) if isPrime[i]]


def legendre(a, p):  # legendre symbol of (a/p)
    return pow(a, (p - 1) // 2, p)

def tonelli(n, p):  # tonelli-shanks to solve modular square root: x^2 = n (mod p)
    assert legendre(n, p) == 1, "not a square (mod p)"
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1
    if s == 1:
        r = pow(n, (p + 1) // 4, p)
        return r, p - r
    for z in range(2, p):
        if p - 1 == legendre(z, p):
            break
    c = pow(z, q, p)
    r = pow(n, (q + 1) // 2, p)
    t = pow(n, q, p)
    m = s
    t2 = 0
    while (t - 1) % p != 0:
        t2 = (t * t) % p
        for i in range(1, m):
            if (t2 - 1) % p == 0:
                break
            t2 = (t2 * t2) % p
        b = pow(c, 1 << (m - i - 1), p)
        r = (r * b) % p
        c = (b * b) % p
        t = (t * c) % p
        m = i

    return (r, p - r)


def size_bound(N):  # heuristic for optimal factor base and interval size

    # F = pow(exp(sqrt(log(N)*log(log(N)))),sqrt(2)/4)
    B = exp( pow(log(N) * log(log(N)), 0.5))
    
    return int(B)


def find_base(N, B):
    # generates a B-smooth factor base

    factor_base = []
    primes = prime_gen(B)
    # print(primes)

    for p in primes:  # such that N is a quadratic residue mod p
        if legendre(N, p) == 1:
            factor_base.append(p)
    return (factor_base)


def find_base1(N, F):
    # generates a factor base of size F

    factor_base = []
    primes = prime_gen(F * 10)  # kind of arbitrary
    # print(primes)

    for p in primes:
        if len(factor_base) == F:
            break
        if legendre(N, p) == 1:
            factor_base.append(p)
    return factor_base

    
def find_smooth(N, factor_base, I, root, row_tol, bit_tol):
    '''Finds B + row_tol smooth relations. The most recent version utilizes negative intervals,
    logarithmic sieving, segmented sieves and the Large Prime variation to maximize efficiency.'''

    def sieve(indices, bits, base_list = None):
        '''Run over bits, sequentially adding factor base bits using information from indices'''
        
        new_indices = []
        for k in range(len(indices)):
            starts = indices[k]
            p = starts[0]
            for i in range(1, 3):  # two per prime

                start = starts[i]
                if start >= I:
                    print('start index overshoot,',start)
                    starts[i] = start - I
                    continue

                for j in range(start, len(bits), p):
                    bits[j] += base_bits[k+1] #because 2 was included
                    #base_list[j].append(factor_base[k+1])
                starts[i] = j + p - I

            new_indices.append(starts) #fresh starts

        return new_indices, bits
        

    def find_candidates(n_bits,p_bits,dis_from_center):
        '''Filter smooth candidates. Tolerance is adjustable'''
        
        nx_cands = []  
        nsmooth_cands = []
        px_cands = []  
        psmooth_cands = []

        for i in range(I-1, 0, -1):  # going backwards to preserve order
            x = (root - i) - dis_from_center
            if x < 0:  # too far negative
                continue

            thres = int(log2(abs((x ** 2) - N))) - bit_tol  # threshold
            #print(x,n_bits[i],nbase_list[i])
            
            if abs(n_bits[i]) >= thres:  # found B-smooth candidate
                nsmooth_cands.append((x ** 2) - N)
                nx_cands.append(x)

        for i in range(I):
            x = root + i + dis_from_center
            thres = int(log2(abs((x ** 2) - N))) - bit_tol  # threshold
            #print(x,p_bits[i],pbase_list[i])

            if abs(p_bits[i]) >= thres:  # found B-smooth candidate
                psmooth_cands.append((x ** 2) - N)
                px_cands.append(x)
                
            
        return nsmooth_cands, nx_cands, psmooth_cands, px_cands

        
    def verify_smooth(factor_base, smooth_cands, x_cands):
        '''verifies smooth relations from candidates'''
            
        def factor(n, factor_base): # trial division from factor base

            factors = []
            #large_prime_facs = []
            
            if n < 0:
                factors.append(-1)
                n //= -1
                
            for p in factor_base:

                while n % p == 0:
                    factors.append(p)
                    n //= p
            if n == 1 or n == -1:
                return factors
            
            else:
                return None

        
        smooth_nums = []
        factors = []
        x_list = []
        
        for i in range(len(smooth_cands)):
            
            fac = factor(smooth_cands[i], factor_base)
            
            if fac:
                smooth_nums.append(smooth_cands[i])
                factors.append(fac)
                x_list.append(x_cands[i])
            
        return (smooth_nums, x_list, factors)


    def verify_smooth_largePrime(factor_base, smooth_cands, x_cands):
        '''Large Prime Variation. Factorizations with one larger prime than B are stored,
        in the hope of combining with another to yield a usable exponent vector.'''
        
        def factor(n, factor_base):
            '''Trial division from factor base.
            Modern versions use sieving instead.'''

            factors = []
            #large_prime_facs = []
            
            if n < 0:
                factors.append(-1)
                n //= -1
                
            for p in factor_base:

                while n % p == 0:
                    factors.append(p)
                    n //= p
            if n == 1 or n == -1:
                return False, factors
            
            elif n < B**2: #large prime variation
                #print(n)
                #print(is_probable_prime(n))
                factors.append(n)
                return True, factors
            else:
                return None, None

        def largePrime(large_p_relations):
            'combine large prime cycles'
            
            large_p_relations = sorted(large_p_relations)
            #print(large_p_relations)
            
            while len(large_p_relations)>1:

                shared_primes = []
                #print(len(large_p_relations))
                shared_primes.append(large_p_relations.pop(0))
                
                while shared_primes[0][0][0] == large_p_relations[0][0][0]:
                   shared_primes.append(large_p_relations.pop(0))
                #print(shared_primes)
                
                if len(shared_primes) == 1: # no matches
                    continue
                
                else: #create and combine exponent matrices

                    '''if shared_primes[0][0] is in large_p_list:
                        
                    large_p_list.append(shared_primes[0][0])'''
                    '''for relation in shared_primes:
                        exp_vector = make_vector(list(reversed(relation[0])),factor_base)'''
                    #sums = list(combinations(shared_primes,2))
                    sums = shared_primes
                    #print(sums)
                    for i in range(1,len(sums)):

                        '''del sums[0][0][0]
                        del sums[i][0][0]'''
                        factors.append(sums[0][0]+sums[i][0])
                        smooth_nums.append(sums[0][1]*sums[i][1])
                        x_list.append(sums[0][2]*sums[i][2])

                        print(sums[0][0]+sums[i][0])
                        print(sums[0][1]*sums[i][1],sums[0][2]*sums[i][2],'\n')

                        '''class largePrime:
                        def __init__(self,prime):
                            self.prime = prime'''
                        
        smooth_nums = []
        factors = []
        x_list = []
        large_p_relations = []
        
        for i in range(len(smooth_cands)):
            is_largePrime, fac = factor(smooth_cands[i], factor_base)
            if is_largePrime:
                large_p_relations.append([list(reversed(fac)),smooth_cands[i],x_cands[i]])
                #large_primes.append(fac[-1])
            elif fac:
                smooth_nums.append(smooth_cands[i])
                factors.append(fac)
                x_list.append(x_cands[i])

        largePrime(large_p_relations)

        return (smooth_nums, x_list, factors)


    '''Find smooth numbers'''
    
    base_bits = [round(log2(p)) for p in factor_base]
    p_indices = []
    n_indices = []
    
    '''Initialize starting indices. There are two roots per factor, so each factor
    is stored with two indices, in a 3-tuple.'''
    
    for i in range(1,len(base_bits)):  # 2 is ignored

        p = factor_base[i]
        mod_roots = tonelli(N, p)  # two roots
        p_tuple = [p] # p_ = positive, refers to interval direction
        n_tuple = [p]

        for r in mod_roots:
            start = ((r - root) % p)  # idk why
            p_tuple.append(start)
            n_tuple.append(abs(start - p))

        p_indices.append(p_tuple)
        n_indices.append(n_tuple)
    
    smooth_nums = []
    x_list = []
    factors = []

    dis_from_center = 0
    
    '''Sieve. Repeat sieving if necessary, increasing distance from center'''

    while len(smooth_nums) < len(factor_base) + row_tol:
        
        #print('we have', len(smooth_nums), 'extending interval...')
        
        p_bits = [0 for x in range(I)]
        n_bits = [0 for x in range(I)]
        '''pbase_list = [[] for x in range(I)]
        nbase_list = [[] for x in range(I)]
        print(p_indices)
        print(n_indices)'''
        
        p_indices, p_bits = sieve(p_indices, p_bits)
        n_indices, n_bits = sieve(n_indices, n_bits)

        nsmooth_cands, nx_cands, psmooth_cands, px_cands = find_candidates(n_bits,p_bits,dis_from_center)
        print(len(nsmooth_cands)+len(psmooth_cands),'found')
        #print('verifying...')
        n_smooths, n_xs, n_factors = verify_smooth(factor_base, nsmooth_cands, nx_cands)
        p_smooths, p_xs, p_factors = verify_smooth(factor_base, psmooth_cands, px_cands)

        '''Appending smooth relations in numeric order, optional'''
        smooth_nums += p_smooths
        x_list += p_xs
        factors += p_factors

        smooth_nums = n_smooths + smooth_nums #negatives go before!
        x_list = n_xs + x_list
        factors = n_factors + factors

        dis_from_center += I
    
    print('total interval size of {}'.format((dis_from_center)*2))

    return smooth_nums, x_list, factors


def make_vector(n_factors,factor_base): 
    '''turns factorization into an exponent vector mod 2'''
    
    exp_vector = [0] * (len(factor_base))
    # print(n,n_factors)
    for j in range(len(factor_base)):
        if factor_base[j] in n_factors:
            exp_vector[j] = (exp_vector[j] + n_factors.count(factor_base[j])) % 2
    return exp_vector
    
def transpose(matrix):
    '''transpose matrix so columns become rows, makes list comp easier to work with.
    Alternatively use Numpy column manipulations'''
    
    new_matrix = []
    for i in range(len(matrix[0])):
        new_row = []
        for row in matrix:
            new_row.append(row[i])
        new_matrix.append(new_row)
    return (new_matrix)


def build_matrix(factor_base, smooth_nums, factors):
    '''builds matrix from exponent vectors mod 2 from smooth numbers'''

    M = []
    factor_base.insert(0, -1)
        
    for i in range(len(smooth_nums)):
        
        exp_vector = make_vector(factors[i],factor_base)
        # print(n_factors, exp_vector)

        if 1 not in exp_vector:  # search for squares
            return True, (smooth_nums[i])
        else:
            pass

        M.append(exp_vector)

    M = transpose(M)
    # mprint(M)
    return (False, M)


def gauss_elim(M):
    '''reduced form of gaussian elimination, finds rref and reads off the nullspace
    https://www.cs.umd.edu/~gasarch/TOPICS/factoring/fastgauss.pdf'''

    # M = optimize(M)
    marks = [False] * len(M[0])

    for i in range(len(M)):  # do for all rows
        row = M[i]
        # print(row)

        for num in row:  # search for pivot
            if num == 1:
                # print("found pivot at column " + str(row.index(num)+1))
                j = row.index(num)  # column index
                marks[j] = True

                for k in chain(range(0, i), range(i + 1, len(M))):  # search for other 1s in the same column
                    if M[k][j] == 1:
                        for i in range(len(M[k])):
                            M[k][i] = (M[k][i] + row[i]) % 2
                break

    M = transpose(M)
    # print(marks)
    # mprint(M)

    sol_rows = []
    for i in range(len(marks)):  # find free columns (which have now become rows)
        if not marks[i]:  # found free row
            sol_rows.append([M[i], i])

    if not sol_rows:
        print("No solution found. Need more smooth numbers.")
        sys.exit()

    print("Found {} potential solutions.\n".format(len(sol_rows)))
    #print(sol_rows)
    return sol_rows, marks, M


def solve_row(sol_rows, M, marks, K=0):
    '''Find linear dependencies and create solution vector'''
    
    solution_vec, indices = [], []
    free_row = sol_rows[K][0]  # may be multiple K
    for i in range(len(free_row)):
        if free_row[i] == 1:
            indices.append(i)

    for r in range(len(M)):  # rows with 1 in the same column will be dependent
        for i in indices:
            if M[r][i] == 1 and marks[r]:
                solution_vec.append(r)
                break
    #print(solution_vec)
    # print("Found linear dependencies at rows "+ str(solution_vec))
    solution_vec.append(sol_rows[K][1])
    return (solution_vec)


def solve(solution_vec, smooth_nums, factors, x_list, N, factor_base):
    '''Solves the congruence of squares'''
    
    solution_nums = [smooth_nums[i] for i in solution_vec]
    #sol_facs = [factors[i] for i in solution_vec]
    x_nums = [x_list[i] for i in solution_vec]

    '''for i in range(len(solution_vec)):
        print(x_nums[i],solution_nums[i],sol_facs[i])'''

    '''residues = []

    for i in range(len(factor_base)):
        f = factor_base[i]
        exponent = 0
        for row in factors: #deal with smaller numbers
            e = row.count(f)
            exponent += e

        #print(exponent)
        res = pow(f,exponent,N)
        residues.append(res)

    a = 1
    for r in residues:
        a *= r
    a = a % N'''

    b = 1
    for n in x_nums:
        b *= n

    Asquare = 1
    for n in solution_nums:
        Asquare *= n
    a = isqrt(Asquare)
    assert a**2 == Asquare, 'not square'
    #print(str(a)+"^2 == "+str(b)+"^2 mod "+str(N))

    factor = gcd(abs(b - a), N)
    print(factor)
    return factor

        
def QS(N, b = None, I = None):
    '''Single polynomial version of quadratic sieve, smoothness bound b and sieve interval I.
    Estimation is provided if unknown. Matrix becomes slow around B = 50000'''

    assert not is_probable_prime(N), "prime"

    for power in range(2, int(log2(N))):  # test for prime powers
        r = int(1000 * pow(N, 1 / power)) // 1000
        if pow(r, power) == N:
            print('found root')
            return r

    print("Data Collection Phase...")
    # set row_tol for extra solutions, bit_tol for sieve fudge factor
    root, row_tol, bit_tol = int(sqrt(N)), 0, 20
    global B
    B = b
    
    if not B:  # automatic parameter estimation
        B = size_bound(N)
        I = B
        print('Estimated B =', B, 'I =', I, '\n')
    elif not I:
        I = B
        
    factor_base = find_base(N, B)
    F = len(factor_base)
    print(F, 'factors in factor base')

    print("\nSearching for {}+{} B-smooth relations...".format(F, row_tol))
    print('Sieving for candidates...')
    smooth_nums, x_list, factors = find_smooth(N, factor_base, I, root, row_tol, bit_tol)
    
    if len(smooth_nums) < F:
        return ("Error: not enough smooth numbers")

    print("\nFound {} relations.".format(len(smooth_nums)))

    if len(smooth_nums)-100 > F: #reduce for smaller matrix
        print('trimming smooth relations...')
        del smooth_nums[F+row_tol:]
        del x_list[F+row_tol:]
        del factors[F+row_tol:]
        print(len(smooth_nums))

    '''for i in range(len(x_list)):
        print(x_list[i], smooth_nums[i], factors[i])'''
    
    print("\nMatrix Phase. Building exponent matrix...")
    is_square, t_matrix = build_matrix(factor_base, smooth_nums, factors)

    if is_square:
        print("Found a square!")
        x = smooth_nums.index(t_matrix)
        factor = (gcd(x_list[x] + isqrt(t_matrix), N))
        return factor, N / factor

    print("\nPerforming Gaussian Elimination...")
    sol_rows, marks, M = gauss_elim(t_matrix)

    print('Finding linear dependencies...')
    solution_vec = solve_row(sol_rows, M, marks, 0)
    factor_base.remove(-1)
    
    print("Solving congruence of squares...")
    factor = solve(solution_vec, smooth_nums, factors, x_list, N, factor_base)

    for K in range(1, len(sol_rows)):
        if (factor == 1 or factor == N):
            print("Trivial. Trying again...")
            solution_vec = solve_row(sol_rows, M, marks, K)
            factor = solve(solution_vec, smooth_nums, factors, x_list, N, factor_base)
        else:
            print("Success!")
            return factor, N // factor

    return 'Fail. Increase B, I or T.'


__version__ = 1.3
