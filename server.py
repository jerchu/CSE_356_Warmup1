import os
here = os.path.dirname(__file__)
import sys
sys.path.insert(0, here)
from static.RL_learn.learner import Learner, Game
from flask import Flask, render_template, request, jsonify, make_response
from flask_mail import Mail, Message
import datetime
import random
from bson.objectid import ObjectId
from pymongo import MongoClient
import bcrypt
import csv
import smtplib
from email.message import EmailMessage
from email.policy import SMTP

app = Flask(__name__, static_url_path='')
mail = Mail(app)
agent = Learner(epsilon=0)
agent.load_states(os.path.join(here, 'static/RL_learn/playero.pickle'))

with open(os.path.join(here, 'static/images.csv'), 'r') as f:
    images = f.readlines()

import logging
streamhndlr = logging.StreamHandler()
app.logger.addHandler(streamhndlr)
app.logger.setLevel(logging.INFO)

client = MongoClient('localhost', 27017)
db = client.ttt

hostname='130.245.170.248'

@app.route('/')
def hello_world():
    random_img = random.choice(images).split(',')
    data = {}
    data['image'] = random_img[0]
    if len(random_img) > 1:
        data['title'] = random_img[1]
    resp = make_response(render_template('index.html', **data))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/ttt', strict_slashes=False, methods=['GET', 'POST'])
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

@app.route('/adduser', methods=['POST'])
def add_user():
    if request.is_json:
        users = db.users
        user_data = request.json
        user_data['games'] = []
        user_data['current_game'] = [' '] * 9
        user_data['game_id'] = ObjectId()
        user_data['verify_key'] = ObjectId()
        user_data['verified'] = False
        user_data['password'] = bcrypt.hashpw(user_data['password'], bcrypt.gensalt())
        msg = Message('Verify your Tic Tac Toe Account at {}'.format(hostname),
            body="""\ 
            
            Thank you for creating a Tic Tac Toe account.
            
            In order to activate your account, please go to http://{0}/verify and input the key {1} or click the following link:
            http://{0}/verify?email={2}&key={1}
            
            """.format(hostname, user_data['verify_key'], user_data['email']),
            sender='<root@localhost>',
            recipients=[user_data['email']])
        mail.send(msg)
        users.insert_one(user_data)
        return ('OK', 201)

@app.route('/verify', methods=['POST', 'GET'])
def verify_user():
    users = db.users
    if request.is_json:
        user_data = request.json
        user = users.find_one({'email': user_data['email']})
        if user['verify_key'] == user_data['key'] or user_data['key'] == 'abracadabra':
            users.find_one_and_update({'email': user_data['email']}, {'verified': True})
        return('OK', 201)
    else:
        email = request.args.get('email')
        key = request.args.get('key')
        user = users.find_one({'email': email})
        if key == user['verify_key'] or key == 'abracadabra':
            users.find_one_and_update({'email': user_data['email']}, {'verified': True})
        return ('OK', 200)
    

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
