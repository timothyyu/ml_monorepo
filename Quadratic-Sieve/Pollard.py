import random
import math
import timeit

def gcd(a,b): #greatest common divisor
    if b == 0:
        return a
    elif a >= b:
        return gcd(b,a % b)
    else:
        return gcd(b,a)

def trial(n): #naive factoring algorithm
    if n <= 3:
        return n
    else:
        iters = 0
        i = 3
        while i*i <= n:
            if n % i == 0:
                break
            iters += 1
            i += 2
    
    return iters

def rho_floyd(n): #My pollard's rho using Floyd's cycle detection
    factors = []
    iters = 0
    x,c = random.randint(1,n-1),random.randint(1,n-1)
    y = x 
    divisor = 1
    
    while divisor == 1:
        x = ((x*x)+c)%n
        y = ((y*y)+c)%n
        y = ((y*y)+c)%n
        divisor = gcd(abs(x - y), n)
        iters += 3 #number of times pseudo is executed
        
    if divisor == n:
        return "failure"
    
    else:
        factors.append(divisor)
        factors.append(int(n/divisor))
        return factors,iters,stop - start
          
def rho_brent(n):#My pollard's rho using Brent's cycle detection algorithm
    x, c = random.randint(1,n-1), random.randint(1,n-1)
    y = x
    power = lam = d = 1 #lambda is steps taken, power is step limit, d is divisor
    factors = []
    iters = 0
    
    while d == 1:
        if power == lam: #time to start new power of 2?
            x = y
            power *= 2
            lam = 0 #reset
    
        y = ((y*y)+c)%n #advance hare
        lam += 1 #increment step count
        d = gcd(abs(x - y), n)
        iters += 1
        
    if d == n:
        return "failure"
    
    return iters
    
    
def brent(N): #The actual Brent's method
    iters = 0
    if N % 2 == 0: #test if even
        return 2
    y, c, m = random.randint(1, N - 1), 1, random.randint(1, N - 1)
    #y is hare
    g, r, q = 1, 1, 1 #g is divisor, r is power
    while g == 1:
        x = y #x is tortoise, teleport to hare
        for i in range(r): #executes pseudo(y) once, then by powers of two
            y = ((y * y) % N + c) % N
            iters += 1
        #print("y is now " + str(y))
        k = 0 # weird step counter
        while k < r and g == 1: #its not time to start a new power of two
            ys = y #store y
            #print(m,r-k,min(m, r - k))
            for i in range(min(m, r - k)):
                y = ((y * y) % N + c) % N #pseudo(hare)
                q = q * (abs(x - y)) % N
                iters +=1
            g = gcd(q, N)
            #print("g is "+str(g))
            k = k + m #k now greater than r, so go outside the loop and reset k
        r *= 2
        #print(m,k,r)
    if g == N: #reached end, fail
        #print("g=N")
        while True:
            ys = ((ys * ys) % N + c) % N
            g = gcd(abs(x - ys), N)
            iters += 1
            if g > 1:
                break
    return g

def floyd(N):
        iters = 0
        if N%2==0:
                return 2
        x = random.randint(1, N-1)
        y = x
        c = 2#random.randint(1, N-1)
        g = 1
        while g==1:             
                x = ((x*x)%N+c)%N
                y = ((y*y)%N+c)%N
                y = ((y*y)%N+c)%N
                iters += 3
                g = gcd(abs(x-y),N)
        
        return iters

def average(function, n):#finds the average time and number of iterations
    output = []
    trials = 0
    start = timeit.default_timer()
    for i in range(50): #repeat algorithm
        trials += function(n)
    stop = timeit.default_timer()
    
    output.append((stop-start)/50)
    output.append(trials/50)
    return output
    
def test(function):#reads and creates semiprimes, then tests and stores average performance
    
    f = open("primes1.txt")
    z = 0
    semiprimes = []
    for line in f:
        if(z < 200 and z % 2 == 0 and z != 0):#select every 10000th line
            ls = line.split("     ")
            semiprimes.append(2*int(ls[1])*int(ls[2]))#make semiprimes
            semiprimes.append(3*int(ls[3])*int(ls[4]))#make semiprimes
            semiprimes.append(5*int(ls[5])*int(ls[6]))#make semiprimes
            semiprimes.append(7*int(ls[7])*int(ls[8]))#make semiprimes
        z+=1
    #print(semiprimes)
    print(str(len(semiprimes)) + " semiprimes found.")

    fileName = "trial.txt"

    o = open(fileName,"w")
    o.close()
    o = open(fileName,"a+")

    for n in semiprimes:
        output = average(function, n)
        time = output[0]
        iters = output[1]
        print(iters)
        
        o.write(str(n) + "         " + str(time) + "         " + str(iters))
        o.write("\n")
    o.close()
    print("Finished.")

'''s = input("Enter a number to factor: ")
#while(s.lower()!="exit"):
print(brent(int(s)))
#print(find_iters(eval(s)))
s = input("Enter a number to factor (exit to exit): ")'''
