from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

# --- Switched to PyMySQL ---
import pymysql.cursors
from pymysql import Error # PyMySQL correctly exports Error at the top level
# ---------------------------

load_dotenv()

app = Flask(__name__)
CORS(app)

# NOTE: PyMySQL generally works well with 'localhost' but '127.0.0.1' is safer
db_config = {
    'host': os.getenv('DB_HOST', '127.0.0.1'), 
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Parvparmar@123'), 
    'database': os.getenv('DB_NAME', 'fifa')
}

import pymysql

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='root@123',
        database='fifa',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

# --- added helper to safely close cursor/connection ---
def close_db(cursor=None, connection=None):
    try:
        if cursor:
            cursor.close()
    except Exception:
        # ignore already closed / other close errors
        pass
    try:
        if connection:
            connection.close()
    except Exception:
        pass
# --- end helper ---

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
            close_db(cursor, connection)
            return jsonify({'success': False, 'message': 'Username exists'}), 400
        
        cursor.execute('INSERT INTO User (username, password) VALUES (%s, %s)', (username, password))
        connection.commit()
        user_id = cursor.lastrowid 
        
        # use safe closer
        close_db(cursor, connection)
        return jsonify({'success': True, 'userId': user_id, 'username': username}), 201
    except Error as e:
        close_db(cursor, connection)
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
    
    # Use PyMySQL DictCursor for dictionary results
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('SELECT user_id, username FROM User WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        
        close_db(cursor, connection)
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        return jsonify({'success': True, 'userId': user['user_id'], 'username': user['username']}), 200
    except Error as e:
        close_db(cursor, connection)
        return jsonify({'success': False, 'message': str(e)}), 500

# PLAYERS
@app.route('/api/players', methods=['GET'])
def get_players():
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    # Use PyMySQL DictCursor for dictionary results
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.item_id, i.ovr
            FROM Player p
            JOIN Item i ON p.player_id = i.player_id
            ORDER BY p.name
        ''')
        players = cursor.fetchall()
        close_db(cursor, connection)
        return jsonify(players), 200
    except:
        close_db(cursor, connection)
        return jsonify([]), 500

@app.route('/api/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.ovr
        FROM Player p
        JOIN Item i ON p.player_id = i.player_id
        WHERE p.player_id = %s
    """, (player_id,))
    player = cursor.fetchone()
    cursor.close()
    connection.close()
    return jsonify(player)


@app.route('/api/players', methods=['POST'])
def add_player():
    name = request.form.get('name')
    nationality = request.form.get('nationality')
    position = request.form.get('position')
    ovr = request.form.get('ovr')
    image = request.files.get('image')

    if not image:
        return jsonify({'success': False, 'message': 'No image uploaded'}), 400

    # Save image to static/sql-fifa-images/
    upload_folder = os.path.join('static', 'sql-fifa-images')
    os.makedirs(upload_folder, exist_ok=True)
    filename = image.filename
    save_path = os.path.join(upload_folder, filename)
    image.save(save_path)

    # Store relative path in DB (for displaying later)
    imagedir = f'sql-fifa-images/{filename}'

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = connection.cursor()
    try:
        cursor.callproc('addplayer', (name, nationality, position, imagedir, ovr))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True, 'imagedir': imagedir}), 201
    except Exception as e:
        connection.rollback()
        # use safe closer
        close_db(cursor, connection)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/players/<int:player_id>', methods=['PUT'])
def update_player(player_id):
    name = request.form.get('name')
    nationality = request.form.get('nationality')
    position = request.form.get('position')
    ovr = request.form.get('ovr')
    image = request.files.get('image')

    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    try:
        # Optional image upload
        if image:
            upload_folder = os.path.join('static', 'sql-fifa-images')
            os.makedirs(upload_folder, exist_ok=True)
            filename = image.filename
            image.save(os.path.join(upload_folder, filename))
            imagedir = f'sql-fifa-images/{filename}'
        else:
            imagedir = request.form.get('imagedir', '')

        cursor.callproc('UpdatePlayer', (player_id, name, nationality, position, imagedir, ovr))
        connection.commit()
        return jsonify({'success': True}), 200

    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        # ensure safe close
        close_db(cursor, connection)

# @app.route('/api/players/<int:player_id>', methods=['GET'])
# def get_player(player_id):
#     connection = get_db_connection()
#     if not connection:
#         return jsonify({'success': False, 'message': 'Database connection failed'}), 500

#     cursor = connection.cursor()
#     try:
#         cursor.execute("""
#             SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.ovr
#             FROM Player p
#             JOIN Item i ON p.player_id = i.player_id
#             WHERE p.player_id = %s
#         """, (player_id,))
#         row = cursor.fetchone()
#         # close via helper
#         close_db(cursor, connection)

#         if not row:
#             return jsonify({'success': False, 'message': 'Player not found'}), 404

#         player = {
#             'player_id': row[0],
#             'name': row[1],
#             'nationality': row[2],
#             'position': row[3],
#             'imagedir': row[4],
#             'ovr': row[5]
#         }

#         return jsonify(player), 200
#     except Exception as e:
#         close_db(cursor, connection)
#         return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/players/<int:player_id>', methods=['DELETE'])
def delete_player(player_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False}), 500
    
    cursor = connection.cursor()
    try:
        cursor.callproc('DeletePlayer', (player_id,))
        connection.commit()
        close_db(cursor, connection)
        return jsonify({'success': True}), 200
    except Exception as e:
        connection.rollback()
        close_db(cursor, connection)
        return jsonify({'success': False, 'message': str(e)}), 500

# TEAMS
@app.route('/api/teams', methods=['GET'])
def get_teams():
    user_id = request.args.get('userId', 1)
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    # Use PyMySQL DictCursor for dictionary results
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('SELECT * FROM Team WHERE user_id = %s ORDER BY team_name', (user_id,))
        teams = cursor.fetchall()
        close_db(cursor, connection)
        return jsonify(teams), 200
    except:
        close_db(cursor, connection)
        return jsonify([]), 500

@app.route('/api/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM Team WHERE team_id = %s", (team_id,))
    team = cursor.fetchone()
    close_db(cursor, connection)

    if team:
        return jsonify(team)
    else:
        return jsonify({'success': False, 'message': 'Team not found'}), 404


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
        close_db(cursor, connection)
        return jsonify({'success': True, 'teamId': team_id}), 201
    except:
        close_db(cursor, connection)
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
        close_db(cursor, connection)
        return jsonify({'success': True}), 200
    except:
        close_db(cursor, connection)
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
        close_db(cursor, connection)
        return jsonify({'success': True}), 200
    except:
        close_db(cursor, connection)
        return jsonify({'success': False}), 500

@app.route('/api/teams/<int:team_id>/players', methods=['GET'])
def get_team_players(team_id):
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    # Use PyMySQL DictCursor for dictionary results
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT p.player_id, p.name, p.nationality, p.position, p.imagedir, i.item_id, i.ovr
            FROM Player p
            JOIN Item i ON p.player_id = i.player_id
            JOIN Club c ON i.item_id = c.item_id
            WHERE c.team_id = %s
        ''', (team_id,))
        players = cursor.fetchall()
        close_db(cursor, connection)
        return jsonify(players), 200
    except:
        close_db(cursor, connection)
        return jsonify([]), 500

