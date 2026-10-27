from flask import Flask, render_template, request, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)

def load_json(f):
    try:
        if os.path.exists(f):
            with open(f,'r') as file: return json.load(file)
    except: pass
    return []

def save_json(f,data):
    try:
        with open(f,'w') as file: json.dump(data,file,indent=2)
    except Exception as e: print(e)

def get_progress():
    donations = load_json('donations.json')
    school = sum(float(d.get('amount',0)) for d in donations if d.get('project')=='school')
    university = sum(float(d.get('amount',0)) for d in donations if d.get('project')=='university')
    clinic = sum(float(d.get('amount',0)) for d in donations if d.get('project')=='clinic')
    return {
        'school': min(100, int(school/100000*100)) if school else 12,
        'school_total': school,
        'university': min(100, int(university/80000*100)) if university else 8,
        'university_total': university,
        'clinic': min(100, int(clinic/60000*100)) if clinic else 5,
        'clinic_total': clinic
    }

@app.route('/')
def home():
    progress = get_progress()
    return render_template('index.html', progress=progress)

@app.route('/transparency')
def transparency():
    donations = load_json('donations.json')
    return render_template('transparency.html', donations=donations[::-1][:200])

@app.route('/join', methods=['POST'])
def join():
    data=request.get_json()
    members=load_json('members.json')
    members.append({**data,'date':datetime.now().strftime('%Y-%m-%d %H:%M')})
    save_json('members.json',members)
    return jsonify({'msg': f"Welcome {data.get('name')}! You joined {data.get('foundation')}. 0975826286 will WhatsApp you. See you on Transparency page!"})

@app.route('/donate', methods=['POST'])
def donate():
    data=request.get_json()
    donations=load_json('donations.json')
    donations.append({**data,'date':datetime.now().strftime('%Y-%m-%d %H:%M')})
    save_json('donations.json',donations)
    return jsonify({'msg': f"Thank you {data.get('name')}! K{data.get('amount')} saved for {data.get('project')}. Ref: {data.get('reference')}. View on /transparency."})

@app.route('/prayer', methods=['POST'])
def prayer():
    data=request.get_json()
    prayers=load_json('prayers.json')
    prayers.append({**data,'date':datetime.now().strftime('%Y-%m-%d')})
    save_json('prayers.json',prayers)
    return jsonify({'msg': 'Prayer received, we will pray for you via 0975826286!'})

@app.route('/order-book', methods=['POST'])
def order_book():
    data=request.get_json()
    orders=load_json('orders.json')
    orders.append({**data,'date':datetime.now().strftime('%Y-%m-%d')})
    save_json('orders.json',orders)
    return jsonify({'msg': f"Order {data.get('book')} received! WhatsApp 0975826286 will confirm delivery."})

@app.route('/history.html')
def history():
    try: return render_template('history.html')
    except: return "<h1>History</h1><p>Backstory from Raising a Blessed Generation book - Elfridah started WOI in 2012</p><a href='/'>Home</a>"

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))


