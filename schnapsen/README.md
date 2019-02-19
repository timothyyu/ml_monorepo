Intelligent Systems 2019
========================
This is the practical material for the Intelligent Systems course, based on the
card based strategy game _Schnapsen_.

## Getting started

To get to know the concept of the game, please visit
[this web page](https://www.pagat.com/marriage/schnaps.html).

Your job is to make a bot that will play this game.

## Particularities of our implementation

For this implementation of the game, we mostly followed the rules described in the above link, with a few caveats:
* Partial information about the state of the deck is updated automatically, so you don't have to keep track of it yourself.
* In the same vein, it is not the player's responsibility to keep track of their (and their enemy's) points, as it would be in regular Schnapsen. This is done automatically through the game engine, which also removes the aspect of having to declare that you have reached 66 points in order to win the game.
* "Closing the talon" is not implemented in order to have a clear separation between the imperfect information and the perfect information parts of the game, and also in order to avoid further increasing the branching factor.
* Scoring is implemented as the rules would suggest. A player can receive 1-3 points for winning a round, depending on the score differential. However, play.py and tournament.py play the game only in terms of these rounds, not in terms of a "full game" described as playing rounds until one player reaches 7 points.

## Technical requirements

You require a working Python 3.x environment and a good text editor or an IDE. You can download Python 3.7 for your machine from the following sources:  
* [Windows](https://www.python.org/downloads/windows/) _Note that the code runs significantly slower on Windows due to the way process management is implemented._
* [MacOS](https://www.python.org/downloads/mac-osx/)  
* [Linux](https://www.python.org/downloads/source/)
* [Other](https://www.python.org/download/other/)

For more advanced Windows users that want to use the Linux bash without a virtual machine or dual-booting, consider using [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10). Once set up, this lets you use the command line interface of the respective Linux distribution you chose, with access to the Windows File System. For Linux newcomers, we suggest using Ubuntu. You can then install Python3 and pip through the following command, in case they are not pre-installed. For other distributions, use the equivalent package manager.

```bash
sudo apt install python3 python3-pip
```

For the regular Windows Python installation, be sure to select the _"Add Python 3.x to PATH"_ option in the installation dialogue, so that you can access Python through your command line.

The core game engine runs on pure Python, however you will need to install a few additional packages for tasks throughout the course. This is most easily done through the standard Python package manager, pip. You will most likely already have pip after the Python 3.x installation. You can check by running the following command in your command line interface.

```bash
pip -V
```

If this fails, you can find installation instructions [here](https://pip.pypa.io/en/stable/installing/). Once installed, pip can be accessed from the command line interface, and the required packages can be obtained through the following command:

```bash
pip install sklearn matplotlib flask
```

### Python knowledge

You will of course also need a working knowledge of python. If you're looking to
brush up on your skills, there are many good tutorials available. For instance:
 * https://www.learnpython.org/
 * https://www.codecademy.com/

You do not need to be an expert in python to write a functioning bot. If you
already know another programming language, you should be able to get going within
a day. You'll pick up the details as the project progresses. However, there are
a few things that are important to understand. Check if you know what the
following mean. If not, take some time to google them and read up:

#### Call-by-reference (and "call-by-value")

What happens if I pass a function a 'State' object, and the function changes the
object? Do I keep an unchanged state, or does my state change as well?

#### Object oriented programming

What's the difference between a class and an object? How are these expressed in python?
What does the _self_ keyword do?

#### Recursion

Briefly: a method calling itself. Why would this useful, and how does it work?

#### List comprehensions

Advanced python, but they occur occasionally in the code. Useful to know.

## Examples

Here are some quick use cases and solutions to help you get a feel for the code.

### Get the size of the stock
Let 'state' be the state you're given and let's say you want the size of the stock. Then the following a should do the trick:
```python
size_of_stock = state.get_stock_size()
```

### Find out if I'm player 1 or 2

```python
me = state.whose_turn()
```

### Print the (abbreviated) cards in your hand

```python
cards_hand = state.hand()

for i, card in enumerate(cards_hand):

	rank, suit = util.get_card_name(card)

	print('Card {} in the hand is {} of {}'.format(i, rank,suit))
```

The deck of cards is represented through a list. Each index corresponds to a different card, as per the table below.

|          | Aces | 10s | Kings | Queens | Jacks |
|:--------:|:----:|:---:|:-----:|:------:|:-----:|
| **Clubs**|   0  |  1  |   2   |    3   |   4   |
|**Diamonds**|   5|  6  |   7   |    8   |   9   |
|**Hearts**|  10  |  11 |   12  |   13   |   14  |
|**Spades**|  15  |  16 |   17  |   18   |   19  |

### Generate a random state
```python
state = State.generate()

# To deterministically generate the same state each time, the generate method can also take a seed, like so:

state = State.generate(25)
# This will always generate the same starting state, to make testing/debugging your bots easier.
# Note that any two states generated with the same seed will be identical, and 25 is only used here as an example.
```

### Check if two states are identical

```python
state = State.generate(1)

# same_state is not the same object as state,
# but all attributes are identical.
same_state = State.generate(1)

diff_state = State.generate(2) 

# The equality and inequality operators are overridden for State
# objects, so you can check if all parameters of two states match.

state == same_state # Evaluates to True
state == diff_state # Evaluates to False
```

### Print a representation of the generated state
```python
>>> print(state)

The game is in phase: 1
Player 1's points: 0, pending: 0
Player 2's points: 0, pending: 0
The trump suit is: C
Player 1's hand: QC JD 10H JH 10S
Player 2's hand: 10C AD 10D KH JS
There are 10 cards in the stock
```
### Get own/opponent's points

```python
me = state.whose_turn()
opponent = util.other(me)

own_points = state.get_points(me)
opponents_points = state.get_points(opponent)
```

### Get familiar with the State API

Every state-related function you will use when building your bot can be found, fully documented, in the State class, located in api/_state.py. We *highly recommend* that you read through this class to understand the capabilities available to you when writing your bots.

Note that you only have access to public functions. Private functions, i.e. functions whose name starts with two underscores "__" are used for the internal implementation of the game and are abstracted away from the player.

Reading the code itself in addition to the documentation can help you get acquainted with the internals of the game engine, however this is not obligatory in order to be able to complete the course.

## FAQ

### I found a bit that could be implemented much better/more efficiently.

Our main goal was to write code that was easy to read and to understand. To achieve
this, we've made many methods less efficient than they need to be. This
is especially important for a project like this where many of the students are
novice programmers. It is also a
[good principle](https://en.wikipedia.org/wiki/Program_optimization#When_to_optimize)
in general, at least when you write the first version of your code.

You may feel that your bot is to slow with our State objects, for
instance if you're creating an evaluating lots of State objects in a deep
tree. Luckily, you're not tied to our API: simply take the State object
you're given and copy it to your own, more efficient, implementation. This may
get you another plie or two in the search tree, so if you really want to win the
competition it might be worth it.  

### I found a bug/improvement. Can I fork the project and send a pull request?

Sure! Just remember this is not a regular project: we've tried to minimize the
amount of advanced python, and the number of dependencies. So, it might be that
we're aware of the potential improvement, but we haven't used it just to keep the
code simple for novice programmers.  

### The command-line scripts (play.py, tournament.py) make it difficult to do X

The command line scripts provide a convenient starting point, but if you want to do
something more complex (like try a range of parameters for your bot), they are probably
too limited.

Your best bet is to write your own script that does what you want, and have it call the
engine. Have a look at the function play(...) in  api/engine.py, or have it run a by
itself. See experiment.py for an example.

## Visual interface

To play Schnapsen via the visual interface, you must first make sure that you have Flask installed. Then you can start a local server. The following example starts a server and sets rdeep as the opponent.

```bash
python visual/server.py --opponent rdeep
```

The "--opponent" flag is followed by the name of the bot you want to play against.

To see a full list of parameters and their usage, run:

```bash
python visual/server.py --help
```

Once your server is up and running, you can fire up your favorite (modern) web browser and visit
[http://127.0.0.1:5000/](http://127.0.0.1:5000/), the local address where your server is listening.

The controls are fairly straightforward; click on the card that you want to play to place it on
the table. You can decide to play this move by clicking the "Submit move" button on the top bar, or you can
change your mind with "Reset move". Whenever you have a complex move available, such as a marriage or
a trump jack exchange, the corresponding buttons on the top bar will become available. Finally, you can
use SHIFT + R to start a new game at any time.


## Changes from last year's challenge

The codebase has been ported to Python 3. A visual interface has been added, along with minor fixes and improvements. Bots from last year can be used this year as well.

## Attributions

Vectorized Playing Card Graphics 2.0 - http://sourceforge.net/projects/vector-cards/  
Copyright 2015 - Chris Aguilar - conjurenation@gmail.com  
Licensed under LGPL 3 - www.gnu.org/copyleft/lesser.html
