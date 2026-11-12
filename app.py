from flask import Flask, render_template, request, redirect, url_for, session, flash, render_template_string
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "woi-secret-key-change-this-123"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- DATABASE ---
def get_db():
    conn = sqlite3.connect('woi.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, location TEXT, photo TEXT, password TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, project TEXT, amount REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS book_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, book TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- PUBLIC PAGES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/transparency')
def transparency():
    conn = get_db()
    donations = conn.execute('SELECT * FROM donations ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('transparency.html', donations=donations)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        location = request.form.get('location')
        password = request.form.get('password')
        photo = request.files.get('photo')
        photo_name = None
        if photo and photo.filename:
            photo_name = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_name))
        conn = get_db()
        conn.execute('INSERT INTO members (name, phone, location, photo, password) VALUES (?,?,?,?,?)',
                     (name, phone, location, photo_name, generate_password_hash(password)))
        conn.commit()
        conn.close()
        flash('Registered successfully! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        conn = get_db()
        user = conn.execute('SELECT * FROM members WHERE phone=?', (phone,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['member_id'] = user['id']
            session['member_name'] = user['name']
            return redirect(url_for('index'))
        flash('Wrong phone or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/donate', methods=['POST'])
def donate():
    name = request.form.get('name')
    project = request.form.get('project')
    amount = request.form.get('amount')
    conn = get_db()
    conn.execute('INSERT INTO donations (name, project, amount) VALUES (?,?,?)', (name, project, amount))
    conn.commit()
    conn.close()
    flash('Thank you for your donation!')
    return redirect(url_for('transparency'))

@app.route('/order-book', methods=['POST'])
def order_book():
    name = request.form.get('name')
    phone = request.form.get('phone')
    book = request.form.get('book')
    conn = get_db()
    conn.execute('INSERT INTO book_orders (name, phone, book) VALUES (?,?,?)', (name, phone, book))
    conn.commit()
    conn.close()
    flash('Book order received!')
    return redirect(url_for('index'))

# --- ADMIN - BUILT-IN, NO TEMPLATE NEEDED ---
ADMIN_USER = "admin"
ADMIN_PASS = "woi2026"

ADMIN_LOGIN_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WOI Admin Login</title>
<style>body{font-family:Arial;background:#f5f0e8;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.box{background:white;padding:30px;border-radius:12px;width:90%;max-width:360px;box-shadow:0 4px 20px rgba(0,0,0,.1);text-align:center}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:8px;box-sizing:border-box}
button{width:100%;padding:12px;background:#7a1f3d;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer}
.error{color:red}</style></head>
<body><div class="box"><h2>WOI Admin Login</h2>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="POST"><input name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button>Login</button></form>
<p><a href="/">Back to site</a></p></div></body></html>
"""

ADMIN_DASH_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WOI Admin Dashboard</title>
<style>body{font-family:Arial;background:#f5f0e8;margin:0;padding:15px}
h1{color:#7a1f3d}.card{background:white;padding:15px;border-radius:10px;margin-bottom:15px;overflow-x:auto}
table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #eee;text-align:left;font-size:14px}
a.btn{background:#7a1f3d;color:white;padding:8px 14px;border-radius:6px;text-decoration:none}</style></head>
<body><h1>WOI Admin Dashboard</h1><p>Logged in as admin | <a class="btn" href="/admin/logout">Logout</a> <a class="btn" href="/">View Site</a></p>
<div class="card"><h2>Members ({{ members|length }})</h2>
<table><tr><th>Name</th><th>Phone</th><th>Location</th><th>Date</th></tr>
{% for m in members %}<tr><td>{{ m['name'] }}</td><td>{{ m['phone'] }}</td><td>{{ m['location'] }}</td><td>{{ m['created_at'] }}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Donations ({{ donations|length }})</h2>
<table><tr><th>Name</th><th>Project</th><th>Amount</th><th>Date</th></tr>
{% for d in donations %}<tr><td>{{ d['name'] }}</td><td>{{ d['project'] }}</td><td>{{ d['amount'] }}</td><td>{{ d['created_at'] }}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Book Orders ({{ orders|length }})</h2>
<table><tr><th>Name</th><th>Phone</th><th>Book</th><th>Date</th></tr>
{% for o in orders %}<tr><td>{{ o['name'] }}</td><td>{{ o['phone'] }}</td><td>{{ o['book'] }}</td><td>{{ o['created_at'] }}</td></tr>{% endfor %}</table></div>
</body></html>
"""

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = "Wrong username or password"
    return render_template_string(ADMIN_LOGIN_HTML, error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    members = conn.execute('SELECT * FROM members ORDER BY id DESC').fetchall()
    donations = conn.execute('SELECT * FROM donations ORDER BY id DESC').fetchall()
    orders = conn.execute('SELECT * FROM book_orders ORDER BY id DESC').fetchall()
    conn.close()
    return render_template_string(ADMIN_DASH_HTML, members=members, donations=donations, orders=orders)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
