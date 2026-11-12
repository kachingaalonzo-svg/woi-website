import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "woi-2026-secret")

# --- Render-safe paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'woi.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_db()
        conn.execute('''CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, location TEXT, profile_pic TEXT, created_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS donations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, project TEXT, amount TEXT, created_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS book_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, book TEXT, created_at TEXT)''')
        conn.commit(); conn.close()
    except Exception as e:
        print("DB INIT ERROR:", e)

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        try:
            conn = get_db()
            conn.execute("INSERT INTO members (name, phone, location, created_at) VALUES (?,?,?,?)",
                         (request.form.get('name'), request.form.get('phone'), request.form.get('location'), datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit(); conn.close()
            return render_template('register.html', success=True)
        except Exception as e:
            print("REGISTER ERROR:", e)
            return render_template('register.html', success=True)
    return render_template('register.html')

@app.route('/member/login', methods=['GET','POST'])
def member_login():
    if request.method == 'POST':
        phone = (request.form.get('phone') or '').strip()
        if not phone:
            return render_template('login.html', error="Please enter your phone number.")
        profile_pic_filename = None
        try:
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and file.filename != '':
                    safe_name = f"{phone}_{secure_filename(file.filename)}"
                    file.save(os.path.join(UPLOAD_FOLDER, safe_name))
                    profile_pic_filename = f"uploads/{safe_name}"
        except Exception as e:
            print("UPLOAD ERROR:", e)
        try:
            conn = get_db()
            try:
                conn.execute("ALTER TABLE members ADD COLUMN profile_pic TEXT")
                conn.commit()
            except:
                pass
            user = conn.execute("SELECT * FROM members WHERE phone=?", (phone,)).fetchone()
            if user:
                if profile_pic_filename:
                    conn.execute("UPDATE members SET profile_pic=? WHERE phone=?", (profile_pic_filename, phone))
                    conn.commit()
                    user = conn.execute("SELECT * FROM members WHERE phone=?", (phone,)).fetchone()
                conn.close()
                session['member'] = dict(user)
                return redirect(url_for('home'))
            conn.close()
            return render_template('login.html', error="Phone not found. Please register first.")
        except Exception as e:
            print("LOGIN ERROR:", e)
            return render_template('login.html', error="Something went wrong, please try again.")
    return render_template('login.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/transparency')
def transparency():
    try:
        conn = get_db()
        donations = conn.execute("SELECT * FROM donations ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
    except:
        donations = []
    return render_template('transparency.html', donations=donations)

@app.route('/donate', methods=['POST'])
def donate():
    d = request.json or {}
    try:
        conn = get_db()
        conn.execute("INSERT INTO donations (name, project, amount, created_at) VALUES (?,?,?,?)",
                     (d.get('name'), d.get('project'), d.get('amount'), datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
    except Exception as e:
        print("DONATE ERROR:", e)
    return jsonify({"msg": "Thank you! Your donation was recorded. God bless you. Send to Access Zambia - Thabo Mbeki."})

@app.route('/order-book', methods=['POST'])
def order_book():
    d = request.json or {}
    try:
        conn = get_db()
        conn.execute("INSERT INTO book_orders (name, phone, book, created_at) VALUES (?,?,?,?)",
                     (d.get('name'), d.get('phone'), d.get('book'), datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
    except Exception as e:
        print("BOOK ERROR:", e)
    return jsonify({"msg": "Order received! We will contact you on WhatsApp."})

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'woi2026':
            session['admin'] = True
            return redirect(url_for('admin'))
        return render_template('admin_login.html', error="Wrong login")
    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        conn = get_db()
        members = conn.execute("SELECT * FROM members ORDER BY id DESC").fetchall()
        donations = conn.execute("SELECT * FROM donations ORDER BY id DESC").fetchall()
        books = conn.execute("SELECT * FROM book_orders ORDER BY id DESC").fetchall()
        conn.close()
    except:
        members=[]; donations=[]; books=[]
    return render_template('admin.html', members=members, donations=donations, books=books)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/health')
def health():
    return "WOI OK"

# --- THIS IS THE RENDER FIX ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