@app.route('/api/teams/<int:team_id>/items', methods=['POST'])
def add_item_to_team(team_id):
    data = request.get_json()
    item_id = data.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'message': 'item_id is required'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'DB connection failed'}), 500

    cursor = connection.cursor()
    try:
        cursor.execute('INSERT INTO club (item_id, team_id) VALUES (%s, %s)', (item_id, team_id))
        connection.commit()
        close_db(cursor, connection)
        return jsonify({'success': True}), 201
    except Exception as e:
        connection.rollback()
        close_db(cursor, connection)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                i.item_id,
                i.ovr,
                p.player_id,
                p.name,
                p.position,
                p.nationality,
                p.imagedir
            FROM Item i
            JOIN Player p ON i.player_id = p.player_id
            ORDER BY p.name
        """)
        items = cursor.fetchall()
        return jsonify(items)
    except Exception as e:
        print("❌ DB Error:", e)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # safe close
        close_db(cursor, connection)

# MATCHES
@app.route('/api/matches', methods=['GET'])
def get_matches():
    connection = get_db_connection()
    if not connection:
        return jsonify([]), 500
    
    # Use PyMySQL DictCursor for dictionary results
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT m.match_id, m.home_team_id, m.away_team_id,
                   t1.team_name as home_team_name, t2.team_name as away_team_name
            FROM Matches m
            JOIN Team t1 ON m.home_team_id = t1.team_id
            JOIN Team t2 ON m.away_team_id = t2.team_id
        ''')
        matches = cursor.fetchall()
        close_db(cursor, connection)
        return jsonify(matches), 200
    except:
        close_db(cursor, connection)
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
        close_db(cursor, connection)
        return jsonify({'success': True, 'matchId': match_id}), 201
    except:
        close_db(cursor, connection)
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
        close_db(cursor, connection)
        return jsonify({'success': True}), 200
    except:
        close_db(cursor, connection)
        return jsonify({'success': False}), 500
    
@app.route('/api/matches/<int:match_id>/teams', methods=['GET'])
def get_match_teams(match_id):
    connection = get_db_connection()
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    try:
        # First get the team IDs for that match
        cursor.execute("""
            SELECT home_team_id, away_team_id
            FROM Matches
            WHERE match_id = %s
        """, (match_id,))
        match = cursor.fetchone()

        if not match:
            return jsonify({'success': False, 'message': 'Match not found'}), 404

        # Now get players from the TeamPlayers view
        cursor.execute("""
            SELECT * FROM TeamPlayers
            WHERE team_id IN (%s, %s)
            ORDER BY team_id, ovr DESC
        """, (match['home_team_id'], match['away_team_id']))

        players = cursor.fetchall()
        close_db(cursor, connection)
        return jsonify({
            'success': True,
            'home_team_id': match['home_team_id'],
            'away_team_id': match['away_team_id'],
            'players': players
        }), 200
    except Exception as e:
        connection.rollback()
        close_db(cursor, connection)
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print('\n' + '='*50)
    print('⚽ FIFA Database Server')
    print('='*50)
    print('✓ Server running on http://localhost:5050')
    print('✓ API Base: http://localhost:5050/api')
    print('='*50 + '\n')
    app.run(debug=True, host='127.0.0.1', port=5050)