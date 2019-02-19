from unittest import TestCase
from api import Deck

class TestDeck(TestCase):

    def test_generate(self):
        d = Deck.generate(0)

        stock = d.get_card_states().count("S")
        self.assertEqual(stock,10,"The value should be 10")

        player1 = d.get_card_states().count("P1H")
        self.assertEqual(player1, 5,"The value should be 5")

        player2 = d.get_card_states().count("P2H")
        self.assertEqual(player2, 5,"The value should be 5")

    def test_trump_exchange(self):

		d = Deck.generate(0)
		print d.get_trump_suit()
		print d.get_card_states()
		if d.can_exchange(1):
			print "1 exchanged"
			d.exchange_trump()
			print d.get_card_states()

		elif d.can_exchange(2):
			print "2 exchanged"
			d.exchange_trump()
			print d.get_card_states()
		else:
			print "no one exchanged"