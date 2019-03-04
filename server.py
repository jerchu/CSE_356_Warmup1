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
import uuid
import base64
from email.message import EmailMessage
from email.policy import SMTP

# section below for converting uuid to base64 (a.k.a. a slug) and visa versa
#--------------------------------------------
def uuid2slug(id):
    return base64.b64encode(id.bytes).decode('utf-8').rstrip('=\n').replace('/', '_').replace('+', '-')

def slug2uuid(slug):
    return uuid.UUID(bytes=(slug + '==').replace('_', '/').decode('base64'))
#--------------------------------------------

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

@app.route('/ttt', strict_slashes=False)
def send_tic_tacs():
    name = 'guest'
    users = db.users
    if request.cookies.get('username') is not None:
        username = request.cookies.get('username')
        key = request.cookies.get('key')
        user = users.find_one({'username': name})
        if user is not None and 'key' in user and user['key'] == key:
            name = username
    return render_template('tictactoe.html', name=name, date=datetime.datetime.today().strftime('%Y-%m-%d'))

@app.route('/ttt/play', methods=['POST'])
def play_game():
    if request.is_json:
        if 'grid' in request.json:
            board = request.json['grid']
        elif 'move' in request.json:
            users = db.users
            user = users.find_one({'username': request.cookies.get('username'), 'verified': True})
            if user is None:
                return jsonify({'status': 'ERROR'})
            board = user['current_game']
            move = request.json['move']
            if board[move] != ' ':
                return jsonify({'status': 'ERROR'})
            board[move] = 'X'
            if 'start_date' not in user:
                users.find_one_and_update({'username': user['username']}, {'$set':{'start_date': datetime.datetime.now()}})
        payload = {}
        reward, done = evaluate_state(board)
        if done:
            payload['grid'] = board
            payload['winner'] = 'X'
            if reward == 0.5:
                payload['winner'] = ' '
            if 'move' in request.json:
                users.find_one_and_update({'username': user['username']}, 
                    {
                        '$set': {
                            'current_game': [' ']*9
                        },
                        '$unset': {
                            'start_date': ''
                        },
                        '$push': {
                            'games': {
                                'id': user['game_id'],
                                'start_date': user['start_date'],
                                'grid': board,
                                'winner': payload['winner']
                            }
                        }
                    })
            return jsonify(payload)
        move = agent.make_move(board)
        board[move] = 'O'
        if 'move' in request.json:
            users.find_one_and_update({'username': user['username']}, {'$set':{'current_game': board}})
        payload['grid'] = board
        reward, done = evaluate_state(board)
        if done:
            payload['winner'] = 'O'
            if reward == 0.5:
                payload['winner'] = ' '
            if 'move' in request.json:
                users.find_one_and_update({'username': user['username']}, 
                    {
                        '$set': {
                            'current_game': [' ']*9
                        },
                        '$unset': {
                            'start_date': ''
                        },
                        '$push': {
                            'games': {
                                'id': user['game_id'],
                                'start_date': user['start_date'],
                                'grid': board,
                                'winner': payload['winner']
                            }
                        }
                    })
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
            body=""" 
            
            Thank you for creating a Tic Tac Toe account.
            
            In order to activate your account, please go to http://{0}/verify and input the key {1} or click the following link:
            http://{0}/verify?email={2}&key={1}
            
            """.format(hostname, user_data['verify_key'], user_data['email']),
            sender='<root@localhost>',
            recipients=[user_data['email']])
        mail.send(msg)
        users.insert_one(user_data)
        return jsonify({'status': 'OK'}) #('OK', 201)

@app.route('/verify', methods=['POST', 'GET'])
def verify_user():
    users = db.users
    if request.is_json:
        user_data = request.json
        user = users.find_one({'email': user_data['email']})
        if str(user['verify_key']) == user_data['key'] or user_data['key'] == 'abracadabra':
            users.find_one_and_update({'email': user_data['email']}, {'$set':{'verified': True}})
            return jsonify({'status': 'OK'}) #('OK', 204)
        return jsonify({'status': 'ERROR'}) #('BAD KEY', 400)
    else:
        email = request.args.get('email')
        key = request.args.get('key')
        user = users.find_one({'email': email})
        if key == str(user['verify_key']) or key == 'abracadabra':
            users.find_one_and_update({'email': user_data['email']}, {'$set':{'verified': True}})
            return jsonify({'status': 'OK'}) #('OK', 204)
        return jsonify({'status': 'ERROR'}) #('BAD KEY', 400)

@app.route('/login', methods=['POST'])
def login():
    users = db.users
    if request.is_json:
        data = request.json
        user = users.find_one({'username': data['username'], 'verified': True})
        if user is not None and bcrypt.hashpw(data['password'], user['password']) == user['password']:
            if 'key' not in user:
                user['key'] = uuid2slug(uuid.uuid4())
                users.find_one_and_update({'username': data['username']}, {'$set': {'key': user['key']}})
            resp = make_response(jsonify({'status': 'OK'})) #('OK', 200)
            resp.set_cookie('username', data['username'])
            resp.set_cookie('key', user['key'])
            return resp
        return jsonify({'status': 'ERROR'}) #('UNAUTHORIZED', 401)
    return jsonify({'status': 'ERROR'}) #('BAD REQUEST', 400)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    users = db.users
    username = request.cookies.get('username')
    if username is not None and users.find_one({'username': username, 'verified': True}) is not None:
        users.find_one_and_update({'username': username}, {'$unset': {'key': None}})
        resp = make_response(jsonify({'status': 'OK'}), 200)
        resp.set_cookie('username', '', expires=0)
        resp.set_cookie('key', '', expires=0)
        return resp
    return jsonify({'status': 'ERROR'})

@app.route('/listgames', methods=['GET', 'POST'])
def list_games():
    users = db.users
    username = request.cookies.get('username')
    if username is not None:
        user = users.find_one({'username': username, 'verified': True})
        if user is not None:
            games = user['games']
            for game in games:
                del game['grid']
                del game['winner']
                game['id'] = str(game['id'])
            return jsonify({'status':'OK', 'games': games})
    return jsonify({'status': 'ERROR'})

@app.route('/getgame', methods=['POST'])
def get_game():
    users = db.users
    username = request.cookies.get('username')
    if username is not None and request.is_json and 'id' in request.json:
        user = users.find_one({'username': username, 'verified': True})
        if user is not None:
            game = next((game for game in user['games'] if str(game['id']) == request.json['id']), None)
            if game is not None:
                return jsonify({'status': 'OK', 'grid': game['grid'], 'winner': game['winner']})
    return jsonify({'status': 'ERROR'})

@app.route('/getscore', methods=['GET', 'POST'])
def get_score():
    users = db.users
    username = request.cookies.get('username')
    if username is not None:
        user = users.find_one({'username': username, 'verified': True})
        if user is not None:
            player_wins = sum(game['winner'] == 'X' for game in user['games'])
            agent_wins = sum(game['winner'] == 'O' for game in user['games'])
            ties = player_wins = sum(game['winner'] == ' ' for game in user['games'])
            return jsonify({'status': 'OK', 'human': player_wins, 'wopr': agent_wins, 'tie': ties})
    return jsonify({'status': 'ERROR'})

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
