from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
import os, csv, io
from datetime import datetime
import mysql.connector
from werkzeug.utils import secure_filename

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    HAS_EXCEL = True
except:
    HAS_EXCEL = False
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_PDF = True
except:
    HAS_PDF = False

app = Flask(__name__)
app.secret_key = 'woi-4000-strong'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_CONFIG = {'host': 'localhost', 'user': 'root', 'password': '', 'database': 'woi', 'port': 3306}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def ensure_db_exists():
    conn = mysql.connector.connect(host='localhost', user='root', password='', port=3306)
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS woi")
    conn.commit()
    cur.close()
    conn.close()

def add_column_if_missing(cur, table, column, definition):
    # FIX: Adds missing columns to OLD tables without deleting data
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
    except Exception as e:
        # If MariaDB version doesn't support IF NOT EXISTS, try plain ADD and ignore duplicate error
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except:
            pass

def init_db():
    ensure_db_exists()
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # Create tables if they don't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS members (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), phone VARCHAR(50) UNIQUE, password VARCHAR(255), role VARCHAR(20) DEFAULT 'member', lives VARCHAR(255), past_church VARCHAR(255), nrc VARCHAR(100), pic VARCHAR(255), joined VARCHAR(20), email VARCHAR(255), interest VARCHAR(255), created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS donations (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255), project VARCHAR(255), amount VARCHAR(50), phone VARCHAR(50), created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS book_orders (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255), phone VARCHAR(50), book VARCHAR(255), total VARCHAR(50) DEFAULT 'K150', status VARCHAR(50) DEFAULT 'Pending', created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS logins (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), phone VARCHAR(50), email VARCHAR(255), role VARCHAR(20), login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ip VARCHAR(100))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255), message TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # ===== AUTO-MIGRATION: Fix OLD tables that were created before email/interest existed =====
    add_column_if_missing(cur, 'members', 'email', 'VARCHAR(255)')
    add_column_if_missing(cur, 'members', 'interest', 'VARCHAR(255)')
    add_column_if_missing(cur, 'members', 'created', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    add_column_if_missing(cur, 'members', 'lives', 'VARCHAR(255)')
    add_column_if_missing(cur, 'members', 'past_church', 'VARCHAR(255)')
    add_column_if_missing(cur, 'members', 'nrc', 'VARCHAR(100)')
    add_column_if_missing(cur, 'members', 'pic', 'VARCHAR(255)')
    add_column_if_missing(cur, 'members', 'joined', 'VARCHAR(20)')
    add_column_if_missing(cur, 'donations', 'email', 'VARCHAR(255)')
    add_column_if_missing(cur, 'book_orders', 'email', 'VARCHAR(255)')
    add_column_if_missing(cur, 'book_orders', 'total', "VARCHAR(50) DEFAULT 'K150'")
    add_column_if_missing(cur, 'book_orders', 'status', "VARCHAR(50) DEFAULT 'Pending'")
    add_column_if_missing(cur, 'logins', 'email', 'VARCHAR(255)')
    add_column_if_missing(cur, 'logins', 'ip', 'VARCHAR(100)')
    conn.commit()
    # Seed admin
    cur.execute("SELECT * FROM members WHERE phone='0975826286'")
    if not cur.fetchone():
        cur.execute("INSERT INTO members (name, phone, password, role, lives, past_church, nrc, pic, joined, email, interest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", ('Prophetess Elfridah Mhusambazi', '0975826286', 'woi1997', 'admin', 'Mass Media, Lusaka', 'Barak Ministries', '', '', '1997', 'admin@woi.com', 'Leadership'))
    cur.execute("SELECT * FROM members WHERE phone='0970000000'")
    if not cur.fetchone():
        cur.execute("INSERT INTO members (name, phone, password, role, lives, past_church, nrc, pic, joined, email, interest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", ('Test Member', '0970000000', '1234', 'member', 'Lusaka', 'Test Church', '', '', '2026', 'test@test.com', 'Leadership'))
    conn.commit()
    cur.close()
    conn.close()

init_db()

def get_member_by_phone(phone):
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM members WHERE phone=%s", (phone,)); row = cur.fetchone(); cur.close(); conn.close(); return row
def all_members(search=''):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    if search:
        cur.execute("SELECT * FROM members WHERE name LIKE %s OR phone LIKE %s OR lives LIKE %s ORDER BY id DESC", ('%'+search+'%', '%'+search+'%', '%'+search+'%'))
    else:
        cur.execute("SELECT * FROM members ORDER BY id DESC")
    rows = cur.fetchall(); cur.close(); conn.close(); return rows
def all_donations():
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM donations ORDER BY id DESC"); rows = cur.fetchall(); cur.close(); conn.close(); return rows
def all_orders():
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM book_orders ORDER BY id DESC"); rows = cur.fetchall(); cur.close(); conn.close(); return rows
def all_messages():
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM messages ORDER BY id DESC"); rows = cur.fetchall(); cur.close(); conn.close(); return rows
def all_logins():
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM logins ORDER BY login_time DESC"); rows = cur.fetchall(); cur.close(); conn.close(); return rows
def log_login(member, ip):
    email = member.get('email') or ''
    conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO logins (name, phone, email, role, ip) VALUES (%s,%s,%s,%s,%s)", (member['name'], member['phone'], email, member['role'], ip)); conn.commit(); cur.close(); conn.close()
def get_login_stats():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as c FROM logins"); total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM logins WHERE DATE(login_time) = CURDATE()"); today = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM logins WHERE login_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)"); week = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM logins WHERE phone='0975826286'"); my_logins = cur.fetchone()['c']
    cur.execute("SELECT name, email, phone, role, COUNT(*) as cnt, MAX(login_time) as last_login FROM logins GROUP BY phone, name, email, role ORDER BY cnt DESC LIMIT 20"); top_users = cur.fetchall()
    cur.execute("SELECT * FROM logins ORDER BY login_time DESC LIMIT 30"); recent = cur.fetchall()
    cur.close(); conn.close(); return total, today, week, my_logins, top_users, recent
