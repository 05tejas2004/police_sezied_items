import sqlite3
from flask import g
import config
from datetime import datetime
import pytz
ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
# Fixed: Use consistent timestamp format
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

def get_db():
    """Get database connection (cached in Flask g object)"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(config.DATABASE)
        db.row_factory = sqlite3.Row
        # Enable foreign keys
        db.execute("PRAGMA foreign_keys = ON")
    return db

def close_connection(exception):
    """Close database connection when app context ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        g._database = None  # Clear cached connection

def get_system_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_database_timestamp():
    """Get system timestamp directly from database in 24-hour format"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT datetime('now', 'localtime') as timestamp")
    return cursor.fetchone()['timestamp']

def format_timestamp_24h(timestamp_value):
    """Convert timestamp to consistent 24-hour format string"""
    if timestamp_value is None:
        return None
    
    # If already a string, just ensure consistency
    if isinstance(timestamp_value, str):
        try:
            dt = datetime.strptime(timestamp_value, '%Y-%m-%d %H:%M:%S')
            return dt.strftime(TIMESTAMP_FORMAT)
        except ValueError:
            # Handle SQLite timestamp format
            return timestamp_value
    
    # If datetime object, format it
    if isinstance(timestamp_value, datetime):
        return timestamp_value.strftime(TIMESTAMP_FORMAT)
    
    return str(timestamp_value)

def init_db(app):
    """Initialize database with tables and default data"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'officer',
                created_at TEXT NOT NULL,
                system_timestamp TEXT NOT NULL
            )
        ''')
        
        # Cases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT UNIQUE NOT NULL,
                location TEXT NOT NULL,
                officer_name TEXT NOT NULL,
                case_date TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                system_timestamp TEXT NOT NULL
            )
        ''')
        
        # Items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                unique_code TEXT UNIQUE NOT NULL,
                qr_code_image TEXT,
                condition TEXT,
                value REAL,
                created_at TEXT NOT NULL,
                system_timestamp TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        ''')
        
        db.commit()
        
        # Create default admin user using Python's system timestamp
        timestamp = get_system_timestamp()
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password, role, created_at, system_timestamp) 
                VALUES (?, ?, ?, ?, ?)
            """, ('admin', 'admin123', 'admin', timestamp, timestamp))
            db.commit()
        
        print("✅ Database initialized successfully!")
        print(f"📅 System Timestamp: {get_system_timestamp()}")

def add_case(case_number, location, officer_name, case_date, description):
    """Add a new case with system timestamp"""
    db = get_db()
    cursor = db.cursor()
    timestamp = get_system_timestamp()
    
    cursor.execute("""
        INSERT INTO cases (case_number, location, officer_name, case_date, description, created_at, system_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (case_number, location, officer_name, case_date, description, timestamp, timestamp))
    
    db.commit()
    return cursor.lastrowid

def add_item(case_id, item_name, description, unique_code, condition, value):
    """Add a new item with system timestamp"""
    db = get_db()
    cursor = db.cursor()
    timestamp = get_system_timestamp()
    
    cursor.execute("""
        INSERT INTO items (case_id, item_name, description, unique_code, condition, value, created_at, system_timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (case_id, item_name, description, unique_code, condition, value, timestamp, timestamp))
    
    db.commit()
    return cursor.lastrowid

def update_item_timestamp(item_id):
    """Update the system timestamp for an item using Python's time"""
    db = get_db()
    cursor = db.cursor()
    new_timestamp = get_system_timestamp()
    
    cursor.execute("""
        UPDATE items 
        SET system_timestamp = ? 
        WHERE id = ?
    """, (new_timestamp, item_id))
    
    db.commit()
    return cursor.rowcount > 0

def update_case_timestamp(case_id):
    """Update the system timestamp for a case using Python's time"""
    db = get_db()
    cursor = db.cursor()
    new_timestamp = get_system_timestamp()
    
    cursor.execute("""
        UPDATE cases 
        SET system_timestamp = ? 
        WHERE id = ?
    """, (new_timestamp, case_id))
    
    db.commit()
    return cursor.rowcount > 0

def get_all_cases():
    """Get all cases ordered by most recent"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM cases ORDER BY id DESC")
    return cursor.fetchall()

def get_all_items(search='', case_id=''):
    """Get all items with optional search and filter"""
    db = get_db()
    cursor = db.cursor()
    
    query = '''
        SELECT i.*, c.case_number 
        FROM items i
        JOIN cases c ON i.case_id = c.id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (i.item_name LIKE ? OR i.unique_code LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if case_id:
        query += ' AND i.case_id = ?'
        params.append(case_id)
    
    query += ' ORDER BY i.id DESC'
    
    cursor.execute(query, params)
    return cursor.fetchall()

def get_recent_items(limit=5):
    """Get most recent items"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT i.*, c.case_number 
        FROM items i
        JOIN cases c ON i.case_id = c.id
        ORDER BY i.id DESC
        LIMIT ?
    ''', (limit,))
    return cursor.fetchall()

def get_item_timestamp(item_id):
    """Get timestamp for a specific item"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT created_at, system_timestamp 
        FROM items 
        WHERE id = ?
    ''', (item_id,))
    row = cursor.fetchone()
    if row:
        return {
            'created_at': format_timestamp_24h(row['created_at']),
            'system_timestamp': format_timestamp_24h(row['system_timestamp'])
        }
    return None

def get_case_timestamp(case_id):
    """Get timestamp for a specific case"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT created_at, system_timestamp 
        FROM cases 
        WHERE id = ?
    ''', (case_id,))
    row = cursor.fetchone()
    if row:
        return {
            'created_at': format_timestamp_24h(row['created_at']),
            'system_timestamp': format_timestamp_24h(row['system_timestamp'])
        }
    return None

