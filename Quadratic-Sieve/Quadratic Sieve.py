from math import fabs, ceil, sqrt, exp, log
import random
from MillerRabin import is_probable_prime
from itertools import chain

def gcd(a,b): # Euclid's algorithm
    if b == 0:
        return a
    elif a >= b:
        return gcd(b,a % b)
    else:
        return gcd(b,a)

def isqrt(n): # Newton's method, returns exact int for large squares
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x

def mprint(M): #prints a matrix in readable form
    for row in M:
        print(row)
        
def prime_gen(n): # sieve of Eratosthenes, generates primes up to a bound n
    if n < 2:
        return []
    
    nums = []
    isPrime = []
    
    for i in range(0, n+1):#Creates list of numbers from 0 to n
        nums.append(i)
        isPrime.append(True)
        
    isPrime[0]=False
    isPrime[1]=False
    
    for j in range(2,int(n/2)):#tries all size gaps that make sense
        if isPrime[j] == True:
            for i in range(2*j,n+1,j):#starts from j+j, jumps by gap size j and crosses out that number
                isPrime[i] = False
                
    primes = []
    for i in range(0, n+1):#Adds leftovers
        if isPrime[i] == True:
            primes.append(nums[i])
            
    return primes


def pollard(N,factors): # completely factors N using Pollard Rho, given a list
    
    rem = N
    while True:
        if is_probable_prime(rem):
            factors.append(rem)
            break

        f = brent(rem)
        while f == rem:#ensures pollard rho returns a smaller factor
            f = brent(rem)
            
        if f and f < rem: #found a factor
            if is_probable_prime(f): #ensure f is prime
                #print("Pollard rho (Brent): Prime factor found: %s" % f)
                factors.append(f)
                rem = rem//f #other factor
            else: #factor is composite
                #print("Pollard rho (Brent): Non-prime factor found: %s" % f)
                rem_f = factor(f,factors) #recursive part
                rem = (rem//f) * rem_f #combines the two remainders
                factors.remove(rem_f)#removes tricky duplicate that got appended in 1st if stmt
        else: #no more factors found, rem is prime
            #print("No (more) small factors found.")
            break
                 
    return rem


def legendre(a, p): #legendre symbol of (a/p)
    return pow(a, (p - 1) // 2, p)
 
def tonelli(n, p): #tonelli-shanks to solve modular square root, x^2 = N (mod p)
    assert legendre(n, p) == 1, "not a square (mod p)"
    q = p - 1
    s = 0
    while q % 2 == 0:
        q //= 2
        s += 1
    if s == 1:
        r = pow(n, (p + 1) // 4, p)
        return r,p-r
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

    return (r,p-r)

        
def size_bound(N): # finds optimal factor base size and interval

    F = pow(exp(sqrt(log(N)*log(log(N)))),sqrt(2)/4)
    I = F**3
    print(F,I)
    return int(F),int(I)

    
def find_base(N,B):
# generates a B-smooth factor base

    factor_base = []
    primes = prime_gen(B)
    #print(primes)
    
    for p in primes: # such that N is a quadratic residue mod p
        if legendre(N,p) == 1:
            factor_base.append(p)
    return factor_base

def find_base1(N,F):
# generates an F-long factor base

    factor_base = []
    primes = prime_gen(P*10) # kind of arbitrary
    #print(primes)
    
    for p in primes:
        if len(factor_base) == F:
            break
        if legendre(N,p) == 1:
            factor_base.append(p)
    return factor_base

def find_smooth(factor_base,N,I):
# tries to find B-smooth numbers in sieve_seq, using sieving

    def sieve_prep(N,sieve_int):
    # generates a sequence from Y(x) = x^2 - N, starting at x = root 
        sieve_seq = [x**2 - N for x in range(root,root+sieve_int)]
        #sieve_seq_neg = [x**2 - N for x in range(root,root-sieve_int,-1)]
        return sieve_seq

    sieve_seq = sieve_prep(N,I)
    sieve_list = sieve_seq.copy() # keep a copy of sieve_seq for later

    if factor_base[0] == 2:
        i = 0
        while sieve_list[i] % 2 != 0:
            i += 1
        for j in range(i,len(sieve_list),2): # found the 1st even term, now every other term will also be even
            while sieve_list[j] % 2 == 0: #account for powers of 2
                sieve_list[j] //= 2
        
    for p in factor_base[1:]: #not including 2
        residues = tonelli(N,p) #finds x such that x^2 = n (mod p). There are two start solutions
        #print(residues)
        
        for r in residues:
            print((r-root)%p)
            for i in range((r-root) % p, len(sieve_list), p): # Now every pth term will also be divisible
                while sieve_list[i] % p == 0: #account for prime powers
                    sieve_list[i] //= p
                                     
    xlist = [] #original x terms
    smooth_nums = []
    indices = [] # index of discovery
    
    for i in range(len(sieve_list)):
        if len(smooth_nums) >= len(factor_base)+T: #probability of no solutions is 2^-T
            break
        if sieve_list[i] == 1: # found B-smooth number
            smooth_nums.append(sieve_seq[i])
            xlist.append(i+root)
            indices.append(i)
    return(smooth_nums,xlist,indices)
                
def find_smooth1(factor_base,N,I): #accounts for -1 in factor base

    def sieve_prep(N,I):
    # generates a sequence from Y(x) = x^2 - N, starting at x = root - I
        
        xlist = [x for x in range(root-I,root+I)]
        sieve_seq = [x**2 - N for x in range(root-I,root+I)]
        
        return sieve_seq
    
    sieve_seq = sieve_prep(N,I)
    sieve_list = sieve_seq.copy() # keep a copy of sieve_seq for later
    
    if factor_base[0] == 2:
        i = 0
        while sieve_list[i] % 2 != 0:
            i += 1
        for j in range(i,len(sieve_list),2): # found the 1st even term, now every other term will also be even
            while sieve_list[j] % 2 == 0: #account for powers of 2
                sieve_list[j] //= 2
        
    for p in factor_base[1:]: #not including 2
        residues = tonelli(N,p) #finds x such that x^2 = n (mod p). There are two start solutions
        #print(residues)
        
        for r in residues:
            
            for i in range((r-root+I) % p, len(sieve_list), p): # Now every pth term will also be divisible
                while sieve_list[i] % p == 0: #account for prime powers
                    sieve_list[i] //= p
                    
            for i in range(((r-root+I) % p)+I, 0, -p): # Going the negative direction!
                while sieve_list[i] % p == 0: #account for prime powers
                    sieve_list[i] //= p
                    
    #print(sieve_list)
    indices = [] # index of discovery
    xlist = [] #original x terms
    smooth_nums = []
    
    for i in range(len(sieve_list)):
        if len(smooth_nums) >= len(factor_base)+T: #probability of no solutions is 2^-T
            break
        elif sieve_list[i] == 1 or sieve_list[i] == -1: # found B-smooth number
            smooth_nums.append(sieve_seq[i])
            xlist.append(i+root-I)
            indices.append(i)
    return(smooth_nums,xlist,indices)

def build_matrix(smooth_nums,factor_base):
# generates exponent vectors mod 2 from previously obtained smooth numbers, then builds matrix

    def factor(n,factor_base):#trial division from factor base
        factors = []
        if n < 0:
            factors.append(-1)
        for p in factor_base:
            if p == -1:
                pass
            else:
                while n % p == 0:
                    factors.append(p)
                    n //= p
        return factors

    M = []
    factor_base.insert(0,-1)

    for n in smooth_nums:
        exp_vector = [0]*(len(factor_base))
        n_factors = factor(n,factor_base)
        print(n,n_factors)
        for i in range(len(factor_base)):
            if factor_base[i] in n_factors:
                exp_vector[i] = (exp_vector[i] + n_factors.count(factor_base[i])) % 2

        #print(n_factors, exp_vector)
        if 1 not in exp_vector: #search for squares
            return True, n
        else:
            pass
        
        M.append(exp_vector)
        
    #print("Matrix built:")
    #mprint(M)
    return(False, transpose(M))

    
def transpose(matrix):
#transpose matrix so columns become rows, makes list comp easier to work with
    new_matrix = []
    for i in range(len(matrix[0])):
        new_row = []
        for row in matrix:
            new_row.append(row[i])
        new_matrix.append(new_row)
    return(new_matrix)

'''def optimize(M):
    for row in M: #matrix optimization; delete factors that only occur once
        if row.count(1) == 1:
            for r in M:
                del r[row.index(1)]
            del row

    return(M)'''
        
def gauss_elim(M):
#reduced form of gaussian elimination, finds rref and reads off the nullspace
#https://www.cs.umd.edu/~gasarch/TOPICS/factoring/fastgauss.pdf
    #mprint(M)
    #M = optimize(M)
    marks = [False]*len(M[0])
    
    for i in range(len(M)): #do for all rows
        row = M[i]
        #print(row)
        
        for num in row: #search for pivot
            if num == 1:
                #print("found pivot at column " + str(row.index(num)+1))
                j = row.index(num) # column index
                marks[j] = True
                
                for k in chain(range(0,i),range(i+1,len(M))): #search for other 1s in the same column
                    if M[k][j] == 1:
                        for i in range(len(M[k])):
                            M[k][i] = (M[k][i] + row[i])%2
                break
            
    print(marks)
    M = transpose(M)
    #mprint(M)
    
    sol_rows = []
    for i in range(len(marks)): #find free columns (which have now become rows)
        if marks[i]== False:
            free_row = [M[i],i]
            sol_rows.append(free_row)
    
    if not sol_rows:
        return("No solution found. Need more smooth numbers.")

    print("Found {} potential solutions".format(len(sol_rows)))
    return sol_rows,marks,M

def solve_row(sol_rows,M,marks,K=0):
    solution_vec, indices = [],[]
    free_row = sol_rows[K][0] # may be multiple K
    for i in range(len(free_row)):
        if free_row[i] == 1: 
            indices.append(i)
    
    for r in range(len(M)): #rows with 1 in the same column will be dependent
        for i in indices:
            if M[r][i] == 1 and marks[r]:
                solution_vec.append(r)
                break
            
    print("Found linear dependencies at rows "+ str(solution_vec))     
    solution_vec.append(sol_rows[K][1])       
    return(solution_vec)
    
def solve(solution_vec,smooth_nums,xlist,N):
    
    solution_nums = [smooth_nums[i] for i in solution_vec]
    x_nums = [xlist[i] for i in solution_vec]
    print(solution_nums,x_nums)
    
    Asquare = 1
    for n in solution_nums:
        Asquare *= n
    #print(Asquare)
        
    b = 1
    for n in x_nums:
        b *= n

    a = isqrt(Asquare)
    print(str(a)+"^2 = "+str(b)+"^2 mod "+str(N))
    
    factor = gcd(b-a,N)
    return factor


def QS(n,B,I):
#single polynomial version of quadratic sieve, given smoothness bound B and sieve interval I
    
    global N
    global root
    global T #tolerance factor
    N,root,K,T = n,int(sqrt(n)),0,1

    if is_probable_prime(N):
        return "prime"
    
    if isinstance(sqrt(N),int):
        return isqrt(N)
    
    #print(root)
    print("Attempting to factor {}...".format(N))
    #F,I = size_bound(N)
    
    print("Generating {}-smooth factor base...".format(B))
    factor_base = find_base(N,B) #generates a B-smooth factor base
    #print(factor_base)

    global F
    F = len(factor_base)
    
    print("Looking for {} {}-smooth relations...".format(F+T,B))
    smooth_nums,xlist,indices = find_smooth1(factor_base, N,I)
    #finds B-smooth relations, using sieving and Tonelli-Shanks
    
    print("Found {} smooth relations.".format(len(smooth_nums)))
    print(indices)
    print(xlist)
    print(smooth_nums)
    
    if len(smooth_nums) < len(factor_base):
        return("Not enough smooth numbers. Increase the sieve interval or size of the factor base.")
    
    print("Building exponent matrix...")
    is_square, t_matrix = build_matrix(smooth_nums,factor_base)
    #builds exponent matrix mod 2 from relations
    
    if is_square == True:
        x = smooth_nums.index(t_matrix)
        factor = gcd(xlist[x]+sqrt(t_matrix),N)
        print("Found a square!")
        return factor, N/factor
    
    print("Performing Gaussian Elimination...")
    sol_rows,marks,M = gauss_elim(t_matrix) #solves the matrix for the null space, finds perfect square
    solution_vec = solve_row(sol_rows,M,marks,0)
    
    '''vec = [0]*len(smooth_nums) # prints solution vector
    for i in solution_vec:
        vec[i] = 1
    print("Solution vector found: " + str(vec))'''
    
    print("Solving congruence of squares...")
    factor = solve(solution_vec,smooth_nums,xlist,N) #solves the congruence of squares to obtain factors

    for K in range(1,len(sol_rows)):
        if (factor == 1 or factor == N):
            print("Didn't work. Trying different solution vector...")
            solution_vec = solve_row(sol_rows,M,marks,K)
            factor = solve(solution_vec,smooth_nums,xlist,N)
        else:
            print("Found factors!")
            return factor, N/factor
            
            
    return("Didn't find any nontrivial factors!")
                   
    
    
