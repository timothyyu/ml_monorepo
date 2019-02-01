# Author: Legendnic @ ael
# Title: Combination of GA and CNN
# This code is for template. It is much more better if you
# grasp the idea and change it for your own purpose.
# This is because, I am using fully extensive libraries, which I am
# afraid that it won't work on your computer.
# Thus, I hope you guys find a way of making this on your own, for the sake of
# better performance.

# First, import all oof these libraries.

import numpy as np
import pandas as pd
from random import choice, uniform, random, randint
from operator import itemgetter, attrgetter

# Second, import deep learning library
import keras
from keras import backend as K
from keras.models import Sequential
from keras.layers import Conv2D,MaxPooling2D,Dropout,Activation,Flatten,Dense
from keras.optimizers import Adam
from keras.preprocessing.image import ImageDataGenerator
import os

# Declare the foundation of GA: Variable .
population = [] # placeholders for individual/chromosomes.
noPop = 6 # number of chromosomes in a population. Please note that this might
# causing overhead to our computation
fmap = [16,32,64,128,256] # each value is the features map value. this indicate
# how much features map need to produce
kernel = [2,3,5,7,9] # kernel is the window size to produce features map.
activation = ['relu','sigmoid','tanh'] #this is the activation function to transform
# features map before pooling
dropout = [0.0,0.1,0.2,0.3,0.4,0.5] # this is dropout value
learningRate = [0.0001,0.0005, 0.001, 0.005, 0.01,0.05,0.1,0.5] #this is
# learning rate for cnn
mutationRate = 0.3 #mutation rate for offspring to randomly change the allele value
noGen = 10 # number of generation loop

K.set_image_dim_ordering('th')
# Declare cnn settings
trainPath = 'D:\\MicroExpression\\Preprocess\\Train'
# this is path for training datasets. you can change according where
# you store your datasets
np.random.seed(12) # seeding
train = ImageDataGenerator().flow_from_directory(trainPath,target_size=(128,128),classes=['Anger','Happy','Sad'],color_mode='grayscale',batch_size=30)

def initializingPopulation(population,noPop): # function to initializing chromosomes in population
    for i in range (0,noPop): # ieach iteration will generate a chromosome
        loss = 0.0
        accuracy = 0.0
        inPop = [choice(fmap),choice(kernel),choice(activation),choice(dropout),choice(learningRate),loss,accuracy]
        # the command of choice is to randomly select the members of the list.
        # loss and accuracy need to be set as 0.0 because the is no chromosome evaluation yet.
        # in case of my project, loss and accuracy become my objective function/ fitness value
        # the formula is min(Loss),max(Accuracy).
        population.append (inPop)
        # Now, append it to global list variable known as Population

def rankSelection (population,noPop): # this is to ranking up and select half of the best chromosomes
    population = sorted(population,key=itemgetter(5))
    # code above is to ranking the lowest loss, which in ascending order
    # in logical point of view, the lowest lost will be sorted at the top of population
    population = sorted(population,key=itemgetter(6),reverse=True)
    # code above is to ranking the highest accuracy, in descending order
    # in logical point of view, the highest accuracy will be sorted at the top of population
    noHalfPopulation = noPop//2 # this is to get half number of overall population
    halfPopulation = population[:noHalfPopulation]
    # in logic, the index of the list start with 0
    # therefore, [:noHalfPopulation] denote select chromosomes higher than (<) noHalfPopulation
    # example:
    # total population of chromosomes is 20
    # noHalfPopulation is 10
    # [:noHalfPopulation] = [:10]
    # this indicate that chromosomes with index 0-9 will be selected

    return halfPopulation

def tournamentSelection(selectedRank,tSize): # this is tournament selection function
    #selectedRank is the placeholders of half best chromosomes
    #tSize is tournament size
    best = None # variable that hold the only best fitness value
    for i in range(0,tSize):
        # this loop is to make sure that the returned candidate isn't same for the second time
        ind = choice(selectedRank) #randomly selected a candidate
        if best == None:
            # if variable beest does not hold any chromosome
            best = ind
            # the variable best will hold onto randomly selected chromosome
        elif best == ind:
            # if chromosome best and random are identical,
            ind = choice(selectedRank)
            # it then will randomly select another chromosome

        if best[5]>ind[5] and best[6]<ind[6]:
            # executed only if variable ind loss is lower and accuracy is higher than variable best
            best = ind
            #the chromosome in ind will replace chromosome in variable best

    return best

def crossover(p1,p2): # this is crossover function
    crossoverPoint = len(p1)//2 # to get center of the chromosome
    # however, this is my project.
    # I advicing you guys to make randomly one point or k-point crossover
    # here the logic that I can think of:
    # crossoverPoint = random.random(0,4)
    # the value in crossoverPoint then will become notion to slicing the chromosome
    # as you guys can see there, the index is starting from 0 to 4
    # I deliberately not include index 5 and 6
    # this is because index of 5 is for loss
    # index 6 is for accuracy
    # both of it, in my project, is the fitness value
    # it doesn't make any sense if those indexes become crossover cut point

    c1 = p1[:crossoverPoint] + p2[crossoverPoint:]
    # this is variable child 1
    # p1[:crossoverPoint] indicates the head of parent 1
    # p2[crossoverPoint:] indicate tail of parent 2
    # :crossoverPoint means index lower than crossoverPoint will be selected as head
    # crossoverPoint: indicate the index of crossoverPoint will be included as tail
    # example:
    # :6 means indexes of 0 to 5 will be selected as head
    # 6: means indexes of 6 to 9 will be selected as tail

    c2 = p2[:crossoverPoint] + p1[crossoverPoint:]
    # this variable will become the second child
    # parent 2 as head, parent 1 as tail

    return c1, c2

