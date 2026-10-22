from flask import Flask, render_template, request, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)

DONATIONS_FILE = 'donations.json'
ORDERS_FILE = 'orders.json'
PRAYERS_FILE = 'prayers.json'

GOALS = {'school': 100000, 'university': 80000, 'clinic': 60000}

# ABSA OFFICIAL
ABSA_NAME = "Women of Influence"
ABSA_NUMBER = "0000001011355"
ABSA_FULL = f"{ABSA_NAME} - {ABSA_NUMBER} - ABSA Bank Zambia"

def load_json(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def get_progress():
    donations = load_json(DONATIONS_FILE, [])
    school_total = sum(d['amount'] for d in donations if d['project'] == 'school')
    uni_total = sum(d['amount'] for d in donations if d['project'] == 'university')
    clinic_total = sum(d['amount'] for d in donations if d['project'] == 'clinic')
    school_donors = len([d for d in donations if d['project'] == 'school'])
    uni_donors = len([d for d in donations if d['project'] == 'university'])
    clinic_donors = len([d for d in donations if d['project'] == 'clinic'])
    def pct(total, goal):
        return min(int((total / goal) * 100), 100) if goal else 0
    return {
        'school': pct(school_total, GOALS['school']),
        'university': pct(uni_total, GOALS['university']),
        'clinic': pct(clinic_total, GOALS['clinic']),
        'school_total': school_total,
        'university_total': uni_total,
        'clinic_total': clinic_total,
        'school_next': max(GOALS['school'] - school_total, 0),
        'university_next': max(GOALS['university'] - uni_total, 0),
        'clinic_next': max(GOALS['clinic'] - clinic_total, 0),
        'school_donors': school_donors,
        'university_donors': uni_donors,
        'clinic_donors': clinic_donors,
    }

def get_recent():
    donations = load_json(DONATIONS_FILE, [])
    recent = sorted(donations, key=lambda x: x.get('timestamp',''), reverse=True)[:5]
    for r in recent:
        r['time'] = r.get('time_str', 'just now')
    return recent

@app.route('/')
def home():
    return render_template('index.html', progress=get_progress(), recent=get_recent())

@app.route('/events')
def events():
    return render_template('index.html', progress=get_progress(), recent=get_recent())

@app.route('/prayer', methods=['POST'])
def prayer():
    data = request.get_json()
    name = data.get('name','Anonymous')
    prayer_text = data.get('prayer','')
    prayers = load_json(PRAYERS_FILE, [])
    prayers.append({'name': name, 'prayer': prayer_text, 'timestamp': datetime.now().isoformat(), 'time_str': datetime.now().strftime('%d %b %H:%M')})
    save_json(PRAYERS_FILE, prayers)
    msg = f"🙏 Thank you {name}, your prayer request is received."
    whatsapp = f"https://wa.me/260975826286?text=New Prayer from {name}: {prayer_text[:100]}"
    return jsonify({'msg': msg, 'whatsapp': whatsapp})

@app.route('/order-book', methods=['POST'])
def order_book():
    data = request.get_json()
    orders = load_json(ORDERS_FILE, [])
    orders.append({
        'name': data.get('name',''), 'phone': data.get('phone',''),
        'book': data.get('book',''), 'method': data.get('method',f'ABSA Bank - {ABSA_NUMBER}'),
        'ref': data.get('ref',''), 'timestamp': datetime.now().isoformat(),
        'time_str': datetime.now().strftime('%d %b %H:%M')
    })
    save_json(ORDERS_FILE, orders)
    wa_text = f"New Book Order: {data.get('book')} by {data.get('name')} via {data.get('method')} Ref:{data.get('ref')}"
    return jsonify({'msg': f"✅ Order received! Paid via {data.get('method')}. We will confirm on WhatsApp.", 'whatsapp': f"https://wa.me/260975826286?text={wa_text}"})

@app.route('/donate', methods=['POST'])
def donate():
    data = request.get_json()
    name = data.get('name','Anonymous')
    project = data.get('project','school')
    amount = float(data.get('amount',0))
    method = data.get('method',f'ABSA Bank - {ABSA_NUMBER}')
    reference = data.get('reference','')
    donations = load_json(DONATIONS_FILE, [])
    if 'ABSA' in method or ABSA_NUMBER in method:
        method_display = 'ABSA Bank'
    elif 'Airtel' in method:
        method_display = 'Airtel Money'
    else:
        method_display = method
    donations.append({
        'name': name, 'project': project, 'amount': amount,
        'method': method_display, 'reference': reference,
        'timestamp': datetime.now().isoformat(),
        'time_str': datetime.now().strftime('%d %b, %H:%M')
    })
    save_json(DONATIONS_FILE, donations)
    msg = f"🎉 Thank you {name}! K{amount:.0f} for {project} via {method_display} received."
    wa_text = f"New Donation: K{amount:.0f} for {project.upper()} by {name} via {method_display} Ref:{reference} - {ABSA_FULL}"
    return jsonify({'msg': msg, 'whatsapp': f"https://wa.me/260975826286?text={wa_text}", 'progress': get_progress()})

# --- NEW ADMIN DASHBOARD WITH ABSA ---
@app.route('/admin')
def admin():
    donations = load_json(DONATIONS_FILE, [])
    orders = load_json(ORDERS_FILE, [])
    prayers = load_json(PRAYERS_FILE, [])
    progress = get_progress()
    donations_sorted = sorted(donations, key=lambda x: x.get('timestamp',''), reverse=True)
    orders_sorted = sorted(orders, key=lambda x: x.get('timestamp',''), reverse=True)
    prayers_sorted = sorted(prayers, key=lambda x: x.get('timestamp',''), reverse=True)
    return render_template('admin.html',
        absa_account=ABSA_FULL,
        absa_name=ABSA_NAME,
        absa_number=ABSA_NUMBER,
        goals=GOALS,
        progress=progress,
        total_donations=len(donations),
        total_raised=sum(d['amount'] for d in donations),
        donations=donations_sorted,
        orders=orders_sorted,
        prayers=prayers_sorted
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)