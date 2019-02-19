"""
This file contains functions to regulate game play.
"""
from api import State, Deck, util
from multiprocessing import Process, Manager

def play(
            player1,            # type: Bot
            player2,            # type: Bot
            state,              # type: State
            max_time=5000,      # type: int
            verbose=True,       # type: bool
            fast=False          # type: bool
        ):
    """
    Play a game between two given players, from the given starting state.
    """
    pr('player1: {}'.format(player1), verbose)
    pr('player2: {}'.format(player2), verbose)

    # The game loop
    while not state.finished():

        player = player1 if state.whose_turn() == 1 else player2

        # We introduce a state signature which essentially obscures the deck's perfect knowledge from the player
        given_state = state.clone(signature=state.whose_turn()) if state.get_phase() == 1 else state.clone()

        move = player.get_move(given_state) if fast else get_move(given_state, player, max_time, verbose)

        if is_valid(move, player): # check for common mistakes


            if move[0] is None:
                pr('*   Player {} performs a trump jack exchange'.format(state.whose_turn()), verbose)
            
            else:
                pr('*   Player {} plays: {}{}'.format(state.whose_turn(), util.get_rank(move[0]), util.get_suit(move[0])), verbose)
                
                if move[1] is not None:
                    pr('*   Player {} melds a marriage between {}{} and {}{}'.format(state.whose_turn(), util.get_rank(move[0]), util.get_suit(move[0]), util.get_rank(move[1]), util.get_suit(move[1])), verbose)

            state = state.next(move)
            pr(state, verbose)

            if not state.revoked() is None:
                pr('!   Player {} revoked (made illegal move), game finished.'.format(state.revoked()), verbose)
        
        else:
            state.set_to_revoked()

    pr('Game finished. Player {} has won, receiving {} points.'.format(state.winner()[0], state.winner()[1]), verbose)

    return state.winner()

def get_move(state, player, max_time, verbose):
    """
    Asks a player bot for a move. Creates a separate process, so we can kill
    computation if ti exceeds a maximum time.
    :param state:
    :param player:
    :return:
    """
    # We call the player bot in a separate process.This allows us to terminate
    # if the player takes too long.
    manager = Manager()
    result = manager.dict() # result is a variable shared between our process and
                            # the player's. This allows it to pass the move to us

    # Start a process with the function 'call_player' and the given arguments
    process = Process(target=call_player, args=(player, state, result))

    # Start the process
    process.start()

    # Rejoin at most max_time miliseconds later
    process.join(max_time / 1000)

    # Check if the process terminated in time
    move = None
    if process.is_alive():
        pr('!   Player {} took too long, game revoked.'.format(state.whose_turn()), verbose)

        process.terminate()
        process.join()
        move = "Late"

    else:
        # extract the move
        if 'move' in result:
            move = result['move']

    return move

def call_player(player, state, result):
    # Call the player to make the move
    move = player.get_move(state)
    # Put the move in the shared variable, so it can be read by the
    # engine process
    result['move'] = move


def pr(string, verbose):
    """
    Print the given message if verbose is true, otherwise ignore.

    :param string: Message to print
    :param verbose: Whether to print the message
    """
    if(verbose):
        print(string)

#Syntax checking the move
def is_valid(
        move, # type: tuple[int, int]
        player):
    """
    Check a move for common mistakes, and throw a (hopefully) helpful error message if incorrect.

    :param move:
    :param player:
    """

    if move == "Late":
        return False

    if not type(move) is tuple:
        print('Bot {} returned a move {} that was not a pair (i.e. (2,3))'.format(player, move))
        return False

    if len(move) != 2:
        print('Bot {} returned a move {} that was not of length 2.'.format(player, move))
        return False
    
    if ((type(move[0]) is not int) and (move[0] is not None)) or ((type(move[1]) is not int) and (move[1] is not None)):
        print('Bot {} returned a move {} that was not a tuple for which each element is either an int or None'.format(player, move))
        return False

    if move[0] is None and move[1] is None:
        print('Bot {} returned (None, None). At least one of the elements needs to be an integer.'.format(player))
        return False

    return True
