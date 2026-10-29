from flask import Flask, render_template, request, jsonify, Response, redirect, session
import os, csv, io
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'woi-permanent-0573617784')

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'Kondwani2025')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# --- DB Setup ---
if DATABASE_URL:
    # Neon needs psycopg2
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
    from sqlalchemy.orm import declarative_base, sessionmaker
    # Fix Render url
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://','postgresql://',1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base = declarative_base()
    Session = sessionmaker(bind=engine)

    class Member(Base):
        __tablename__='members'
        id=Column(Integer,primary_key=True)
        name=Column(String); phone=Column(String); province=Column(String)
        church=Column(String); foundation=Column(String); date=Column(String)

    class Donation(Base):
        __tablename__='donations'
        id=Column(Integer,primary_key=True)
        name=Column(String); project=Column(String); amount=Column(Float)
        method=Column(String); reference=Column(String); date=Column(String)

    class Order(Base):
        __tablename__='orders'
        id=Column(Integer,primary_key=True)
        name=Column(String); phone=Column(String); book=Column(String)
        method=Column(String); ref=Column(String); date=Column(String)

    class Prayer(Base):
        __tablename__='prayers'
        id=Column(Integer,primary_key=True)
        name=Column(String); prayer=Column(Text); date=Column(String)

    Base.metadata.create_all(engine)
    USE_DB=True
else:
    USE_DB=False
    import json
    def load_json(f):
        try:
            if os.path.exists(f):
                with open(f,'r') as fh:
                    d=fh.read().strip()
                    if d: return json.loads(d)
        except: pass
        return []
    def save_json(f,d):
        try:
            with open(f,'w') as fh: json.dump(d,fh,indent=2)
        except: pass

def login_required(f):
    @wraps(f)
    def dec(*args,**kwargs):
        if not session.get('logged'): return redirect('/admin/login')
        return f(*args,**kwargs)
    return dec

def get_progress():
    if USE_DB:
        s=Session(); donations=s.query(Donation).all(); s.close()
        def tot(p): return sum(d.amount or 0 for d in donations if d.project==p)
        school, univ, clin = tot('school'), tot('university'), tot('clinic')
    else:
        donations=load_json('donations.json')
        def tot(p): return sum(float(d.get('amount',0) or 0) for d in donations if d.get('project')==p)
        school, univ, clin = tot('school'), tot('university'), tot('clinic')
        donations=donations
    return {
        'school': min(100,int(school/100000*100)) if school else 12,
        'school_total': school,
        'university': min(100,int(univ/80000*100)) if univ else 8,
        'university_total': univ,
        'clinic': min(100,int(clin/60000*100)) if clin else 5,
        'clinic_total': clin,
        'total_all': school+univ+clin,
        'count': len(donations) if 'donations' in locals() else 0
    }

@app.route('/')
def home():
    return render_template('index.html', progress=get_progress())

@app.route('/transparency')
def transparency():
    if USE_DB:
        s=Session(); donations=s.query(Donation).order_by(Donation.id.desc()).limit(200).all(); s.close()
        # convert to dict for template
        donations=[{'id':d.id,'date':d.date,'name':d.name,'project':d.project,'amount':d.amount,'method':d.method,'reference':d.reference} for d in donations]
    else:
        donations=load_json('donations.json')[::-1][:200]
    return render_template('transparency.html', donations=donations, progress=get_progress())

@app.route('/join', methods=['POST'])
def join():
    data=request.get_json() or {}
    if not data.get('name') or not data.get('phone'):
        return jsonify({'msg':'Name & Phone required'}),400
    if USE_DB:
        s=Session()
        m=Member(name=data.get('name'), phone=data.get('phone'), province=data.get('province'), church=data.get('church'), foundation=data.get('foundation'), date=datetime.now().strftime('%Y-%m-%d %H:%M'))
        s.add(m); s.commit(); s.close()
    else:
        members=load_json('members.json'); data['id']=len(members)+1; data['date']=datetime.now().strftime('%Y-%m-%d %H:%M'); members.append(data); save_json('members.json',members)
    return jsonify({'msg':f"Welcome {data.get('name')}! Joined {data.get('foundation','WOI')}. We will WhatsApp you on 0573617784."})

@app.route('/donate', methods=['POST'])
def donate():
    data=request.get_json() or {}
    if not data.get('amount'): return jsonify({'msg':'Amount required'}),400
    if USE_DB:
        s=Session()
        d=Donation(name=data.get('name'), project=data.get('project'), amount=float(data.get('amount') or 0), method=data.get('method'), reference=data.get('reference'), date=datetime.now().strftime('%Y-%m-%d %H:%M'))
        s.add(d); s.commit(); s.close()
    else:
        donations=load_json('donations.json'); data['id']=len(donations)+1; data['date']=datetime.now().strftime('%Y-%m-%d %H:%M'); donations.append(data); save_json('donations.json',donations)
    return jsonify({'msg':f"Thank you {data.get('name','Friend')}! K{data.get('amount')} saved to permanent DB. View on Transparency."})

