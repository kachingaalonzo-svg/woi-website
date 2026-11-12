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

# --- ADMIN - MODERN, BUILT-IN ---
ADMIN_USER = "admin"
ADMIN_PASS = "woi2026"

ADMIN_LOGIN_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WOI Admin • Login</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;font-family:'Inter',Arial,sans-serif}
body{margin:0;min-height:100vh;background:linear-gradient(135deg,#2b0a1a 0%,#7a1f3d 45%,#c98a2e 100%);display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:rgba(255,255,255,.98);width:100%;max-width:400px;border-radius:20px;padding:32px 28px;box-shadow:0 20px 50px rgba(0,0,0,.35);text-align:center}
.logo{width:64px;height:64px;background:#7a1f3d;color:white;border-radius:18px;display:flex;align-items:center;justify-content:center;font-size:30px;margin:0 auto 14px}
h2{margin:0;font-size:24px;color:#1a1a1a}p.sub{color:#777;margin:6px 0 20px;font-size:14px}
input{width:100%;padding:14px 16px;margin:8px 0;border:1.5px solid #eee;border-radius:12px;font-size:15px;outline:none;background:#fafafa}
input:focus{border-color:#7a1f3d;background:white}
button{width:100%;padding:14px;background:#7a1f3d;color:white;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;margin-top:10px}
button:hover{background:#5e1730}.error{background:#ffe8e8;color:#c00;padding:10px;border-radius:10px;font-size:14px}
.back{display:block;margin-top:16px;color:#888;font-size:13px;text-decoration:none}
</style></head>
<body><div class="card"><div class="logo">✦</div><h2>Welcome Back</h2><p class="sub">Women of Integrity • Admin Portal</p>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST"><input name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button>Sign In →</button></form>
<a class="back" href="/">← Back to website</a></div></body></html>
"""

ADMIN_DASH_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WOI Admin Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;font-family:'Inter',Arial,sans-serif}body{margin:0;background:#f6f3f0;color:#1a1a1a}
.top{background:#1a0a12;color:white;padding:18px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.top b{font-size:19px}.top span{font-size:13px;opacity:.7}
.top a{background:white;color:#1a1a1a;padding:8px 14px;border-radius:20px;text-decoration:none;font-size:13px;font-weight:600}
.top a.red{background:#7a1f3d;color:white}
.wrap{max-width:1100px;margin:0 auto;padding:20px 16px 40px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}
@media(max-width:650px){.stats{grid-template-columns:1fr}}
.stat{background:white;border-radius:16px;padding:18px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.stat small{color:#888;text-transform:uppercase;letter-spacing:.5px;font-size:11px;font-weight:700}
.stat h3{margin:6px 0 0;font-size:30px}.stat p{margin:4px 0 0;font-size:13px;color:#777}
.stat.pink{border-top:4px solid #7a1f3d}.stat.gold{border-top:4px solid #c98a2e}.stat.green{border-top:4px solid #1a9a6b}
.search{width:100%;padding:13px 16px;border:1px solid #e5e0db;border-radius:12px;margin-bottom:20px;font-size:15px;outline:none}
.card{background:white;border-radius:16px;overflow:hidden;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.card-head{padding:16px 18px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #f0ece8}
.card-head h2{margin:0;font-size:16px}.badge{background:#fdf0e8;color:#7a1f3d;padding:5px 10px;border-radius:20px;font-size:12px;font-weight:700}
table{width:100%;border-collapse:collapse}th{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#999;padding:12px 18px;text-align:left;background:#faf8f6}
td{padding:12px 18px;border-top:1px solid #f5f1ed;font-size:14px}tr:hover td{background:#fffaf7}
.empty{padding:20px;text-align:center;color:#999;font-size:14px}
.pill{background:#e8f8f0;color:#0a7a52;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700}
</style></head>
<body>
<div class="top"><div><b>✦ WOI Admin</b><br><span>Women of Integrity • Dashboard</span></div><div><a href="/">View Site</a> <a class="red" href="/admin/logout">Logout</a></div></div>
<div class="wrap">
<div class="stats">
<div class="stat pink"><small>Total Members</small><h3>{{ members|length }}</h3><p>Registered women</p></div>
<div class="stat gold"><small>Total Donations</small><h3>{{ donations|length }}</h3><p>Donation records</p></div>
<div class="stat green"><small>Book Orders</small><h3>{{ orders|length }}</h3><p>Books ordered</p></div>
</div>
<input class="search" id="search" placeholder="🔍 Search members, donations, orders..." onkeyup="filterAll()">
<div class="card"><div class="card-head"><h2>👩‍🦰 Members</h2><span class="badge">{{ members|length }} total</span></div>
<table class="tbl"><tr><th>Name</th><th>Phone</th><th>Location</th><th>Date</th></tr>
{% for m in members %}<tr><td><b>{{ m['name'] }}</b></td><td>{{ m['phone'] }}</td><td>{{ m['location'] }}</td><td>{{ m['created_at'] }}</td></tr>{% else %}<tr><td colspan="4" class="empty">No members yet</td></tr>{% endfor %}</table></div>
<div class="card"><div class="card-head"><h2>💛 Donations</h2><span class="badge">{{ donations|length }} total</span></div>
<table class="tbl"><tr><th>Name</th><th>Project</th><th>Amount</th><th>Date</th></tr>
{% for d in donations %}<tr><td><b>{{ d['name'] }}</b></td><td>{{ d['project'] }}</td><td><span class="pill">K{{ d['amount'] }}</span></td><td>{{ d['created_at'] }}</td></tr>{% else %}<tr><td colspan="4" class="empty">No donations yet</td></tr>{% endfor %}</table></div>
<div class="card"><div class="card-head"><h2>📖 Book Orders</h2><span class="badge">{{ orders|length }} total</span></div>
<table class="tbl"><tr><th>Name</th><th>Phone</th><th>Book</th><th>Date</th></tr>
{% for o in orders %}<tr><td><b>{{ o['name'] }}</b></td><td>{{ o['phone'] }}</td><td>{{ o['book'] }}</td><td>{{ o['created_at'] }}</td></tr>{% else %}<tr><td colspan="4" class="empty">No book orders yet</td></tr>{% endfor %}</table></div>
</div>
<script>
function filterAll(){
  let q=document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('.tbl tr').forEach((r,i)=>{ if(i===0) return; r.style.display=r.textContent.toLowerCase().includes(q)?'':'none'; });
}
</script></body></html>
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
