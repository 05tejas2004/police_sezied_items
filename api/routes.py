from flask import Blueprint, request, jsonify, g, render_template, redirect, url_for
import sqlite3
import datetime
import secrets
from database import get_db, get_all_cases, get_all_items, get_recent_items, init_db
from blockchain import Blockchain
from helpers import generate_unique_code, generate_qr_code
import config

# Create Blueprint
api = Blueprint('api', __name__)

# Initialize blockchain
police_chain = Blockchain(config.BLOCKCHAIN_FILE)

# Simple token存储 (使用session模拟)
def generate_token(username):
    """Generate a simple token"""
    return f"{username}_{secrets.token_hex(16)}"

def verify_token(token):
    """Verify if token is valid (simple check)"""
    if not token or '_' not in token:
        return False
    return True

# ================= AUTH ROUTES =================

@api.route('/login')
def login_page():
    # 如果已登录，直接跳转dashboard
    if request.args.get('token'):
        return redirect(url_for('api.dashboard'))
    return render_template('login.html')

@api.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required!'})
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user and user['password'] == password:
            # Create token
            token = generate_token(username)
            
            return jsonify({
                'success': True, 
                'message': 'Login successful!',
                'token': token,
                'user': username
            })
        
        return jsonify({'success': False, 'message': 'Invalid credentials!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ================= PAGE ROUTES =================

@api.route('/')
def index():
    return render_template('login.html')

@api.route('/dashboard')
def dashboard():
    # Check for token in query string or session
    token = request.args.get('token') or request.cookies.get('token')
    
    # Also accept from localStorage (handled in template)
    return render_template('dashboard.html')

# ================= DATA API ROUTES =================

@api.route('/api/cases', methods=['GET'])
def get_cases():
    cases = get_all_cases()
    return jsonify([{
        'id': c['id'], 
        'case_number': c['case_number'], 
        'location': c['location']
    } for c in cases])

@api.route('/api/case', methods=['POST'])
def create_case():
    data = request.json
    case_number = data.get('case_number', '').strip()
    location = data.get('location', '').strip()
    officer_name = data.get('officer_name', '').strip()
    case_date = data.get('case_date', '')
    description = data.get('description', '').strip()
    
    if not case_number or not location or not officer_name:
        return jsonify({'success': False, 'message': 'All fields required!'})
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO cases (case_number, location, officer_name, case_date, description) VALUES (?, ?, ?, ?, ?)",
            (case_number, location, officer_name, case_date, description)
        )
        db.commit()
        
        police_chain.add_block({
            "type": "CASE_REGISTERED",
            "details": {
                "case_number": case_number, 
                "location": location, 
                "officer": officer_name
            }
        })
        
        return jsonify({'success': True, 'message': 'Case registered on Blockchain!'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Case number already exists!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@api.route('/api/item', methods=['POST'])
def add_item():
    data = request.json
    case_id = data.get('case_id')
    item_name = data.get('item_name', '').strip()
    description = data.get('description', '').strip()
    quantity = data.get('quantity', '').strip()
    value = data.get('value', 0)
    condition = data.get('condition', 'New')
    
    if not case_id or not item_name:
        return jsonify({'success': False, 'message': 'Case and item name required!'})
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT case_number FROM cases WHERE id = ?", (case_id,))
    case = cursor.fetchone()
    
    if not case:
        return jsonify({'success': False, 'message': 'Case not found!'})
    
    case_number = case['case_number']
    unique_code = generate_unique_code(case_number)
    qr_image = generate_qr_code(unique_code)
    
    full_description = description
    if quantity:
        full_description = f"{quantity} | {description}"
    
    try:
        cursor.execute(
            "INSERT INTO items (case_id, item_name, description, unique_code, qr_code_image, condition, value) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, item_name, full_description, unique_code, qr_image, condition, value)
        )
        db.commit()
        
        police_chain.add_block({
            "type": "ITEM_SEIZED",
            "details": {
                "case_number": case_number, 
                "item_name": item_name, 
                "unique_code": unique_code
            }
        })
        
        return jsonify({
            'success': True, 
            'message': 'Item registered on Blockchain!', 
            'unique_code': unique_code, 
            'qr_code': qr_image
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@api.route('/api/recent-items')
def api_recent_items():
    items = get_recent_items(5)
    return jsonify([dict(row) for row in items])

@api.route('/api/all-items')
def api_all_items():
    search = request.args.get('search', '')
    case_id = request.args.get('case_id', '')
    items = get_all_items(search, case_id)
    return jsonify([dict(row) for row in items])

# ================= OTHER PAGES =================

@api.route('/case-register')
def case_register_page():
    return render_template('case_register.html')

@api.route('/item-register')
def item_register_page():
    return render_template('item_register.html')

@api.route('/items-list')
def items_list_page():
    return render_template('items_list.html')

@api.route('/stats')
def stats_page():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cases")
    total_cases = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM items")
    total_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM items WHERE created_at >= date('now')")
    today_items = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(value) FROM items")
    total_value = cursor.fetchone()[0] or 0
    
    recent_items = get_recent_items(10)
    
    return render_template('stats.html', 
                      total_cases=total_cases, 
                      total_items=total_items,
                      today_items=today_items,
                      total_value=total_value,
                      recent_items=recent_items)

@api.route('/blockchain')
def blockchain_page():
    return render_template('blockchain.html', chain=police_chain.get_chain_json())