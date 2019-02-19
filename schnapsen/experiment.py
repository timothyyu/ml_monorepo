"""

This script shows an example of how to run a simple computational experiment. The research
question is as follows:

    What is the value of saving your trump cards for the late stages of the game?

As a first step towards answering this question, we will make two assumptions:

    1) Players have two options: play randomly, or play highest value non-trump card
    2) Players decide between these two entirely at random

Under these simplified circumstances, how often should players decide to save their trump cards?
This is a simple question to answer, we simply build rand bots for a range of parameters, and play a few games for each
combination. We plot the results in a heat map

"""
import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot as plt
from api import State, util

import random

# Define the bot:
# (we're not using it with the command line tools, so we can just put it here)
class Bot:

    # Probability of moving with non-trump cards
    __non_trump_move = 0.0
    def __init__(self, non_trump_move=0.0):
        self.__non_trump_move = non_trump_move

    def get_move(self, state):

        if random.random() < self.__non_trump_move:

            # IMPLEMENT: Make the best non-trump move you can. Use the best_non_trump_card method written below.
            pass

        #IMPLEMENT: Make a random move (but exclude the best non-trump move from above)
        pass


def empty(n):
    """
    :param n: Size of the matrix to return
    :return: n by n matrix (2D array) filled with 0s
    """
    return [[0 for i in range(n)] for j in range(n)]

def best_non_trump_card(state):
    """
    :param state: A state object
    :return: A move tuple representing the highest rank non-trump move available
    """

    # All legal moves
    moves = state.moves()
    chosen_move = moves[0]

    lowest_suit_moves = []

    #Get all moves which are not trump suit or matching the suit of the enemy's card
    for move in moves:

        if move[0] is not None and util.get_suit(move[0]) != state.get_trump_suit():
            lowest_suit_moves.append(move)

    if len(lowest_suit_moves) == 0:
        lowest_suit_moves = moves

    # Get move with highest rank available, of the subset that we've narrowed down so far
    for move in lowest_suit_moves:
        if move[0] is not None and move[0] % 5 <= chosen_move[0] % 5:
            chosen_move = move

    return chosen_move

# For experiments, it's good to have repeatability, so we set the seed of the random number generator to a known value.
# That way, if something interesting happens, we can always rerun the exact same experiment
seed = random.randint(1, 1000)
print('Using seed {}.'.format(seed))
random.seed(seed)

# Parameters of our experiment
STEPS = 10
REPEATS = 5

inc = 1.0/STEPS

# Make empty matrices to count how many times each player won for a given
# combination of parameters
won_by_1 = empty(STEPS)
won_by_2 = empty(STEPS)


# We will move through the parameters from 0 to 1 in STEPS steps, and play REPEATS games for each
# combination. If at combination (i, j) player 1 winds a game, we increment won_by_1[i][j]

for i in range(STEPS):
    for j in range(STEPS):
        for r in range(REPEATS):

            # Make the players
            player1 = Bot(inc * i)
            player2 = Bot(inc * j)

            state = State.generate()

            # play the game
            while not state.finished():
                player = player1 if state.whose_turn() == 1 else player2
                state = state.next(player.get_move(state))

            #TODO Maybe add points for state.winner()
            if state.finished():
                winner, points = state.winner()
                if winner == 1:
                    won_by_1[i][j] += points
                else:
                    won_by_2[i][j] += points

        print('finished {} vs {}'.format(inc * i, inc * j))



# This
result = [[0 for i in range(STEPS)] for j in range(STEPS)]

extreme = float('-inf')
for i in range(STEPS):
    for j in range(STEPS):
        # How many more games player 1 won than player 2
        result[i][j] = float(won_by_1[i][j] - won_by_2[i][j])

        # Find the largest absolute value
        extreme = max(extreme, abs(result[i][j]))

# Plot the data as a heatmap
plt.imshow(
    result,
    extent=(0,1,0,1), # fit it to the square from (0,0) to (1,1)
    vmin=-extreme,  # give this value the lowest color (blue)
    vmax=extreme,    # give this value the higest color (red)
    interpolation='nearest', # don't smooth the colors
    origin='lower')    # put the result[0][0] in the bottem left corner

# Always label your axes
plt.xlabel('player 1 lowmove probability')
plt.ylabel('player 2 lowmove probability')

# Set the red/blue colormap
plt.set_cmap('bwr')
plt.colorbar()

plt.savefig('experiment.pdf')