@app.route('/order-book', methods=['POST'])
def order_book():
    data=request.get_json() or {}
    if USE_DB:
        s=Session()
        o=Order(name=data.get('name'), phone=data.get('phone'), book=data.get('book'), method=data.get('method'), ref=data.get('ref'), date=datetime.now().strftime('%Y-%m-%d %H:%M'))
        s.add(o); s.commit(); s.close()
    else:
        orders=load_json('orders.json'); data['id']=len(orders)+1; data['date']=datetime.now().strftime('%Y-%m-%d %H:%M'); orders.append(data); save_json('orders.json',orders)
    return jsonify({'msg':f"Order {data.get('book','Book')} saved permanently!"})

@app.route('/prayer', methods=['POST'])
def prayer():
    data=request.get_json() or {}
    if USE_DB:
        s=Session(); p=Prayer(name=data.get('name'), prayer=data.get('prayer'), date=datetime.now().strftime('%Y-%m-%d %H:%M')); s.add(p); s.commit(); s.close()
    else:
        prayers=load_json('prayers.json'); data['id']=len(prayers)+1; data['date']=datetime.now().strftime('%Y-%m-%d %H:%M'); prayers.append(data); save_json('prayers.json',prayers)
    return jsonify({'msg':'Prayer saved permanently!'})

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form.get('username')==ADMIN_USER and request.form.get('password')==ADMIN_PASS:
            session['logged']=True; return redirect('/admin')
        return render_template('admin_login.html', error='Wrong password')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear(); return redirect('/admin/login')

@app.route('/admin')
@login_required
def admin():
    if USE_DB:
        s=Session()
        members=[{'id':m.id,'date':m.date,'name':m.name,'phone':m.phone,'province':m.province,'church':m.church,'foundation':m.foundation} for m in s.query(Member).order_by(Member.id.desc()).all()]
        donations=[{'id':d.id,'date':d.date,'name':d.name,'project':d.project,'amount':d.amount,'method':d.method,'reference':d.reference} for d in s.query(Donation).order_by(Donation.id.desc()).all()]
        orders=[{'id':o.id,'date':o.date,'name':o.name,'phone':o.phone,'book':o.book,'method':o.method,'ref':o.ref} for o in s.query(Order).order_by(Order.id.desc()).all()]
        prayers=[{'id':p.id,'date':p.date,'name':p.name,'prayer':p.prayer} for p in s.query(Prayer).order_by(Prayer.id.desc()).all()]
        s.close()
    else:
        members=load_json('members.json')[::-1]; donations=load_json('donations.json')[::-1]; orders=load_json('orders.json')[::-1]; prayers=load_json('prayers.json')[::-1]
    return render_template('admin.html', members=members, donations=donations, orders=orders, prayers=prayers, progress=get_progress(), use_db=USE_DB)

@app.route('/admin/delete/<typ>/<int:id>')
@login_required
def admin_delete(typ,id):
    if USE_DB:
        s=Session()
        maps={'members':Member,'donations':Donation,'orders':Order,'prayers':Prayer}
        if typ in maps:
            obj=s.query(maps[typ]).filter_by(id=id).first()
            if obj: s.delete(obj); s.commit()
        s.close()
    else:
        import json
        files={'members':'members.json','donations':'donations.json','orders':'orders.json','prayers':'prayers.json'}
        if typ in files:
            data=load_json(files[typ]); data=[d for d in data if d.get('id')!=id]; save_json(files[typ],data)
    return redirect('/admin')

@app.route('/admin/export/<typ>')
@login_required
def admin_export(typ):
    if USE_DB:
        s=Session()
        maps={'members':Member,'donations':Donation,'orders':Order}
        if typ not in maps: return "Invalid",400
        objs=s.query(maps[typ]).all(); s.close()
        if not objs: return "No data",404
        si=io.StringIO(); writer=csv.writer(si)
        writer.writerow([c.name for c in maps[typ].__table__.columns])
        for o in objs: writer.writerow([getattr(o,c.name) for c in maps[typ].__table__.columns])
        return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition':f'attachment; filename={typ}.csv'})
    else:
        import json
        files={'members':'members.json','donations':'donations.json','orders':'orders.json'}
        data=load_json(files[typ]); si=io.StringIO(); writer=csv.DictWriter(si, fieldnames=data[0].keys() if data else []); writer.writeheader(); writer.writerows(data)
        return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition':f'attachment; filename={typ}.csv'})

@app.route('/history.html')
def history():
    try: return render_template('history.html')
    except: return "<h1>WOI Story 29 years</h1><a href='/'>Home</a>"

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
