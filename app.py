import os
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Date, func
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "woi-secret-2024-lusaka")
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','webp'}

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///woi.db"
# fix for Render postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# MODELS
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    nrc = Column(String(50))
    dob = Column(String(20))
    gender = Column(String(20))
    marital_status = Column(String(20))
    phone = Column(String(30), nullable=False)
    whatsapp = Column(String(30))
    residential_address = Column(String(300))
    compound = Column(String(100))
    district = Column(String(100))
    province = Column(String(100))
    occupation = Column(String(100))
    church = Column(String(200))
    foundation_interest = Column(String(100))
    next_of_kin_name = Column(String(200))
    next_of_kin_phone = Column(String(30))
    profile_pic = Column(String(300))
    membership_status = Column(String(30), default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    phone = Column(String(50))
    province = Column(String(100))
    church = Column(String(200))
    foundation = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    project = Column(String(100))
    amount = Column(String(50))
    method = Column(String(50))
    reference = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class BookOrder(Base):
    __tablename__ = "book_orders"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    phone = Column(String(50))
    book = Column(String(100))
    method = Column(String(50))
    ref = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class HistoryEntry(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ROUTES
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/history.html")
@app.route("/history")
def history_page():
    db = SessionLocal()
    entries = db.query(HistoryEntry).order_by(HistoryEntry.created_at.desc()).all()
    db.close()
    return render_template("history.html", entries=entries)

@app.route("/transparency")
def transparency_page():
    db = SessionLocal()
    donations = db.query(Donation).order_by(Donation.created_at.desc()).all()
    total = len(donations)
    db.close()
    return render_template("transparency.html", donations=donations, total=total)

# NEW REGISTRATION
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    db = SessionLocal()
    try:
        email = request.form.get("email","").strip().lower()
        if db.query(User).filter_by(email=email).first():
            db.close()
            return jsonify({"ok":False,"msg":"Email already registered. Please login."}), 400
        
        # handle pic
        pic_path = ""
        file = request.files.get("profile_pic")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            pic_path = f"/static/uploads/{filename}"

        user = User(
            email=email,
            password_hash=generate_password_hash(request.form.get("password","")),
            full_name=request.form.get("full_name"),
            nrc=request.form.get("nrc"),
            dob=request.form.get("dob"),
            gender=request.form.get("gender"),
            marital_status=request.form.get("marital_status"),
            phone=request.form.get("phone"),
            whatsapp=request.form.get("whatsapp"),
            residential_address=request.form.get("residential_address"),
            compound=request.form.get("compound"),
            district=request.form.get("district","Lusaka"),
            province=request.form.get("province","Lusaka"),
            occupation=request.form.get("occupation"),
            church=request.form.get("church"),
            foundation_interest=request.form.get("foundation_interest"),
            next_of_kin_name=request.form.get("next_of_kin_name"),
            next_of_kin_phone=request.form.get("next_of_kin_phone"),
            profile_pic=pic_path,
            membership_status="Pending"
        )
        db.add(user)
        db.commit()
        session["user_id"] = user.id
        session["user_name"] = user.full_name
        db.close()
        return redirect("/member/dashboard")
    except Exception as e:
        db.rollback()
        db.close()
        return f"Error: {e}", 500

@app.route("/member/login", methods=["GET","POST"])
def member_login():
    if request.method == "GET":
        return render_template("member_login.html")
    email = request.form.get("email","").lower().strip()
    password = request.form.get("password","")
    db = SessionLocal()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    if user and check_password_hash(user.password_hash, password):
        session["user_id"] = user.id
        session["user_name"] = user.full_name
        return redirect("/member/dashboard")
    return render_template("member_login.html", error="Invalid email or password")

@app.route("/member/dashboard")
def member_dashboard():
    if "user_id" not in session:
        return redirect("/member/login")
    db = SessionLocal()
    user = db.query(User).filter_by(id=session["user_id"]).first()
    db.close()
    if not user:
        session.clear()
        return redirect("/member/login")
    return render_template("member_dashboard.html", user=user)

@app.route("/member/logout")
def member_logout():
    session.clear()
    return redirect("/")

# OLD APIS KEEP
@app.route("/join", methods=["POST"])
def join():
    data = request.get_json() or {}
    db = SessionLocal()
    m = Member(name=data.get("name"), phone=data.get("phone"), province=data.get("province"), church=data.get("church"), foundation=data.get("foundation"))
    db.add(m); db.commit(); db.close()
    return jsonify({"msg":"Welcome to WOI! Redirecting to WhatsApp..."})

@app.route("/donate", methods=["POST"])
def donate():
    data = request.get_json() or {}
    db = SessionLocal()
    d = Donation(name=data.get("name"), project=data.get("project"), amount=data.get("amount"), method=data.get("method"), reference=data.get("reference"))
    db.add(d); db.commit(); db.close()
    return jsonify({"msg":"Donation recorded — Thank you! Check Transparency page."})

@app.route("/order-book", methods=["POST"])
def order_book():
    data = request.get_json() or {}
    db = SessionLocal()
    b = BookOrder(name=data.get("name"), phone=data.get("phone"), book=data.get("book"), method=data.get("method"), ref=data.get("ref"))
    db.add(b); db.commit(); db.close()
    return jsonify({"msg":"Order saved — Please pay and we will confirm."})

# ADMIN
ADMIN_USER = os.environ.get("ADMIN_USER","admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS","admin123")

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username")==ADMIN_USER and request.form.get("password")==ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
        return render_template("admin_login.html", error="Wrong credentials")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")
    db = SessionLocal()
    users = db.query(User).order_by(User.created_at.desc()).all()
    members = db.query(Member).order_by(Member.created_at.desc()).all()
    donations = db.query(Donation).order_by(Donation.created_at.desc()).all()
    books = db.query(BookOrder).order_by(BookOrder.created_at.desc()).all()
    db.close()
    return render_template("admin.html", users=users, members=members, donations=donations, books=books)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin/login")

if __name__ == "__main__":
    app.run(debug=True)