def get_my_login_info(phone):
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT COUNT(*) as c FROM logins WHERE phone=%s", (phone,)); count = cur.fetchone()['c']; cur.execute("SELECT MAX(login_time) as last_login FROM logins WHERE phone=%s", (phone,)); last = cur.fetchone()['last_login']; cur.close(); conn.close(); return count, last

def export_csv(headers, rows, filename):
    output = io.StringIO(); w = csv.writer(output); w.writerow(headers)
    for r in rows: w.writerow(r)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=' + filename + '.csv'})
def export_excel(headers, rows, filename, sheet_name):
    if not HAS_EXCEL: return Response("Run: pip install openpyxl", status=500)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = sheet_name
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    c = ws.cell(row=1, column=1, value="WOMEN OF INFLUENCE INTERNATIONAL - " + sheet_name.upper()); c.font = Font(bold=True, size=14, color="2A0A2A"); c.alignment = Alignment(horizontal='center')
    fill = PatternFill(start_color="2A0A2A", end_color="2A0A2A", fill_type="solid")
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=col, value=h); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = fill; cell.alignment = Alignment(horizontal='center')
    for r_idx, row in enumerate(rows, start=4):
        for c_idx, val in enumerate(row, start=1): ws.cell(row=r_idx, column=c_idx, value=str(val))
    for col in range(1, len(headers)+1): ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22
    bio = io.BytesIO(); wb.save(bio); bio.seek(0)
    return Response(bio.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment; filename=' + filename + '.xlsx'})
def export_pdf(headers, rows, filename, title):
    if not HAS_PDF: return Response("Run: pip install reportlab", status=500)
    bio = io.BytesIO(); doc = SimpleDocTemplate(bio, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet(); story = []
    story.append(Paragraph("Women of Influence International", styles['Title']))
    story.append(Paragraph(title + " - Making Every Life Count | Est. 1997 | PACRA 51848", styles['Normal'])); story.append(Spacer(1, 12))
    data = [headers] + [[str(x) for x in r] for r in rows]
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2A0A2A')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 9), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF9F5')]), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8D5DE')), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story.append(t); doc.build(story); bio.seek(0)
    return Response(bio.getvalue(), mimetype='application/pdf', headers={'Content-Disposition': 'attachment; filename=' + filename + '.pdf'})
