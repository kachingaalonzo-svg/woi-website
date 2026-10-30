from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'woi-secret-key-1997' # important for login session

DB = 'woi.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, email TEXT, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS donations 
                 (id INTEGER PRIMARY KEY, name TEXT, project TEXT, amount INTEGER, method TEXT, reference TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS books 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, book TEXT, method TEXT, ref TEXT)''')
    conn.commit(); conn.close()

init_db()

@app.route('/')
def home(): return render_template('index.html')

@app.route('/register')
def register_page(): return render_template('register.html')

@app.route('/history.html')
def history(): return render_template('history.html')

@app.route('/transparency')
def transparency(): return render_template('transparency.html')

@app.route('/member/login')
def login_page(): return render_template('member/login.html')

@app.route('/member/dashboard')
def dashboard():
    if 'user_phone' not in session:
        return redirect('/member/login')
    return render_template('member/dashboard.html', name=session.get('user_name'))

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name = data.get('name'); phone = data.get('phone'); email = data.get('email',''); password = data.get('password')
    if not name or not phone or not password:
        return jsonify(msg='Fill all fields'), 400
    hashed = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute('INSERT INTO users (name, phone, email, password) VALUES (?,?,?,?)', (name, phone.strip(), email, hashed))
        conn.commit(); conn.close()
        return jsonify(msg='Account created! Redirecting to login...')
    except sqlite3.IntegrityError:
        return jsonify(msg='Phone already registered, please login'), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    phone = data.get('phone','').strip(); password = data.get('password','')
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT name, password FROM users WHERE phone=?', (phone,))
    row = c.fetchone(); conn.close()
    if not row:
        return jsonify(msg='User not found. Please register first'), 404
    name, hashed = row
    if not check_password_hash(hashed, password):
        return jsonify(msg='Wrong password'), 401
    session['user_phone'] = phone
    session['user_name'] = name
    return jsonify(msg=f'Welcome {name}!')

@app.route('/donate', methods=['POST'])
def donate():
    d = request.get_json()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT INTO donations (name, project, amount, method, reference) VALUES (?,?,?,?,?)',
              (d.get('name'), d.get('project'), d.get('amount'), d.get('method'), d.get('reference')))
    conn.commit(); conn.close()
    return jsonify(msg='Donation saved! See Transparency page')

@app.route('/order-book', methods=['POST'])
def order_book():
    d = request.get_json()
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('INSERT INTO books (name, phone, book, method, ref) VALUES (?,?,?,?,?)',
              (d.get('name'), d.get('phone'), d.get('book'), d.get('method'), d.get('ref')))
    conn.commit(); conn.close()
    return jsonify(msg='Book order saved! We will contact you')

@app.route('/api/donations')
def api_donations():
    conn = sqlite3.connect(DB); c = conn.cursor()
    c.execute('SELECT name, project, amount, method FROM donations ORDER BY id DESC LIMIT 50')
    rows = [{'name':r[0],'project':r[1],'amount':r[2],'method':r[3]} for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == '__main__':
    app.run(debug=True)
