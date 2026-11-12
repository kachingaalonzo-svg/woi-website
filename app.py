import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "woi-secret-2026-influence"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "woi.db")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, password TEXT, location TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS donations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, project TEXT, amount TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS book_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, book TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    c.execute("INSERT OR IGNORE INTO admins (username, password) VALUES ('admin','woi2026')")
    conn.commit()
    conn.close()

def fix_old_db():
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'")
        if not c.fetchone():
            conn.close()
            init_db()
            return
        conn.close()
    except Exception as e:
        print("DB fix:", e)
        init_db()

init_db()
fix_old_db()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/transparency')
def transparency():
    conn = get_db()
    try:
        donations = conn.execute("SELECT * FROM donations ORDER BY id DESC LIMIT 50").fetchall()
        total = conn.execute("SELECT COUNT(*) as c FROM donations").fetchone()
    except:
        donations = []
        total = {'c': 0}
    conn.close()
    return render_template('transparency.html', donations=donations, total=total)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        location = request.form.get('location', '')
        conn = get_db()
        conn.execute("INSERT INTO members (name, phone, email, password, location) VALUES (?,?,?,?,?)", (name, phone, email, password, location))
        conn.commit()
        conn.close()
        session['member_name'] = name
        session['member_phone'] = phone
        return redirect(url_for('member_dashboard'))
    return render_template('register.html')

@app.route('/member/login', methods=['GET', 'POST'])
def member_login():
    if request.method == 'POST':
        phone = request.form.get('phone', '')
        password = request.form.get('password', '')
        conn = get_db()
        m = conn.execute("SELECT * FROM members WHERE phone=? AND password=?", (phone, password)).fetchone()
        conn.close()
        if m:
            session['member_name'] = m['name']
            session['member_phone'] = m['phone']
            return redirect(url_for('member_dashboard'))
        return render_template('member_login.html', error="Wrong phone or password. Try again or register.")
    return render_template('member_login.html')

@app.route('/member/dashboard')
def member_dashboard():
    if 'member_name' not in session:
        return redirect(url_for('member_login'))
    return render_template('member_dashboard.html', name=session.get('member_name'))

@app.route('/member/logout')
def member_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        conn = get_db()
        a = conn.execute("SELECT * FROM admins WHERE username=? AND password=?", (u, p)).fetchone()
        conn.close()
        if a:
            session['admin'] = u
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="Wrong username or password. Default: admin / woi2026")
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    members = conn.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
    donations = conn.execute("SELECT * FROM donations ORDER BY id DESC").fetchall()
    books = conn.execute("SELECT * FROM book_orders ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin.html', members=members, donations=donations, books=books)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/donate', methods=['POST'])
def donate():
    data = request.get_json() or request.form
    name = data.get('name', '')
    project = data.get('project', 'General')
    amount = data.get('amount', '')
    conn = get_db()
    conn.execute("INSERT INTO donations (name, project, amount) VALUES (?,?,?)", (name, project, amount))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": f"Thank you {name}! Your K{amount} donation for {project} is received. God bless you! Send via Access Zambia - Thabo Mbeki. WhatsApp +260 975826286 to confirm."})

@app.route('/order-book', methods=['POST'])
def order_book():
    data = request.get_json() or request.form
    name = data.get('name', '')
    phone = data.get('phone', '')
    book = data.get('book', '')
    conn = get_db()
    conn.execute("INSERT INTO book_orders (name, phone, book) VALUES (?,?,?)", (name, phone, book))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "msg": f"Thank you {name}! Your order for '{book}' is received. We will call {phone} on WhatsApp +260 975826286."})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "site": "Women of Influence International"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
