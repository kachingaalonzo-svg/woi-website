from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = "woi-secret-key-2026"

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="woi-db"
    )

# ---------- HOME - YOUR index.html ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/transparency')
def transparency():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT COALESCE(SUM(amount),0) as total FROM donations")
    total_donations = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as total FROM members")
    total_members = cur.fetchone()['total']
    cur.execute("SELECT * FROM donations ORDER BY created_at DESC LIMIT 20")
    donations = cur.fetchall()
    cur.close(); db.close()
    return render_template('transparency.html', total_donations=total_donations, total_members=total_members, donations=donations)

# ---------- REGISTER - /register ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        location = request.form.get('location')
        interest = request.form.get('interest')
        try:
            db = get_db(); cur = db.cursor()
            cur.execute("INSERT INTO members (full_name, email, phone, password, location, interest) VALUES (%s,%s,%s,%s,%s,%s)",
                        (full_name, email, phone, password, location, interest))
            db.commit(); cur.close(); db.close()
            flash("Welcome to WOI! You can now login.", "success")
            return redirect(url_for('member_login'))
        except Exception as e:
            flash(f"Error: Email already registered.", "error")
    return render_template('register.html')

# ---------- MEMBER LOGIN ----------
@app.route('/member/login', methods=['GET','POST'])
def member_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM members WHERE email=%s AND password=%s", (email, password))
        member = cur.fetchone()
        cur.close(); db.close()
        if member:
            session['member_id'] = member['id']
            session['member_name'] = member['full_name']
            return redirect(url_for('member_dashboard'))
        else:
            flash("Wrong email or password", "error")
    return render_template('member_login.html')

@app.route('/member/dashboard')
def member_dashboard():
    if 'member_id' not in session:
        return redirect(url_for('member_login'))
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM members WHERE id=%s", (session['member_id'],))
    member = cur.fetchone()
    cur.close(); db.close()
    return render_template('member_dashboard.html', member=member)

@app.route('/member/logout')
def member_logout():
    session.clear()
    return redirect(url_for('home'))

# ---------- DONATE - JSON from your index.html ----------
@app.route('/donate', methods=['POST'])
def donate():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "No data"}), 400
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO donations (donor_name, project, amount) VALUES (%s,%s,%s)",
                (data.get('name'), data.get('project'), data.get('amount') or 0))
    db.commit(); cur.close(); db.close()
    return jsonify({"msg": "Thank you! Donation received. We will contact you."})

# ---------- ORDER BOOK - JSON from your index.html ----------
@app.route('/order-book', methods=['POST'])
def order_book():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "No data"}), 400
    book = data.get('book')
    price = 200 if book == 'Making Every Life Count' else 150
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO book_orders (customer_name, customer_phone, book_title, quantity, price, total_amount) VALUES (%s,%s,%s,1,%s,%s)",
                (data.get('name'), data.get('phone'), book, price, price))
    db.commit(); cur.close(); db.close()
    return jsonify({"msg": f"Order received for {book} - K{price}. We will call you!"})

# ---------- CONTACT ----------
@app.route('/contact', methods=['POST'])
def contact():
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO contacts (name, email, phone, subject, message) VALUES (%s,%s,%s,%s,%s)",
                (request.form.get('name'), request.form.get('email'), request.form.get('phone'), request.form.get('subject'), request.form.get('message')))
    db.commit(); cur.close(); db.close()
    flash("Message sent!")
    return redirect(url_for('home'))

# ---------- ADMIN ----------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM admins WHERE username=%s AND password=%s", (request.form.get('username'), request.form.get('password')))
        admin = cur.fetchone()
        cur.close(); db.close()
        if admin:
            session['admin'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        flash("Wrong username or password", "error")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM members ORDER BY created_at DESC"); members = cur.fetchall()
    cur.execute("SELECT * FROM donations ORDER BY created_at DESC"); donations = cur.fetchall()
    cur.execute("SELECT * FROM book_orders ORDER BY created_at DESC"); orders = cur.fetchall()
    cur.execute("SELECT * FROM contacts ORDER BY created_at DESC"); contacts = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(amount),0) as total FROM donations"); total_don = cur.fetchone()['total']
    cur.close(); db.close()
    return render_template('admin_dashboard.html', members=members, donations=donations, orders=orders, contacts=contacts, total_don=total_don)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