def get_export_data(kind):
    if kind == 'members':
        headers = ['ID', 'Name', 'Email', 'Phone', 'Location', 'Interest', 'Date']
        rows = [[x['id'], x['name'], x.get('email') or '', x['phone'], x.get('lives') or '', x.get('interest') or '', x.get('created') or x.get('joined') or ''] for x in all_members()]
        return headers, rows, 'woi_members', 'WOI Members'
    if kind == 'donations':
        headers = ['ID', 'Name', 'Email', 'Project', 'Amount', 'Date']
        rows = [[d['id'], d['name'], d.get('email') or '', d['project'], d['amount'], d['created']] for d in all_donations()]
        return headers, rows, 'woi_donations', 'WOI Donations'
    if kind == 'books':
        headers = ['ID', 'Name', 'Phone', 'Book', 'Total', 'Status', 'Date']
        rows = [[b['id'], b['name'], b['phone'], b['book'], b.get('total') or 'K150', b.get('status') or 'Pending', b['created']] for b in all_orders()]
        return headers, rows, 'woi_book_orders', 'WOI Book Orders'
    if kind == 'logins':
        headers = ['ID', 'Name', 'Email', 'Role', 'Login Time', 'IP']
        rows = [[r['id'], r['name'], r.get('email') or '', r['role'], r['login_time'], r['ip']] for r in all_logins()]
        return headers, rows, 'woi_logins', 'WOI Login Tracking'
    if kind == 'messages':
        headers = ['ID', 'Name', 'Email', 'Message', 'Date']
        rows = [[r['id'], r['name'], r.get('email') or '', r['message'], r['created']] for r in all_messages()]
        return headers, rows, 'woi_messages', 'WOI Messages'
    return [], [], '', ''

ADMIN_CSS = "<style>body{font-family:Inter,Arial,sans-serif;background:#FDEAF3;margin:0;color:#1a1a1a}.top{background:#111;color:white;padding:14px 22px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10}.top b{font-size:17px}.top small{opacity:0.7;font-size:12px}.top a{color:white;text-decoration:none;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:700}.btn-gold{background:#D4AF37!important;color:#111!important}.btn-dark2{background:#333!important}.wrap{max-width:1100px;margin:0 auto;padding:22px}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}@media(max-width:800px){.stats{grid-template-columns:1fr 1fr}}.stat{background:white;border-radius:16px;padding:18px;box-shadow:0 4px 15px rgba(0,0,0,0.05)}.stat.purple{background:#2A0A2A;color:white}.stat.gold{background:#D4AF37;color:#111}.stat b{font-size:26px;display:block}.stat span{font-size:12px;opacity:0.8}.stat small{font-size:11px;opacity:0.7}.card{background:white;border-radius:16px;padding:22px;box-shadow:0 4px 15px rgba(0,0,0,0.05);margin-top:16px}.card h3{margin:0;font-size:18px}.card p.sub{color:#888;font-size:12px;margin:4px 0 0}.btn{display:inline-block;background:#111;color:white;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:700;border:none;cursor:pointer;font-size:12px;margin:3px}.btn-gold2{background:#D4AF37;color:#111}.btn-white{background:white;color:#111;border:1px solid #ddd}.btn-green{background:#25D366;color:white}.btn-pink{background:#C93A8A;color:white}table{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}th{text-align:left;padding:10px;background:#FFF3E6;font-size:12px}td{padding:10px;border-bottom:1px solid #f0f0f0}input{width:100%;padding:12px;border:1px solid #eee;border-radius:10px;margin-top:10px;box-sizing:border-box;background:#FFF9F5}label{font-size:12px;font-weight:700}.export{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}</style>"
LOGIN_CSS = "<style>body{font-family:Inter,Arial,sans-serif;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a0a2a 0%,#2A0A2A 40%,#8a6d1a 70%,#D4AF37 100%)}.card{background:white;border-radius:18px;padding:34px 30px;width:100%;max-width:360px;box-shadow:0 20px 50px rgba(0,0,0,0.3);text-align:center}.card h2{margin:8px 0 2px;font-size:22px}.card p{color:#888;font-size:12px;margin:0}input{width:100%;padding:12px;border:none;border-radius:8px;margin-top:10px;box-sizing:border-box;background:#EEF2FF;font-size:14px}label{font-size:12px;font-weight:700;display:block;text-align:left;margin-top:14px}.btn{width:100%;background:#111;color:white;padding:13px;border:none;border-radius:8px;font-weight:700;cursor:pointer;margin-top:16px}.demo{background:#FFF8DC;padding:10px;border-radius:8px;font-size:11px;color:#666;margin-top:12px}.back{font-size:12px;color:#111;font-weight:700;display:block;margin-top:12px}</style>"