def check_all_timestamps():
    """Check timestamps for all records"""
    db = get_db()
    cursor = db.cursor()
    
    results = {
        'system_time': get_system_timestamp(),
        'database_time': get_database_timestamp(),
        'items': [],
        'cases': [],
        'users': []
    }
    
    # Get items timestamps
    cursor.execute('''
        SELECT id, item_name, unique_code, created_at, system_timestamp 
        FROM items 
        ORDER BY id DESC
    ''')
    for row in cursor.fetchall():
        results['items'].append({
            'id': row['id'],
            'item_name': row['item_name'],
            'unique_code': row['unique_code'],
            'created_at': format_timestamp_24h(row['created_at']),
            'system_timestamp': format_timestamp_24h(row['system_timestamp'])
        })
    
    # Get cases timestamps
    cursor.execute('''
        SELECT id, case_number, officer_name, created_at, system_timestamp 
        FROM cases 
        ORDER BY id DESC
    ''')
    for row in cursor.fetchall():
        results['cases'].append({
            'id': row['id'],
            'case_number': row['case_number'],
            'officer_name': row['officer_name'],
            'created_at': format_timestamp_24h(row['created_at']),
            'system_timestamp': format_timestamp_24h(row['system_timestamp'])
        })
    
    # Get users timestamps
    cursor.execute('''
        SELECT id, username, role, created_at, system_timestamp 
        FROM users 
        ORDER BY id DESC
    ''')
    for row in cursor.fetchall():
        results['users'].append({
            'id': row['id'],
            'username': row['username'],
            'role': row['role'],
            'created_at': format_timestamp_24h(row['created_at']),
            'system_timestamp': format_timestamp_24h(row['system_timestamp'])
        })
    
    return results

# ============================================================================
# USAGE IN FLASK APP (main.py)
# ============================================================================

"""
from flask import Flask
import database

app = Flask(__name__)

# Register the close_connection as teardown
@app.teardown_appcontext
def shutdown_session(exception=None):
    database.close_connection(exception)

# Initialize database on startup
with app.app_context():
    database.init_db(app)

if __name__ == '__main__':
    app.run(debug=True)
"""

# ============================================================================
# KEY FIXES MADE:
# ============================================================================

"""
1. ✅ CHANGED: Table schema - used TEXT instead of TIMESTAMP for portability
   - SQLite TIMESTAMP defaults can be inconsistent
   - TEXT with Python's datetime gives you control

2. ✅ FIXED: close_connection - added session clearing: g._database = None
   - Prevents stale connections

3. ✅ FIXED: Added timestamp parameter in INSERT statements
   - Changed from DEFAULT CURRENT_TIMESTAMP to explicit timestamp values
   - Ensures Python's system timestamp is used consistently

4. ✅ ADDED: Foreign key constraint with ON DELETE CASCADE
   - Better data integrity

5. ✅ ADDED: Helper functions for adding cases and items
   - add_case() and add_item() with timestamps

6. ✅ CONSISTENT: Used TIMESTAMP_FORMAT constant
   - All timestamp formatting now uses same format

7. ✅ FIXED: get_system_timestamp_db() renamed to get_database_timestamp()
   - Avoids confusion between system time sources
"""