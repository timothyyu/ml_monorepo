#!flask/bin/python

import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from api import State, util
from argparse import ArgumentParser
import random
import json


from flask import Flask, render_template, request, redirect, Response
import random, json


app = Flask(__name__, template_folder='.')
app.config.update(
	PROPAGATE_EXCEPTIONS = True
)

@app.route('/')
def output():
	# serve index template
	# return "Welcome to python flask!"
	return render_template("index_interactive.html")

@app.route('/generate', methods = ['GET'])
def generate():
	global state
	# Use 3 for marriage, 50 for exchange
	state = State.generate(id=options.seed, phase=options.phase)
	return state.convert_to_json() #[:-1] + ', "seed": ' + str(id) + '}')

@app.route('/next', methods = ['GET'])
def new():
	global state

	given_state = state.clone(signature=state.whose_turn()) if state.get_phase() == 1 else state.clone()

	state = state.next(player2.get_move(given_state))
	return state.convert_to_json()

@app.route('/sendmove', methods = ['POST'])
def send():
	global state
	data = request.get_json(force=True)
	move = (data[0], data[1])
	state = state.next(move)
	return state.convert_to_json()


@app.route('/getcurrent', methods = ['GET'])
def getcurrent():
	return state.convert_to_json()


@app.route('/receiver', methods = ['POST'])
def worker():
	# read json + reply
	data = request.get_json(force=True)
	print(data)
	result = ''

	for item in data:
		# loop over every row
		result += str(item['make']) + '\n'

	return result

if __name__ == '__main__':


	## Parse the command line options
	parser = ArgumentParser()

	parser.add_argument("-o", "--opponent",
						dest="player2",
						help="the bot to run as your opponent (default: rand)",
						default="rand")

	parser.add_argument("-s", "--seed",
						dest="seed",
						type=int,
						help="The seed for state generation. Same seed will always return the same state, useful for debugging.",
						default=None)

	parser.add_argument("-p", "--phase",
						dest="phase",
						type=int,
						choices=[1,2],
						help="The seed for state generation. Same seed will always return the same state, useful for debugging.",
						default=1)



	options = parser.parse_args()

	state = None
	player2 = util.load_player(options.player2)


	app.run(debug=True)