def current_member():
    phone = session.get('member_phone')
    if not phone: return None
    return get_member_by_phone(phone)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', ''); phone = request.form.get('phone', '').strip(); password = request.form.get('password', '') or '1234'; lives = request.form.get('lives', ''); past_church = request.form.get('past_church', ''); nrc = request.form.get('nrc', ''); pic_path = ''
        f = request.files.get('pic')
        if f and f.filename != '':
            filename = secure_filename(phone + '_' + f.filename); save_to = os.path.join(app.config['UPLOAD_FOLDER'], filename); f.save(save_to); pic_path = '/static/uploads/' + filename
        conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM members WHERE phone=%s", (phone,)); existing = cur.fetchone()
        if existing:
            cur.execute("UPDATE members SET name=%s, password=%s, lives=%s, past_church=%s, nrc=%s WHERE phone=%s", (name, password, lives, past_church, nrc, phone))
            if pic_path: cur.execute("UPDATE members SET pic=%s WHERE phone=%s", (pic_path, phone))
        else:
            cur.execute("INSERT INTO members (name, phone, password, role, lives, past_church, nrc, pic, joined, email, interest) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (name, phone, password, 'member', lives, past_church, nrc, pic_path, '2026', '', 'Leadership'))
        conn.commit(); cur.close(); conn.close(); session['member_phone'] = phone; return redirect(url_for('member_dashboard'))
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Join WOI</title>" + ADMIN_CSS + "</head><body>"
    html += "<div class='top'><b>WOI • WOMEN OF INFLUENCE</b><a href='/'>Home</a></div>"
    html += "<div class='wrap'><div class='card' style='background:#2A0A2A;color:white;text-align:center'><h1 style='font-size:30px'>Become a Woman of Influence.</h1><p style='opacity:0.8;margin-top:8px'>Faith • Skills • Sisterhood</p></div>"
    html += "<form method='POST' enctype='multipart/form-data'>"
    html += "<div class='card'><h3>1. About You</h3><label>Full Name *</label><input name='name' placeholder='e.g. Mary Banda' required><label>Phone / WhatsApp *</label><input name='phone' placeholder='e.g. 0975826286' required><label>Create Password *</label><input type='password' name='password' placeholder='Create password' required></div>"
    html += "<div class='card'><h3>2. Where You Live & Your Church</h3><label>Where Do You Live? *</label><input name='lives' placeholder='e.g. Garden, Matero, Kabwata' required><label>Past / Current Church *</label><input name='past_church' placeholder='e.g. Barak Ministries' required><label>NRC Number (Optional)</label><input name='nrc' placeholder='e.g. 123456/11/1 - can leave blank'></div>"
    html += "<div class='card'><h3>3. Your Profile Picture</h3><input type='file' name='pic' accept='image/*'></div>"
    html += "<div class='card' style='text-align:center'><p>First Saturday Meeting<br><b>13:00 - 18:00 - Mass Media, Lusaka</b></p><button class='btn' style='width:100%;margin-top:12px;padding:14px'>Join WOI - Become a Member →</button><p style='margin-top:10px'>Already a member? <a href='/member/login'>Login here</a></p></div>"
    html += "</form></div></body></html>"
    return html

@app.route('/member/login', methods=['GET', 'POST'])
def member_login():
    error = ''
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip(); password = request.form.get('password', '').strip(); m = get_member_by_phone(phone)
        if m and m['password'] == password:
            log_login(m, request.remote_addr or ''); session['member_phone'] = phone
            if m['role'] == 'admin': return redirect(url_for('admin_dashboard'))
            return redirect(url_for('member_dashboard'))
        error = 'Wrong phone or password.'
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Member Login - WOI</title>" + LOGIN_CSS + "</head><body>"
    html += "<div class='card'><div style='font-size:32px'>🔒</div><h2>Member Portal</h2><p>WOI Members Only</p>"
    if error: html += "<p style='background:#FCE4F0;color:#C93A8A;padding:10px;border-radius:8px;margin-top:12px'>" + error + "</p>"
    html += "<form method='POST'><label>Username</label><input name='phone' placeholder='Phone / WhatsApp' required><label>Password</label><input type='password' name='password' placeholder='Password' required><button class='btn'>Login as Member →</button></form>"
    html += "<div class='demo'>Demo: 0970000000 / 1234</div><a href='/' class='back'>← Back to Home</a></div></body></html>"
    return html

@app.route('/member/dashboard')
def member_dashboard():
    m = current_member()
    if not m: return redirect(url_for('member_login'))
    pic = "<img src='" + m['pic'] + "' style='width:70px;height:70px;border-radius:50%;object-fit:cover'>" if m['pic'] else "<div style='width:70px;height:70px;border-radius:50%;background:#2A0A2A;color:white;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:900'>" + m['name'][0] + "</div>"
    my_count, my_last = get_my_login_info(m['phone'])
    conn = get_db(); cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM donations WHERE name=%s", (m['name'],)); my_don = cur.fetchall(); cur.execute("SELECT * FROM book_orders WHERE name=%s", (m['name'],)); my_books = cur.fetchall(); cur.close(); conn.close()
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>My Dashboard</title>" + ADMIN_CSS + "</head><body>"
    html += "<div class='top'><div><b>👑 WOI Member Dashboard</b><br><small>Welcome, " + m['name'] + "</small></div><div><a href='/' class='btn-gold'>View Site</a> <a href='/member/logout' class='btn-dark2'>Logout</a></div></div>"
    html += "<div class='wrap'><div class='card' style='display:flex;gap:16px;align-items:center'>" + pic + "<div><h3>Welcome, " + m['name'] + "</h3><p class='sub'>📍 " + (m.get('lives') or '') + " • ⛪ " + (m.get('past_church') or '') + " • 📱 " + m['phone'] + "<br><b>You have logged in " + str(my_count) + " times</b> • Last: " + str(my_last) + "</p></div></div>"
    html += "<div class='card'><h3>Next Meeting</h3><p class='sub'>First Saturday - 13:00-18:00 • Mass Media, Lusaka</p><a href='/#donate' class='btn btn-pink'>Donate</a> <a href='/#books' class='btn'>Order Book</a></div>"
    html += "<div class='card'><h3>My Donations (" + str(len(my_don)) + ")</h3>"
    for d in my_don: html += "<p>" + str(d['project']) + " - K" + str(d['amount']) + "</p>"
    html += "<h3 style='margin-top:14px'>My Book Orders (" + str(len(my_books)) + ")</h3>"
    for b in my_books: html += "<p>" + str(b['book']) + "</p></div></div></body></html>"
    return html

@app.route('/member/logout')
def member_logout():
    session.clear(); return redirect(url_for('home'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip(); password = request.form.get('password', '').strip()
        phone_clean = phone.replace('+', '').replace(' ', '')
        if phone_clean.startswith('260'): phone_clean = '0' + phone_clean[3:]
        is_admin = (phone.lower() == 'admin' and password in ['woi2026', 'woi1997', '1234']) or (phone_clean == '0975826286' and password in ['woi1997', 'woi2026', '1234']) or (phone.lower() in ['elfridah', 'prophetess'] and password in ['woi1997', 'woi2026'])
        if is_admin:
            m = get_member_by_phone('0975826286')
            if m: log_login(m, request.remote_addr or '')
            session['member_phone'] = '0975826286'; session['admin_name'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        error = 'Wrong username or password.'
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Admin Login - WOI</title>" + LOGIN_CSS + "</head><body>"
    html += "<div class='card'><div style='font-size:32px'>🔒</div><h2>Admin Portal</h2><p>WOI Management Only</p>"
    if error: html += "<p style='background:#FCE4F0;color:#C93A8A;padding:10px;border-radius:8px;margin-top:12px'>" + error + "</p>"
    html += "<form method='POST'><label>Username</label><input name='phone' placeholder='admin' value='admin' required><label>Password</label><input type='password' name='password' placeholder='••••••••' required><button class='btn'>Login as Admin →</button></form>"
    html += "<div class='demo'>Demo: admin / woi2026<br>Change this after you go live!</div><a href='/' class='back'>← Back to Home</a></div></body></html>"
    return html

@app.route('/admin')
def admin_dashboard():
    return redirect(url_for('admin_dashboard_new'))

@app.route('/admin/dashboard')
def admin_dashboard_new():
    m = current_member()
    if not m or m['role'] != 'admin': return redirect(url_for('admin_login'))
    search = request.args.get('search', '')
    members_list = all_members(search); donations_list = all_donations(); orders_list = all_orders(); messages_list = all_messages()
    total_logins, today_logins, week_logins, my_logins, top_users, recent_logins = get_login_stats()
    total_don = 0
    for d in donations_list:
        try: total_don += float(str(d['amount']).replace('K', '').strip() or 0)
        except: pass
    today_str = datetime.now().strftime('%d %B %Y')
    rows_top = ''
    for u in top_users:
        email = u.get('email') or ''
        rows_top += "<tr><td><b>" + str(u['name']) + "</b></td><td>" + str(email) + "</td><td>" + str(u['cnt']) + "x</td><td>" + str(u['last_login']) + "</td></tr>"
    if not rows_top: rows_top = "<tr><td colspan=4>No logins yet</td></tr>"
    rows_recent = ''
    for l in recent_logins:
        rows_recent += "<tr><td>" + str(l['role']).capitalize() + "</td><td>" + str(l['name']) + "</td><td>" + str(l.get('email') or '') + "</td><td>" + str(l['login_time']) + "</td></tr>"
    if not rows_recent: rows_recent = "<tr><td colspan=4>No logins yet</td></tr>"
    rows_m = ''
    for x in members_list:
        rows_m += "<tr><td>" + x['name'] + "</td><td>" + str(x.get('email') or '') + "</td><td>" + x['phone'] + "</td><td>" + (x.get('lives') or '') + "</td><td>" + str(x.get('interest') or 'Leadership') + "</td><td>" + str(x.get('created') or x.get('joined') or '') + "</td></tr>"
    if not rows_m: rows_m = "<tr><td colspan=6>No members yet</td></tr>"
    rows_d = ''
    for d in donations_list:
        rows_d += "<tr><td>" + str(d['name']) + "</td><td>" + str(d.get('email') or '') + "</td><td>" + str(d['project']) + "</td><td>K" + str(d['amount']) + "</td><td>" + str(d['created']) + "</td></tr>"
    if not rows_d: rows_d = "<tr><td colspan=5>No donations yet</td></tr>"
    rows_b = ''
    for b in orders_list:
        rows_b += "<tr><td>" + str(b['name']) + "</td><td>" + str(b['phone']) + "</td><td>" + str(b['book']) + "</td><td>" + str(b.get('total') or 'K150') + "</td><td>" + str(b.get('status') or 'Pending') + "</td><td>" + str(b['created']) + "</td></tr>"
    if not rows_b: rows_b = "<tr><td colspan=6>No orders yet</td></tr>"
    rows_msg = ''
    for msg in messages_list:
        rows_msg += "<tr><td>" + str(msg['name']) + "</td><td>" + str(msg['message']) + "</td></tr>"
    if not rows_msg: rows_msg = "<tr><td colspan=2>No messages</td></tr>"
    def exp(kind):
        return "<div class='export'><a href='/admin/export/" + kind + "/csv' class='btn'>📄 CSV</a><a href='/admin/export/" + kind + "/xlsx' class='btn btn-green'>📊 Excel (XLSX)</a><a href='/admin/export/" + kind + "/pdf' class='btn btn-gold2'>📕 PDF</a></div>"
    html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>Admin Dashboard - WOI</title>" + ADMIN_CSS + "</head><body>"
    html += "<div class='top'><div><b>👑 WOI Admin Dashboard</b><br><small>Logged in as admin • " + today_str + "</small></div><div><a href='/' class='btn-gold'>View Site</a> <a href='/member/logout' class='btn-dark2'>Logout</a></div></div>"
    html += "<div class='wrap'>"
    html += "<div class='stats'>"
    html += "<div class='stat purple'><span>👥</span><b>" + str(len(members_list)) + "</b><span>Total Members</span></div>"
    html += "<div class='stat gold'><span>💰</span><b>K" + ('%.2f' % total_don) + "</b><span>Total Donations</span></div>"
    html += "<div class='stat'><span>🧾</span><b>" + str(len(donations_list)) + "</b><span>Donation Records</span></div>"
    html += "<div class='stat'><span>📚</span><b>" + str(len(orders_list)) + "</b><span>Book Orders</span></div>"
    html += "<div class='stat'><span>💬</span><b>" + str(len(messages_list)) + "</b><span>Messages</span></div>"
    html += "</div>"
    html += "<div class='stats' style='margin-top:14px'><div class='stat purple'><span>🔑</span><b>" + str(total_logins) + "</b><span>Total Logins</span></div><div class='stat'><span>📅</span><b>" + str(today_logins) + "</b><span>Logins Today</span></div><div class='stat'><span>📈</span><b>" + str(week_logins) + "</b><span>Last 7 Days</span></div><div class='stat gold'><span>👑</span><b>" + str(my_logins) + "</b><span>Your Logins</span></div><div class='stat'><span>👥</span><b>" + str(len(members_list)) + "</b><span>Members</span></div></div>"
    html += "<div style='margin-top:14px'><button onclick='window.print()' class='btn'>🖨️ Print Full Report</button><button onclick='window.print()' class='btn btn-gold2'>Clean Printable Report</button><a href='/transparency' class='btn btn-white'>Public Transparency</a></div>"
    html += "<div class='card'><h3>🔑 Login Activity - How Often People Login</h3><p class='sub'>Who logs in the most? Who was last active?</p>" + exp('logins') + "<table><tr><th>Member</th><th>Email</th><th>Total Logins</th><th>Last Login</th></tr>" + rows_top + "</table></div>"
    html += "<div class='card'><h3>Recent Logins (Last 30)</h3><p class='sub'>Every login, newest first</p><table><tr><th>Type</th><th>Name</th><th>Email</th><th>Time</th></tr>" + rows_recent + "</table></div>"
    html += "<div class='card'><h3>Members (" + str(len(members_list)) + ")</h3><p class='sub'>Everyone who joined WOI</p>" + exp('members')
    html += "<form method='GET' action='/admin/dashboard'><input name='search' placeholder='🔍 Search members...' value='" + search + "'></form>"
    html += "<table><tr><th>Name</th><th>Email</th><th>Phone</th><th>Location</th><th>Interest</th><th>Date</th></tr>" + rows_m + "</table></div>"
    html += "<div class='card'><h3>Donations</h3><p class='sub'>All donations received</p>" + exp('donations') + "<table><tr><th>Donor</th><th>Email</th><th>Project</th><th>Amount</th><th>Date</th></tr>" + rows_d + "</table></div>"
    html += "<div class='card'><h3>Book Orders</h3><p class='sub'>Woman of Influence - K150 each</p>" + exp('books') + "<table><tr><th>Customer</th><th>Phone</th><th>Book</th><th>Total</th><th>Status</th><th>Date</th></tr>" + rows_b + "</table></div>"
    html += "<div class='card'><h3>Messages</h3><p class='sub'>Contact form messages</p>" + exp('messages') + "<table><tr><th>Name</th><th>Message</th></tr>" + rows_msg + "</table></div>"
    html += "<p style='text-align:center;color:#999;font-size:11px;margin-top:18px'>Women of Influence (WOI) - Official Report - Generated by WOI System</p>"
    html += "</div></body></html>"
    return html

@app.route('/admin/export/<kind>/<fmt>')
def export_data(kind, fmt):
    m = current_member()
    if not m or m['role'] != 'admin': return redirect(url_for('admin_login'))
    if kind not in ['members', 'donations', 'books', 'logins', 'messages']: return "Invalid", 400
    headers, rows, filename, title = get_export_data(kind)
    if fmt == 'csv': return export_csv(headers, rows, filename)
    if fmt == 'xlsx': return export_excel(headers, rows, filename, title)
    if fmt == 'pdf': return export_pdf(headers, rows, filename, title)
    return "Invalid format", 400

@app.route('/admin/export/members.csv')
def old_members_csv(): return redirect(url_for('export_data', kind='members', fmt='csv'))
@app.route('/admin/export/donations.csv')
def old_donations_csv(): return redirect(url_for('export_data', kind='donations', fmt='csv'))
@app.route('/admin/export/books.csv')
def old_books_csv(): return redirect(url_for('export_data', kind='books', fmt='csv'))
@app.route('/admin/export/logins.csv')
def old_logins_csv(): return redirect(url_for('export_data', kind='logins', fmt='csv'))

@app.route('/history')
def history():
    return "<h2 style='font-family:Arial;padding:20px'>1997 - Garden Compound, Lusaka<br>Prophetess Elfridah began WOI. 150 orphans, skills training, now 4000 Women Strong.</h2><p style='font-family:Arial;padding:0 20px'><a href='/'>Back Home</a></p>"

@app.route('/transparency')
def transparency():
    total = 0
    for d in all_donations():
        try: total += float(str(d['amount']).replace('K', '').strip() or 0)
        except: pass
    return "<h2 style='font-family:Arial;padding:20px'>Transparency - PACRA 51848 - Access Zambia, Thabo Mbeki<br>Total Donations: K" + str(total) + "</h2><p style='font-family:Arial;padding:0 20px'><a href='/'>Back Home</a></p>"

@app.route('/donate', methods=['POST'])
def donate():
    data = request.get_json() or {}; conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO donations (name, email, project, amount, phone) VALUES (%s,%s,%s,%s,%s)", (str(data.get('name', '')), str(data.get('email', '')), str(data.get('project', '')), str(data.get('amount', '')), str(data.get('phone', '')))); conn.commit(); cur.close(); conn.close(); return jsonify({'msg': "Thank you " + str(data.get('name', '')) + "! Donation received. God bless you!"})

@app.route('/order-book', methods=['POST'])
def order_book():
    data = request.get_json() or {}; conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO book_orders (name, email, phone, book) VALUES (%s,%s,%s,%s)", (str(data.get('name', '')), str(data.get('email', '')), str(data.get('phone', '')), str(data.get('book', '')))); conn.commit(); cur.close(); conn.close(); return jsonify({'msg': "Thank you " + str(data.get('name', '')) + "! Book order received."})

@app.route('/contact', methods=['POST'])
def contact():
    data = request.get_json() or {}; conn = get_db(); cur = conn.cursor(); cur.execute("INSERT INTO messages (name, email, message) VALUES (%s,%s,%s)", (str(data.get('name', '')), str(data.get('email', '')), str(data.get('message', '')))); conn.commit(); cur.close(); conn.close(); return jsonify({'msg': "Message received. Thank you!"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
