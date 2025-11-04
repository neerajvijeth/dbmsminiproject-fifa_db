from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fifa')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

# AUTH
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database error'}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT user_id FROM User WHERE username = %s', (username,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username exists'}), 400
        
        cursor.execute('INSERT INTO User (username, password) VALUES (%s, %s)', (username, password))
        connection.commit()
        user_id = cursor.lastrowid
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'userId': user_id, 'username': username}), 201
    except Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database error'}), 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT user_id, username FROM User WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        return jsonify({'success': True, 'userId': user['user_id'], 'username': user['username']}), 200
    except Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# PLAYERS
@app.route('/api/players', methods=['GET'])
def get_players():
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.item_id, i.ovr
            FROM Player p
            JOIN Item i ON p.player_id = i.player_id
            ORDER BY p.name
        ''')
        players = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(players), 200
    except:
        return jsonify([]), 500

@app.route('/api/players', methods=['POST'])
def add_player():
    data = request.json
    name = data.get('name')
    nationality = data.get('nationality')
    position = data.get('position')
    ovr = data.get('ovr')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO Player (name, nationality, position, imagedir) VALUES (%s, %s, %s, %s)',
                      (name, nationality, position, ''))
        player_id = cursor.lastrowid
        cursor.execute('INSERT INTO Item (ovr, player_id) VALUES (%s, %s)', (ovr, player_id))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    data = request.json
    name = data.get('name')
    nationality = data.get('nationality')
    position = data.get('position')
    ovr = data.get('ovr')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('UPDATE Player SET name = %s, nationality = %s, position = %s WHERE player_id = %s',
                      (name, nationality, position, player_id))
        cursor.execute('UPDATE Item SET ovr = %s WHERE player_id = %s', (ovr, player_id))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'success': False}), 500

@app.route('/api/players/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('DELETE FROM Item WHERE player_id = %s', (player_id,))
        cursor.execute('DELETE FROM Player WHERE player_id = %s', (player_id,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'success': False}), 500

# TEAMS
@app.route('/api/teams', methods=['GET'])
def get_teams():
    user_id = request.args.get('userId', 1)
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM Team WHERE user_id = %s ORDER BY team_name', (user_id,))
        teams = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(teams), 200
    except:
        return jsonify([]), 500

@app.route('/api/teams', methods=['POST'])
def add_team():
    data = request.json
    team_name = data.get('team_name')
    formation = data.get('formation')
    user_id = data.get('user_id', 1)
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO Team (team_name, formation, user_id, avg_ovr) VALUES (%s, %s, %s, 0)',
                      (team_name, formation, user_id))
        connection.commit()
        team_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'teamId': team_id}), 201
    except:
        return jsonify({'success': False}), 500

@app.route('/api/teams/<int:team_id>', methods=['PUT'])
def update_team(team_id):
    data = request.json
    team_name = data.get('team_name')
    formation = data.get('formation')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('UPDATE Team SET team_name = %s, formation = %s WHERE team_id = %s',
                      (team_name, formation, team_id))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'success': False}), 500

@app.route('/api/teams/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('DELETE FROM Team WHERE team_id = %s', (team_id,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'success': False}), 500

@app.route('/api/teams/<int:team_id>/players', methods=['GET'])
def get_team_players(team_id):
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.item_id, i.ovr
            FROM Player p
            JOIN Item i ON p.player_id = i.player_id
            JOIN Club c ON i.item_id = c.item_id
            WHERE c.team_id = %s
        ''', (team_id,))
        players = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(players), 200
    except:
        return jsonify([]), 500

# MATCHES
@app.route('/api/matches', methods=['GET'])
def get_matches():
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('''
            SELECT m.match_id, m.home_team_id, m.away_team_id,
                   t1.team_name as home_team_name, t2.team_name as away_team_name
            FROM Matches m
            JOIN Team t1 ON m.home_team_id = t1.team_id
            JOIN Team t2 ON m.away_team_id = t2.team_id
        ''')
        matches = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(matches), 200
    except:
        return jsonify([]), 500

@app.route('/api/matches', methods=['POST'])
def add_match():
    data = request.json
    home_team_id = data.get('home_team_id')
    away_team_id = data.get('away_team_id')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO Matches (home_team_id, away_team_id) VALUES (%s, %s)',
                      (home_team_id, away_team_id))
        connection.commit()
        match_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'matchId': match_id}), 201
    except:
        return jsonify({'success': False}), 500

@app.route('/api/matches/<int:match_id>', methods=['DELETE'])
def delete_match(match_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.execute('DELETE FROM Matches WHERE match_id = %s', (match_id,))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True}), 200
    except:
        return jsonify({'success': False}), 500

if __name__ == '__main__':
    print('\n' + '='*50)
    print('⚽ FIFA Database Server')
    print('='*50)
    print('✓ Server running on http://localhost:5050')
    print('✓ API Base: http://localhost:5050/api')
    print('='*50 + '\n')
    app.run(debug=True, host='127.0.0.1', port=5050)
