In this section, I will explain how my GA actually works.
There are 5 steps taken to complete the whole process of GA.

Initialization:
For initialization, I am using built-in python list to store every variables, including my fitness functions.

Features Map | Kernel Size | Activation Function | Dropout | Learning Rate | Fitness Value Loss | Fitness Value Accuracy

This list will never change in terms of index. what actually that changing is the value of each allele, where it is based on 
predefined list. Each value is randomly selected and stored into this list for the initialization process. 

This is the parameters for CNN:

Features Map : 16, 32, 64, 128, 256
Kernel: 2, 3, 5, 7, 9
Activation Function: Sigmoid, relu, tanh
Dropout: 0.0, 0.1, 0.2, 0.3, 0.4, 0.5
Learning Rate: 0.0001,0.0005, 0.001, 0.005, 0.01,0.05,0.1,0.5

This is parameters for GA:
Population: 6 (Example)
Mutation rate: 0.3
Number of Generation/ Looping: 10

For the starting point, each accuracy and loss will be defined as 0.0. This is because it is not evaluate yet.

The Fitness Evaluation:
Immediately after generating random chromosomes, each chromosomes will perform CNN training. After that, each value for accuracy
loss will be recorded at the end of each chromosome. 

Selection:
In my code, I used Rank Selection and Tournament Selection. This is because the chromosomes first need to be ranked up accordingly,
before entering the next process.
After ranking up based on lower loss and higher accuracy, half of these population will be selected to perform the tournament selection.
In tournament selection, the chromosomes are randomly selected, and only once for it to be selected for each tournament. 
this mean that when Parent 1 is selecting chromosome A, I will make sure that the Parent 2 cannot select the same chromosome.
this is to produce the variety of offspring, so that it won't same as their parent afterward. 

Crossover:
In my case, I always use one-point crossover. for the splitting point, I split at the center of chromosomes. You can change the
code to randomly select the splitting point on your own.

Mutation:
I use Pm with the value of 0.3, so that the chromosome will not exchange too often. then, if the Pm below or equal to 0.3 the allele
will randomly selected and change the value within it randomly based on predefined parameters.

Replacement:
In this section, I used elitism to preserve the best chromosomes for the next population. that is why I am using rank-based
selection to automatically sorting out the best candidates. only the worst candidates will be delete from the population and
replaced with the new offspring.
