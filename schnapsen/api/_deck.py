import random

class Deck:
	"""
	Represents the deck at any given turn.
	"""

	__RANKS = ["A", "10", "K", "Q", "J"]
	__SUITS = ["C", "D", "H", "S"]

	# A list of length 20 representing all cards and their states
	__card_state = None # type: list[str]

	# A list of length 20 representing all KNOWN cards and
	# their states from the perspective of each player
	__p1_perspective = None
	__p2_perspective = None

	#We use the following index representations for cards:

	# Suit order: CLUBS, DIAMONDS, HEARTS, SPADES

	# 0, 5, 10, 15 - Aces
	# 1, 6, 11, 16 - 10s
	# 2, 7, 12, 17 - Kings
	# 3, 8, 13, 18 - Queens
	# 4, 9, 14, 19 - Jacks

	# List that holds cards which are played at any one time.
	# Can contain two Nones, one None and an int, or two ints.
	# The ints represent the index of the played cards according to the scheme above.
	__trick = [None, None] # type: list[int], list[None]

	# Variable that stores the previous trick that was evaluated.
	# Starts out as [None, None], then [int, int] after
	# the first trick has been evaluated.
	__previous_trick = [None, None];

	# A variable length list of card indexes representing the
	# cards currently in stock, and more importantly, their order.
	# First index in this list is always the trump_suit card, last index
	# is where the cards are taken from the stock.
	__stock = None # type: list[int]

	# The suit of the trump_suit card for this given deck instance.
	__trump_suit = None # type: String

	__signature = None

	def __init__(self,
				card_state,	# type: list[str]
				stock,		# type: list[int]
				p1_perspective=None, # type: list[str]
				p2_perspective=None, # type: list[str]
				trump_suit=None #type:String
				):
		"""
		:param card_state: list of current card states
		:param card_state: list of current card states
		:param card_state: list of current card states

		:param stock: list of indexes of cards in stock
		:param trump_suit: {C,D,H,S}
		"""

		self.__card_state	= card_state

		self.__p1_perspective = p1_perspective
		self.__p2_perspective = p2_perspective

		self.__stock		= stock

		self.__trump_suit	=  trump_suit if trump_suit is not None else self.get_suit(self.__stock[0])



	# Computes the rank of a given card index, following the ordering given above.
	@staticmethod
	def get_rank(index):
		return Deck.__RANKS[index % 5]


	# Computes the suit of a given card index, following the ordering given above.
	@staticmethod
	def get_suit(index):
		return Deck.__SUITS[int(index/5)]

	# Returns a list of all the cards' states
	def get_card_states(self):
		return list(self.__card_state)

	# Returns the state of the card at the specified index
	def get_card_state(self, index):
		return self.__card_state[index]

	# Returns a list of all cards currently in the stock
	def get_stock(self):
		if self.get_stock_size() > 0:

			return self.__stock if self.__signature is None else [self.__stock[0]] + ['U']*(self.get_stock_size()-1)

		return []

	# Returns the number of cards currently in the stock
	def get_stock_size(self):
		return len(self.__stock)

	# Sets the card at the specified index to the specified state
	def set_card(self, index, state):
		self.__card_state[index] = state

	# Returns a tuple containing the card indices of the cards currently part of the trick. The index of a card will be
	# set to None if no card is put down on that side of the trick. TODO: strange wording
	def get_trick(self):
		return list(self.__trick)

	def get_prev_trick(self):
		return list(self.__previous_trick) if self.__previous_trick is not None else None

	# Places card in the trick in the position of the specified player. Returns the resulting trick.
	def set_trick(self, player, card):
		self.__trick[player-1] = card
		return self.__trick

	# Returns whether the specified player is able to exchange the trump card for its trump jack.
	def can_exchange(self, player):

		# Depending on whether this state is signed or not, we look either through
		# the perspective of the full card deck, or the perspective of a single player
		perspective = self.get_perspective()

		# If game is in phase 1 and player has trump jack
		return (self.get_stock_size() > 0) and (perspective[self.get_trump_jack_index()] == "P" + str(player) + "H")

	# Returns a list of the cards in the hand of the player that is specified.
	def get_player_hand(self, player):
		search_term = "P1H" if player == 1 else "P2H"
		search_array = self.get_perspective()
		return [i for i, x in enumerate(search_array) if x == search_term]

	# Returns the suit of the trump card.
	def get_trump_suit(self):
		return self.__trump_suit

	# Swaps places of the trump card with the trump Jack.
	def exchange_trump(self, trump_jack_index):
		trump_card_index = self.__stock[0]
		self.__card_state[trump_card_index] = self.__p1_perspective[trump_card_index] = self.__p2_perspective[trump_card_index] = self.__card_state[trump_jack_index]
		self.__card_state[trump_jack_index] = self.__p1_perspective[trump_jack_index] = self.__p2_perspective[trump_jack_index] = "S"
		self.__stock[0] = trump_jack_index

		# This is done to help the visual part differentiate between
		# Trump Jack Exchanges and regular moves. Shouldn't affect anything.
		self.__previous_trick = [None, None]

	# Returns the index of the Jack of the trump suit.
	def get_trump_jack_index(self):
		#The Aces of different suits are always 5 apart from another Ace
		trump_ace_index = self.__SUITS.index(self.__trump_suit) * 5

		#The Jack of a suit is always 4 cards removed from the Ace of the same suit
		trump_jack_index = trump_ace_index + 4

		return trump_jack_index

	# Returns index of trump card in stock if still in phase 1, otherwise None
	def get_trump_card_index(self):
		if self.get_stock_size() > 0:
			return self.__stock[0]
		return None

	# Returns a list of possible marriages for the specified player.
	def get_possible_mariages(self, player):
		possible_mariages = []
		player_hand = self.get_player_hand(player)
		#TODO: quite bulky, maybe change into a more elegant solution or at the very least comment
		if 2 in player_hand and 3 in player_hand:
			possible_mariages.append((2, 3))
			possible_mariages.append((3, 2))
		if 7 in player_hand and 8 in player_hand:
			possible_mariages.append((7, 8))
			possible_mariages.append((8, 7))
		if 12 in player_hand and 13 in player_hand:
			possible_mariages.append((12, 13))
			possible_mariages.append((13, 12))
		if 17 in player_hand and 18 in player_hand:
			possible_mariages.append((17, 18))
			possible_mariages.append((18, 17))

		return possible_mariages

	# Takes the top card of the stock and places it in the specified player's hand.
	def draw_card(self, player):
		if self.get_stock_size() == 0:
			raise RuntimeError('Stack is empty.')
		card = self.__stock.pop()
		if player == 1:
			self.__card_state[card] = self.__p1_perspective[card] = "P1H"
		else:
			self.__card_state[card] = self.__p2_perspective[card] = "P2H"

	# Puts the cards in the trick in the specified winner's pile of won cards. After this operation the trick is emptied.
	# Player perspectives are also updated
	def put_trick_away(self, winner):
		self.__card_state[self.__trick[0]] = self.__card_state[self.__trick[1]] = self.__p1_perspective[self.__trick[0]] = self.__p1_perspective[self.__trick[1]] = self.__p2_perspective[self.__trick[0]] = self.__p2_perspective[self.__trick[1]] = "P1W" if winner == 1 else "P2W"

		# Don't need to make a deep copy in this instance, tested.
		self.__previous_trick = self.__trick;
		self.__trick = [None, None]

	def add_to_perspective(self, player, index, card_state):
		"""
		Changes the specified player's perspective of the card at the given index to the given card state

		:param player: An integer signifying the player id
		:param index: An integer signifying the index of a card
		:param card_state: A string signifying the state of the card
		"""

		if player == 1:
			self.__p1_perspective[index] = card_state
		else:
			self.__p2_perspective[index] = card_state

	#Look into overloading this function as well
	# Generates a new deck based on a seed. If no seed is given, a random seed in generated.
	@staticmethod
	def generate(id=None):

		rng = random.Random(id)
		shuffled_cards = list(range(20))
		rng.shuffle(shuffled_cards)

		card_state = [0]*20
		p1_perspective = ["U"]*20
		p2_perspective = ["U"]*20
		stock = [] # Can be thought of as a stack data structure.

		# First card of stock is trump card, face up known by both players
		p1_perspective[shuffled_cards[0]] = p2_perspective[shuffled_cards[0]] = "S"

		# Three separate for loops assign a state to the cards in the
		# shuffled deck depending on their position. The indices of the
		# stock cards are pushed onto the stock stack to save their order.
		# Perspectives are also generated.
		for i in range(10):
			card_state[shuffled_cards[i]] = "S"
			stock.append(shuffled_cards[i])

		for i in range(10, 15):
			card_state[shuffled_cards[i]] = "P1H"
			p1_perspective[shuffled_cards[i]] = "P1H"

		for i in range(15, 20):
			card_state[shuffled_cards[i]] = "P2H"
			p2_perspective[shuffled_cards[i]] = "P2H"

		return Deck(card_state, stock, p1_perspective, p2_perspective)

	def make_assumption(self, seed=None):
		"""
		Identifies all unknown cards from the perspective of
		the relevant player, and makes guesses for their states.

		:param seed: Optional random number generator seed.
		:return: A deck object with the card_state array changed
		to represent a random guess of the states of the unknown cards.
		"""
		if seed is None:
			seed = random.randint(0, 100000)

		rng = random.Random(seed)

		perspective = self.get_perspective()

		trump_index = perspective.index("S")

		unknowns = [index for index, card in enumerate(perspective) if card == "U"]

		rng.shuffle(unknowns)

		other_player_term = "P2H" if self.__signature == 1 else "P1H"

		other_player_unknowns = 5 - perspective.count(other_player_term)

		for i in range(other_player_unknowns):
			perspective[unknowns.pop()] = other_player_term

		stock = [trump_index] + unknowns

		for i in range(len(unknowns)):
			perspective[unknowns.pop()] = "S"

		deck = Deck(perspective, stock, list(self.__p1_perspective), list(self.__p2_perspective))

		deck.__trick = list(self.__trick)
		deck.__previous_trick = list(self.__previous_trick) if self.__previous_trick is not None else None

		deck.__signature = None

		return deck

	def clone(self, signature):
		deck = Deck(list(self.__card_state), list(self.__stock), list(self.__p1_perspective), list(self.__p2_perspective), self.__trump_suit)

		deck.__signature = signature if self.__signature is None else self.__signature
		deck.__trick = list(self.__trick)
		deck.__previous_trick = list(self.__previous_trick) if self.__previous_trick is not None else None

		return deck

	def get_perspective(self, player=None):
		if self.__signature is None:
			if player is None:
				return self.__card_state
			return list(self.__p1_perspective) if player == 1 else list(self.__p2_perspective)
		return list(self.__p1_perspective) if self.__signature == 1 else list(self.__p2_perspective)

	def get_signature(self):
		return self.__signature

	def convert_to_json(self):
		return {"card_state":self.__card_state, "p1_perspective":self.__p1_perspective, "p2_perspective":self.__p2_perspective, "trick":self.__trick, "previous_trick":self.__previous_trick, "stock":self.__stock, "trump_suit":self.__trump_suit, "signature":self.__signature}

	@staticmethod
	def load_from_json(dict):
		deck = Deck(dict['card_state'], dict['stock'], dict['p1_perspective'], dict['p2_perspective'])
		deck.__signature = dict['signature']
		deck.__trick = dict['trick']
		deck.__previous_trick = dict['previous_trick']

		return deck

	def __eq__(self, o):
		return self.__card_state == o.__card_state and self.__p1_perspective == o.__p1_perspective and self.__p2_perspective == o.__p2_perspective and self.__trick == o.__trick and self.__stock == o.__stock and self.__trump_suit == o.__trump_suit and self.__signature == o.__signature

	def __ne__(self, o):
		return not (self.__card_state == o.__card_state and self.__p1_perspective == o.__p1_perspective and self.__p2_perspective == o.__p2_perspective and self.__trick == o.__trick and self.__stock == o.__stock and self.__trump_suit == o.__trump_suit and self.__signature == o.__signature)
