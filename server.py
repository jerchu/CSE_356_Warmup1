import os
here = os.path.dirname(__file__)
import sys
sys.path.insert(0, here)
from static.RL_learn.learner import Learner, Game
from flask import Flask, render_template, request, jsonify
import datetime
app = Flask(__name__, static_url_path='')
agent = Learner(epsilon=0)
agent.load_states(os.path.join(here, 'static/RL_learn/playero.pickle'))
import logging
streamhndlr = logging.StreamHandler()
app.logger.addHandler(streamhndlr)
app.logger.setLevel(logging.INFO)

@app.route('/')
def hello_world():
    return 'Hello world'

@app.route('/ttt', methods=['GET', 'POST'])
def send_tic_tacs():
	if request.method == 'POST':
		name = request.form['name']
		return render_template('tictactoe.html', name=name, date=datetime.datetime.today().strftime('%Y-%m-%d'))
	return render_template('tictactoe.html')

@app.route('/ttt/play', methods=['POST'])
def play_game():
	if request.is_json and 'grid' in request.json:
		board = request.json['grid']
		payload = {}
		reward, done = evaluate_state(board)
		if done:
			payload['grid'] = board
			payload['winner'] = 'X'
			if reward == 0.5:
				payload['winner'] = ' '
			return jsonify(payload)
		move = agent.make_move(board)
		board[move] = 'O'
		payload['grid'] = board
		reward, done = evaluate_state(board)
		if done:
			payload['winner'] = 'O'
			if reward == 0.5:
				payload['winner'] = ' '
		return jsonify(payload)
	return ('BAD REQUEST', 400)

def evaluate_state(board):
	for i in range(3):
		if board[i*3] != ' ': 
			if board[i*3] == board[i*3+1] and board[i*3] == board[i*3+2]:
				return 1, True
		if board[i] != ' ':
			if board[i] == board[i+3] and board[i] == board[i+6]:
				return 1, True
	if board[4] != ' ':
		if board[0] == board[4] and board[0] == board[8]:
			return 1, True
		if board[2] == board[4] and board[2] == board[6]:
			return 1, True
	if len([tile for tile, t in enumerate(board) if t == ' ']) < 1:
		return 0.5, True
	return 0.0, False

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=80)