def mutation (c1,c2):
    # this is mutation function
    rate = round(random(),2)
    print(c1)
    print(c2)
    
    print ('rate: ' +str(rate))
    # the rate variable will randomly generate value from 0 to 1
    if rate<=mutationRate:
        # this if-else statement is to execute mutation
        # if variable rate lower or equal to variable mutationRate
        # this if-else statement will execute
        length = len(c1)-2
        print ('length: '+str(length))
        # the variable i will become limitation condition for randomly generated index
        index = randint(0,length)
        print('index: ' +str(index))
        # this variable will generate random integer from 0 to lower than length of chromosome
        # this exclude the index of loss and accuracy
        # this is because mutating loss and accuracy doesn't make any sense

        if index == 0:
            c1[index] = choice(fmap)
            c2[index] = choice(fmap)
            # this is to change value of index 0 for both childs
        elif index == 1:
            c1[index] = choice(kernel)
            c2[index] = choice(kernel)
            # this is to change value of index 1 for both childs
        elif index == 2:
            c1[index] = choice(activation)
            c2[index] = choice(activation)
            # this is to change value of index 2 for both childs
        elif index == 3:
            c1[index] = choice(dropout)
            c2[index] = choice(dropout)
            # this is to change value of index 3 for both childs
        elif index == 4:
            c1[index] = choice(learningRate)
            c2[index] = choice(learningRate)
            # this is to change value of index 4 for both childs

    return c1,c2

def cnn(population):
    # this function is for cnn
    # Making 2 different kind of file kinda headache for me
    #but, if no one understand how it goes, later i will commit the separate files
    for p in population:
        #this is where the fitness value will evaluate
        f = p[0] # features map variable
        k = p[1] # kernel variable
        a = p[2] # activation function variable
        d = p[3] # dropout variable
        l = p[4] # learning rate variable
        print(f,k,a,d,l)
        model=Sequential()
        model.add(Conv2D(f,(k,k),input_shape=(128,128,1),border_mode='same'))
        model.add(Activation(a))
        model.add(MaxPooling2D(pool_size=(2,2),border_mode='same'))
        model.add(Flatten())
        model.add(Dense(32*32))
        model.add(Dropout(d))
        model.add(Dense(3))
        model.add(Activation('softmax'))

        model.compile(Adam(l),loss='categorical_crossentropy',metrics=['accuracy'])

        history = model.fit_generator(train,epochs=100,steps_per_epoch=10,verbose=2)
        acc = np.mean(history.history['acc'])
        loss = np.mean(history.history['loss'])
        print(acc)
        print(loss)

        p[5] = loss
        p[6] = acc
        print(p[5])
        print(p[6])

# Here is how the code executed
initializingPopulation(population,noPop)
# Start with initializing population
print ('Generation 0')
for p in population:
    print(p)

for gen in range(0,noGen):
    # looping for generation
    # convolutional neural network fitness value
    cnn(population)
    # after cnn fitness evaluation, it will be ranked
    selectedRank = rankSelection(population,noPop)
    print('Selected Ranked Chromosomes:')
    for sr in selectedRank:
        print(sr)

    if selectedRank[-1][5]<6 and selectedRank[-1][6]>0.6:
        # this is  stopping condition for genetic algorithm.
        # you can change or delete it if you want
        # but, remember, waiting for 10 generation is time consumption
        # and also computationally overhead
        break
    else:
        child = [] #childs placeholders
        tSize = 2 # this indicate 2-way tournament
        numberOfMating = len(selectedRank)//2
        # this is limiter  for number of child will generate
        # let say, you have 12 total population
        # let say, you have 6 ranking selection
        # the mating process will be 3 time
        # but, since the generated child is 2
        # thus mating process would generate 6 children
        # this is because number of mating * generated Children = half new population
        # 3 mating process * 2 newly generated child = 6 population
        for i in range (0,numberOfMating):
            #this is where mating process take place
            parent1 = tournamentSelection(selectedRank,tSize)
            parent2 = tournamentSelection(selectedRank,tSize)
            while parent2 is parent1:
                parent2 = tournamentSelection(selectedRank,tSize)
                #this is to make sure the candidate does not identical
            c1,c2 = crossover(parent1,parent2)
            print('Child 1: %s child 2: %s'%(c1,c2))
            c1,c2 = mutation(c1,c2)
            child.append(c1)
            child.append(c2)

        population.clear() # clearing old population
        population = selectedRank + child # combining the best half of old population with new childs
        # known as elitism method

        print ('New Child' + str(gen))
        for c in child:
            print(c)

        print('New Generation ' + str(gen+1))
        for p in population:
            print(p)

# please remember that it is much more better if you grasp the idea and make on your own
# or you could change according to your fits
