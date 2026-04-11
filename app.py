from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sqlite3
import uuid
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())

# ⚡ تعديل لـ Render: استخدام المسار الدائم إذا كان متوفراً
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Render Persistent Disk path (إذا كان متوفراً)
RENDER_DISK = os.environ.get('RENDER_DISK_PATH', '/opt/render/project/src')
if os.path.exists(RENDER_DISK):
    DATA_DIR = os.path.join(RENDER_DISK, 'data')
else:
    DATA_DIR = BASE_DIR

os.makedirs(DATA_DIR, exist_ok=True)

UPLOAD_FOLDER = os.path.join(DATA_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ⚡ مسار قاعدة البيانات في القرص الدائم
DB_PATH = os.path.join(DATA_DIR, 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            img TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            stock INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            shipping_type TEXT DEFAULT 'free',
            shipping_price REAL DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            UNIQUE(user_email, product_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            card_img TEXT NOT NULL,
            items_details TEXT NOT NULL,
            total_price REAL NOT NULL,
            shipping_total REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP,
            delivered INTEGER DEFAULT 0,
            delivery_review TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            review_img TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            review TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول سجل الدخول
    c.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    ADMIN_EMAIL = "qwerasdf1234598760@gmail.com"
    ADMIN_PASS = "qaws54321"
    
    hashed = generate_password_hash(ADMIN_PASS)
    
    try:
        c.execute("DELETE FROM users WHERE email=?", (ADMIN_EMAIL,))
        c.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", 
                  (ADMIN_EMAIL, hashed))
    except:
        pass
    
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        flash('نوع الملف غير مسموح', 'error')
        return None
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filename

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');
    
    :root {
        --primary: #1b5e20;
        --primary-light: #4caf50;
        --primary-dark: #0d3312;
        --accent: #2e7d32;
        --gold: #81c784;
        --bg: #f8faf8;
        --card: #ffffff;
        --text: #1a1a1a;
        --text-light: #666666;
        --border: #e0ece0;
        --success: #4caf50;
        --error: #e53935;
        --warning: #fb8c00;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
        --shadow-lg: 0 8px 40px rgba(0,0,0,0.12);
        --radius-sm: 12px;
        --radius-md: 16px;
        --radius-lg: 24px;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
        font-family: 'Tajawal', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg);
        direction: rtl;
        color: var(--text);
        padding-bottom: 80px;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
    }
    
    .flash-messages {
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        width: 90%;
        max-width: 400px;
    }
    .flash {
        padding: 14px 24px;
        border-radius: var(--radius-md);
        margin-bottom: 10px;
        text-align: center;
        font-weight: 600;
        font-size: 14px;
        box-shadow: var(--shadow-lg);
        animation: slideDown 0.3s ease;
    }
    @keyframes slideDown {
        from { opacity: 0; transform: translate(-50%, -20px); }
        to { opacity: 1; transform: translate(-50%, 0); }
    }
    .flash.success { background: var(--success); color: white; }
    .flash.error { background: var(--error); color: white; }
    .flash.warning { background: var(--warning); color: white; }
    
    header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        padding: 20px;
        text-align: center;
        position: sticky;
        top: 0;
        z-index: 1000;
        box-shadow: var(--shadow-md);
    }
    .logo {
        font-size: 26px;
        font-weight: 800;
        color: white;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .user-info {
        color: rgba(255,255,255,0.85);
        font-size: 12px;
        margin-top: 6px;
        font-weight: 500;
    }
    
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(255,255,255,0.95);
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: space-around;
        padding: 12px 0 8px;
        border-top: 1px solid var(--border);
        z-index: 1000;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.06);
    }
    .nav-item {
        color: var(--text-light);
        text-decoration: none;
        font-size: 11px;
        font-weight: 600;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        padding: 8px 16px;
        border-radius: var(--radius-md);
        transition: all 0.3s;
    }
    .nav-item:hover { color: var(--primary); }
    .nav-item.active {
        color: var(--primary);
        background: rgba(76, 175, 80, 0.1);
    }
    .nav-icon { font-size: 22px; }
    
    .container {
        padding: 16px;
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        max-width: 600px;
        margin: 0 auto;
    }
    
    .card {
        background: var(--card);
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
        transition: all 0.3s;
    }
    .card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
    .card:active { transform: scale(0.98); }
    .card img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    }
    .card-body { padding: 14px; }
    .product-title {
        font-size: 13px;
        font-weight: 600;
        color: var(--text);
        height: 40px;
        overflow: hidden;
        line-height: 1.5;
        margin-bottom: 10px;
    }
    .price {
        color: var(--primary);
        font-weight: 800;
        font-size: 16px;
    }
    
    .btn {
        border: none;
        padding: 12px 20px;
        border-radius: var(--radius-sm);
        font-weight: 700;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        font-size: 14px;
        font-family: inherit;
        transition: all 0.3s;
    }
    .btn-primary {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(27, 94, 32, 0.3);
    }
    .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(27, 94, 32, 0.4); }
    .btn-primary:active { transform: scale(0.98); }
    .btn-outline {
        background: transparent;
        color: var(--primary);
        border: 2px solid var(--primary);
    }
    .btn-outline:hover { background: var(--bg); }
    .btn-block { width: 100%; margin-top: 12px; }
    .btn-sm { padding: 8px 14px; font-size: 12px; }
    .btn-danger {
        background: linear-gradient(135deg, #e53935 0%, #c62828 100%);
        color: white;
    }
    
    .cat-bar {
        display: flex;
        overflow-x: auto;
        padding: 16px;
        gap: 10px;
        background: white;
        border-bottom: 1px solid var(--border);
        scrollbar-width: none;
    }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-item {
        background: var(--bg);
        color: var(--text-light);
        padding: 10px 20px;
        border-radius: 25px;
        text-decoration: none;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
        border: 2px solid transparent;
        transition: all 0.3s;
    }
    .cat-item:hover { border-color: var(--primary-light); color: var(--primary); }
    .cat-item.active {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(27, 94, 32, 0.3);
    }
    
    .form-group { margin-bottom: 20px; }
    label {
        display: block;
        margin-bottom: 8px;
        color: var(--text);
        font-size: 14px;
        font-weight: 600;
    }
    input, select, textarea {
        width: 100%;
        padding: 14px 16px;
        background: white;
        border: 2px solid var(--border);
        color: var(--text);
        border-radius: var(--radius-sm);
        font-family: inherit;
        font-size: 15px;
        transition: all 0.3s;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 4px rgba(76, 175, 80, 0.1);
    }
    
    .order-card {
        background: white;
        padding: 20px;
        border-radius: var(--radius-md);
        margin-bottom: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .order-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }
    .order-id { font-weight: 700; color: var(--primary); font-size: 15px; }
    .badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-pending { background: #fff3e0; color: #e65100; }
    .badge-approved { background: #e8f5e9; color: var(--primary); }
    .badge-rejected { background: #ffebee; color: var(--error); }
    
    .cart-item {
        display: flex;
        gap: 14px;
        background: white;
        padding: 16px;
        border-radius: var(--radius-md);
        margin-bottom: 12px;
        border: 1px solid var(--border);
        align-items: center;
        box-shadow: var(--shadow-sm);
    }
    .cart-item img {
        width: 70px;
        height: 70px;
        object-fit: cover;
        border-radius: var(--radius-sm);
        background: var(--bg);
    }
    
    .empty-state {
        text-align: center;
        padding: 80px 20px;
        color: var(--text-light);
    }
    .empty-state-icon { font-size: 72px; margin-bottom: 20px; opacity: 0.4; }
    
    .admin-section {
        background: white;
        padding: 24px;
        border-radius: var(--radius-md);
        margin-bottom: 20px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .admin-section h3 {
        color: var(--primary);
        margin-bottom: 20px;
        font-size: 18px;
        font-weight: 700;
    }
    
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: var(--bg); color: var(--primary); padding: 14px; font-weight: 700; }
    td { border-bottom: 1px solid var(--border); padding: 14px; }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: var(--radius-md);
        text-align: center;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .stat-number { font-size: 28px; font-weight: 800; color: var(--primary); }
    .stat-label { font-size: 12px; color: var(--text-light); margin-top: 6px; font-weight: 600; }
    
    .receipt-img {
        max-width: 100%;
        border-radius: var(--radius-md);
        border: 2px solid var(--border);
        margin-top: 16px;
    }
    
    .success-page { text-align: center; padding: 60px 20px; }
    .success-icon { font-size: 90px; margin-bottom: 24px; }
    .success-title { color: var(--success); font-size: 28px; margin-bottom: 16px; font-weight: 800; }
    
    .review-img {
        max-width: 100%;
        border-radius: var(--radius-sm);
        margin-top: 10px;
        border: 1px solid var(--border);
    }
    
    .delivery-track {
        background: #e8e8e8;
        height: 50px;
        border-radius: 25px;
        position: relative;
        margin: 20px 0;
        overflow: hidden;
        border: 2px solid var(--border);
    }
    
    .delivery-truck {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 28px;
        transition: all 1s linear;
        z-index: 10;
    }
    
    .track-line {
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        height: 4px;
        background: linear-gradient(90deg, var(--primary-light), var(--primary));
        border-radius: 2px;
        transition: width 1s linear;
    }
    
    .delivery-info {
        text-align: center;
        color: var(--text-light);
        font-size: 13px;
        margin-top: 10px;
        font-weight: 600;
    }
    
    .delivery-complete-box {
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
        color: white;
        padding: 24px;
        border-radius: var(--radius-md);
        text-align: center;
        margin: 20px 0;
        box-shadow: var(--shadow-md);
        animation: slideDown 0.5s ease;
    }
    
    .review-delivery-form {
        background: rgba(255,255,255,0.95);
        padding: 20px;
        border-radius: var(--radius-md);
        margin-top: 16px;
    }
    
    .truck-moving {
        animation: bounce 0.6s infinite alternate;
    }
    
    @keyframes bounce {
        from { transform: translateY(-50%) translateY(0); }
        to { transform: translateY(-50%) translateY(-4px); }
    }
    
    .admin-container {
        max-width: 100%;
        margin: 0 auto;
        padding: 12px;
    }
    
    .admin-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 20px;
        border-radius: var(--radius-md);
        margin-bottom: 16px;
        box-shadow: var(--shadow-md);
    }
    
    .admin-header h1 {
        font-size: 22px;
        margin-bottom: 4px;
        font-weight: 800;
    }
    
    .admin-header p {
        opacity: 0.9;
        font-size: 13px;
        font-weight: 500;
    }
    
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 16px;
    }
    
    .dashboard-card {
        background: white;
        border-radius: var(--radius-md);
        padding: 16px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }
    
    .dashboard-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-bottom: 10px;
    }
    
    .dashboard-card.primary .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.warning .dashboard-icon { background: #fff3e0; }
    .dashboard-card.success .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.info .dashboard-icon { background: #e3f2fd; }
    
    .dashboard-number {
        font-size: 24px;
        font-weight: 800;
        color: var(--text);
        margin-bottom: 2px;
    }
    
    .dashboard-label {
        color: var(--text-light);
        font-size: 11px;
        font-weight: 600;
    }
    
    .admin-section-new {
        background: white;
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }
    
    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--bg);
    }
    
    .section-title {
        font-size: 16px;
        font-weight: 700;
        color: var(--primary);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .btn-modern {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        padding: 10px 16px;
        border-radius: var(--radius-sm);
        font-weight: 700;
        cursor: pointer;
        transition: all 0.3s;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
    }
    
    .btn-modern:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(27, 94, 32, 0.3);
    }
    
    .btn-modern.secondary {
        background: white;
        color: var(--primary);
        border: 2px solid var(--primary);
    }
    
    .btn-modern.secondary:hover {
        background: var(--bg);
    }
    
    .btn-modern.danger {
        background: linear-gradient(135deg, #e53935 0%, #c62828 100%);
    }
    
    .btn-modern.small {
        padding: 6px 12px;
        font-size: 11px;
    }
    
    .orders-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 12px;
    }
    
    .orders-table th {
        background: var(--bg);
        color: var(--primary);
        font-weight: 700;
        padding: 12px 8px;
        text-align: right;
        font-size: 11px;
    }
    
    .orders-table th:first-child { border-radius: 0 10px 10px 0; }
    .orders-table th:last-child { border-radius: 10px 0 0 10px; }
    
    .orders-table td {
        padding: 12px 8px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 6px 10px;
        border-radius: 15px;
        font-size: 10px;
        font-weight: 700;
    }
    
    .status-pending { background: #fff3e0; color: #e65100; }
    .status-approved { background: #e8f5e9; color: var(--primary); }
    .status-rejected { background: #ffebee; color: #c62828; }
    
    .product-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }
    
    .product-card-admin {
        background: white;
        border-radius: var(--radius-md);
        overflow: hidden;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    
    .product-img-admin {
        width: 100%;
        height: 120px;
        object-fit: cover;
    }
    
    .product-info-admin {
        padding: 12px;
    }
    
    .product-name-admin {
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 6px;
        color: var(--text);
        height: 36px;
        overflow: hidden;
    }
    
    .product-meta-admin {
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: var(--text-light);
        font-size: 11px;
        margin-bottom: 10px;
    }
    
    .product-price-admin {
        color: var(--primary);
        font-weight: 800;
        font-size: 15px;
    }
    
    .form-modern {
        display: grid;
        gap: 14px;
    }
    
    .form-grid-2 {
        display: grid;
        grid-template-columns: 1fr;
        gap: 14px;
    }
    
    @media (min-width: 640px) {
        .form-grid-2 { grid-template-columns: 1fr 1fr; }
        .product-grid { grid-template-columns: repeat(3, 1fr); }
        .dashboard-grid { grid-template-columns: repeat(4, 1fr); }
        .admin-container { max-width: 1200px; padding: 20px; }
        .admin-header { padding: 24px; }
        .admin-header h1 { font-size: 26px; }
        .admin-section-new { padding: 24px; }
        .section-title { font-size: 18px; }
    }
    
    .form-group-modern {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .form-group-modern label {
        font-weight: 700;
        color: var(--text);
        font-size: 13px;
    }
    
    .form-control-modern {
        padding: 12px 14px;
        border: 2px solid var(--border);
        border-radius: var(--radius-sm);
        font-size: 14px;
        transition: all 0.3s;
        background: white;
        width: 100%;
    }
    
    .form-control-modern:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
    }
    
    .tabs-container {
        display: flex;
        gap: 6px;
        margin-bottom: 16px;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0;
        overflow-x: auto;
        scrollbar-width: none;
    }
    
    .tabs-container::-webkit-scrollbar { display: none; }
    
    .tab-btn {
        padding: 10px 14px;
        background: none;
        border: none;
        color: var(--text-light);
        font-weight: 700;
        cursor: pointer;
        position: relative;
        transition: all 0.3s;
        font-size: 12px;
        white-space: nowrap;
    }
    
    .tab-btn.active {
        color: var(--primary);
    }
    
    .tab-btn.active::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--primary);
        border-radius: 3px 3px 0 0;
    }
    
    .tab-content {
        display: none;
    }
    
    .tab-content.active {
        display: block;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .category-tag {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        background: var(--bg);
        border-radius: 15px;
        font-size: 11px;
        color: var(--primary);
        font-weight: 600;
    }
    
    .review-card-admin {
        background: linear-gradient(135deg, #f8f8f8 0%, #ffffff 100%);
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 12px;
        border-right: 3px solid var(--primary);
        box-shadow: var(--shadow-sm);
    }
    
    .review-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .reviewer-name {
        font-weight: 700;
        color: var(--primary);
        font-size: 13px;
    }
    
    .review-date {
        font-size: 11px;
        color: var(--text-light);
    }
    
    .review-text {
        color: var(--text);
        line-height: 1.6;
        font-size: 13px;
    }
    
    .order-id-badge {
        background: var(--primary);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 11px;
    }
    
    .premium-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #ffd700 0%, #ffaa00 100%);
        color: #333;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(255, 170, 0, 0.3);
    }
    
    .shipping-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: 700;
    }
    
    .shipping-free {
        background: #e8f5e9;
        color: var(--primary);
    }
    
    .shipping-paid {
        background: #fff3e0;
        color: #e65100;
    }
    
    .radio-group {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
    }
    
    .radio-option {
        flex: 1;
        padding: 16px;
        border: 2px solid var(--border);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all 0.3s;
        text-align: center;
    }
    
    .radio-option:hover {
        border-color: var(--primary-light);
    }
    
    .radio-option.selected {
        border-color: var(--primary);
        background: rgba(76, 175, 80, 0.05);
    }
    
    .radio-option input {
        display: none;
    }
    
    .radio-label {
        font-weight: 700;
        font-size: 14px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }
    
    .radio-icon {
        font-size: 24px;
    }
    
    .shipping-price-input {
        display: none;
    }
    
    .shipping-price-input.show {
        display: block;
        animation: slideDown 0.3s ease;
    }
    
    /* أنماط سجل الدخول */
    .login-log-card {
        background: white;
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        position: relative;
    }
    
    .log-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }
    
    .log-time {
        font-size: 12px;
        color: var(--text-light);
        font-weight: 600;
    }
    
    .log-details {
        display: grid;
        gap: 10px;
    }
    
    .log-row {
        display: flex;
        align-items: center;
        gap: 10px;
        background: var(--bg);
        padding: 10px;
        border-radius: var(--radius-sm);
    }
    
    .log-label {
        font-size: 12px;
        color: var(--text-light);
        font-weight: 700;
        min-width: 80px;
    }
    
    .log-value {
        flex: 1;
        font-family: monospace;
        font-size: 13px;
        color: var(--text);
        font-weight: 600;
        word-break: break-all;
    }
    
    .eye-btn {
        background: var(--primary);
        color: white;
        border: none;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        transition: all 0.3s;
    }
    
    .eye-btn:hover {
        background: var(--primary-dark);
        transform: scale(1.1);
    }
    
    .hidden-text {
        filter: blur(4px);
        user-select: none;
    }
    
    @media (min-width: 768px) {
        .container { grid-template-columns: repeat(3, 1fr); max-width: 900px; }
    }
</style>
"""

BASE_HTML = """<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
    {css}
    <title>{title} | THAWANI</title>
</head>
<body>
    {flash}
    {content}
    {nav}
</body>
</html>"""

def render_page(title, content, show_nav=True):
    flash_html = ""
    if 'flash_messages' in session:
        flash_html = '<div class="flash-messages">' + ''.join([
            f'<div class="flash {m["type"]}">{m["text"]}</div>' 
            for m in session.pop('flash_messages')
        ]) + '</div>'
        session.modified = True
    
    nav_html = ""
    if show_nav and 'user' in session:
        items = [('/', 'الرئيسية', '🏠'), ('/cart', 'السلة', '🛒'), ('/orders', 'طلباتي', '📦')]
        if session.get('is_admin'):
            items.append(('/admin', 'التحكم', '⚙️'))
        items.append(('/logout', 'خروج', '🚪'))
        
        nav_html = '<div class="bottom-nav">' + ''.join([
            f'<a href="{p}" class="nav-item {"active" if request.path==p else ""}"><span class="nav-icon">{i}</span><span>{n}</span></a>'
            for p, n, i in items
        ]) + '</div>'
    
    return BASE_HTML.format(css=CSS, title=title, flash=flash_html, content=content, nav=nav_html)

@app.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'الكل')
    conn = get_db()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    
    if cat == 'الكل':
        prods = conn.execute("SELECT * FROM products WHERE is_active=1").fetchall()
    else:
        prods = conn.execute("SELECT * FROM products WHERE is_active=1 AND category=?", (cat,)).fetchall()
    
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_email=?", (session['user'],)).fetchone()[0] or 0
    conn.close()
    
    html_cats = ''
    for c in cats:
        active_class = 'active' if cat == c['name'] else ''
        html_cats += f'<a href="/?cat={c["name"]}" class="cat-item {active_class}">{c["name"]}</a>'
    
    html_prods = ''
    if prods:
        for p in prods:
            if p['shipping_type'] == 'free':
                shipping_html = '<span class="shipping-badge shipping-free">🚚 مجاني</span>'
            else:
                shipping_html = f'<span class="shipping-badge shipping-paid">🚚 {p["shipping_price"]:.3f} OMR</span>'
            html_prods += f'''
            <div class="card">
                <img src="/static/uploads/{p["img"]}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e8f5e9%22 width=%22100%22 height=%22100%22/></svg>'">
                <div class="card-body">
                    <div class="product-title">{p["name"]}</div>
                    <div style="margin-bottom: 8px;">{shipping_html}</div>
                    <div class="price">{p["price"]:.3f} OMR</div>
                    <a href="/product/{p["id"]}" class="btn btn-primary btn-block">التفاصيل</a>
                </div>
            </div>
            '''
    else:
        html_prods = '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد منتجات</h3></div>'
    
    user_type = '👑 أدمن' if session.get('is_admin') else '👤 عميل'
    
    return render_template_string(render_page('الرئيسية', f"""
    <header>
        <div class="logo">THAWANI</div>
        <div class="user-info">{session['user'].split('@')[0]} | السلة: {cart_count} | {user_type}</div>
    </header>
    <div class="cat-bar">
        <a href="/" class="cat-item {'active' if cat=='الكل' else ''}">الكل</a>
        {html_cats}
    </div>
    <div class="container">
        {html_prods}
    </div>
    """))

@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def product(id):
    conn = get_db()
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()
        review_img = request.files.get('review_img')
        
        img_filename = None
        if review_img and review_img.filename:
            img_filename = save_upload(review_img)
        
        if comment:
            conn.execute(
                "INSERT INTO reviews (product_id, user_email, rating, comment, review_img) VALUES (?,?,?,?,?)",
                (id, session['user'], rating, comment, img_filename)
            )
            conn.commit()
        return redirect(f'/product/{id}')
    
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    revs = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    
    if p['shipping_type'] == 'free':
        shipping_html = '<span class="shipping-badge shipping-free" style="font-size: 13px; padding: 6px 12px;">🚚 شحن مجاني</span>'
    else:
        shipping_html = f'<span class="shipping-badge shipping-paid" style="font-size: 13px; padding: 6px 12px;">🚚 تكلفة الشحن: {p["shipping_price"]:.3f} OMR</span>'
    
    html_revs = ''
    for r in revs:
        stars = '★' * r['rating'] + '☆' * (5 - r['rating'])
        img_html = ''
        if r['review_img']:
            img_html = f'<img src="/static/uploads/{r["review_img"]}" class="review-img" onclick="window.open(this.src)">'
        html_revs += f'''
        <div style="background:white; padding:16px; border-radius:var(--radius-md); margin-bottom:12px; border:1px solid var(--border); box-shadow: var(--shadow-sm);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="color:var(--primary); font-size: 16px; letter-spacing: 2px;">{stars}</div>
                <span style="font-size: 12px; color: var(--text-light); font-weight: 600;">{r["user_email"][:15]}...</span>
            </div>
            <p style="font-size:14px; line-height: 1.6; color: var(--text);">{r["comment"]}</p>
            {img_html}
            <div style="color:var(--text-light); font-size:11px; margin-top: 10px; font-weight: 500;">{r["created_at"][:16]}</div>
        </div>
        '''
    
    return render_template_string(render_page('المنتج', f"""
    <header><div class="logo">تفاصيل المنتج</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        <div style="position: relative; margin-bottom: 20px;">
            <img src="/static/uploads/{p['img']}" style="width:100%; border-radius:var(--radius-lg); box-shadow: var(--shadow-md);">
            <div class="premium-badge" style="position: absolute; top: 12px; right: 12px;">
                ⭐ مميز
            </div>
        </div>
        <h2 style="color:var(--primary); margin-bottom:10px; font-size: 24px; font-weight: 800;">{p['name']}</h2>
        <div style="margin-bottom: 16px;">{shipping_html}</div>
        <div class="price" style="font-size:28px; margin-bottom:16px; font-weight: 800;">{p['price']:.3f} <span style="font-size: 16px; color: var(--text-light);">OMR</span></div>
        <p style="color:var(--text-light); margin-bottom:24px; line-height: 1.8; font-size: 15px;">{p['description'] or 'لا يوجد وصف'}</p>
        <div style="display: flex; gap: 12px; margin-bottom: 30px;">
            <a href="/add_to_cart/{p['id']}" class="btn btn-primary btn-block" style="flex: 2; padding: 16px; font-size: 16px;">أضف للسلة 🛒</a>
        </div>
        
        <div style="margin-top: 30px;">
            <h3 style="margin-bottom: 20px; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                <span>التقييمات</span>
                <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 15px; font-size: 13px;">{len(revs)}</span>
            </h3>
            {html_revs}
            
            <form method="POST" enctype="multipart/form-data" style="margin-top: 24px; background: white; padding: 20px; border-radius: var(--radius-md); border: 2px solid var(--border);">
                <h4 style="margin-bottom: 16px; color: var(--primary); font-weight: 700;">✍️ أضف تقييمك</h4>
                <div class="form-group">
                    <select name="rating" class="form-control-modern" style="width: auto;">
                        <option value="5">⭐⭐⭐⭐⭐ (ممتاز)</option>
                        <option value="4">⭐⭐⭐⭐ (جيد جداً)</option>
                        <option value="3">⭐⭐⭐ (جيد)</option>
                        <option value="2">⭐⭐ (مقبول)</option>
                        <option value="1">⭐ (ضعيف)</option>
                    </select>
                </div>
                <div class="form-group">
                    <textarea name="comment" placeholder="اكتب رأيك في المنتج..." rows="3" required class="form-control-modern"></textarea>
                </div>
                <div class="form-group">
                    <label style="font-size: 13px; color: var(--text-light);">📷 إرفاق صورة (اختياري)</label>
                    <input type="file" name="review_img" accept="image/*" class="form-control-modern" style="padding: 12px;">
                </div>
                <button class="btn btn-primary btn-block" style="padding: 14px;">نشر التقييم</button>
            </form>
        </div>
    </div>
    """))

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    conn = get_db()
    item = conn.execute("SELECT id, quantity FROM cart WHERE user_email=? AND product_id=?", 
                       (session['user'], id)).fetchone()
    if item:
        conn.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (item['id'],))
    else:
        conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
    conn.commit()
    conn.close()
    return redirect('/cart')

@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    items = conn.execute('''
        SELECT p.id, p.name, p.price, p.img, p.shipping_type, p.shipping_price, c.quantity 
        FROM cart c JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    total = 0
    shipping_total = 0
    for i in items:
        total += i['price'] * i['quantity']
        if i['shipping_type'] == 'paid':
            shipping_total += i['shipping_price'] * i['quantity']
    
    conn.close()
    
    html_items = ''
    if items:
        for i in items:
            if i['shipping_type'] == 'free':
                shipping_text = '🚚 مجاني'
            else:
                shipping_text = f'🚚 {i["shipping_price"]:.3f} OMR'
            html_items += f'''
            <div class="cart-item">
                <img src="/static/uploads/{i["img"]}">
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:15px; margin-bottom: 4px;">{i["name"]}</div>
                    <div style="color:var(--primary); font-size:14px; font-weight: 600;">{i["price"]:.3f} OMR × {i["quantity"]}</div>
                    <div style="font-size: 12px; color: var(--text-light); margin-top: 4px;">{shipping_text}</div>
                </div>
                <div style="text-align:left;">
                    <div style="font-weight:800; font-size: 16px; color: var(--text); margin-bottom: 8px;">{(i["price"]*i["quantity"]):.3f}</div>
                    <a href="/remove_from_cart/{i["id"]}" class="btn btn-sm" style="color:var(--error); font-weight: 600; padding: 6px 12px;">🗑️ حذف</a>
                </div>
            </div>
            '''
        
        grand_total = total + shipping_total
        
        shipping_breakdown = ''
        if shipping_total > 0:
            shipping_breakdown = f'<div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size: 14px; color: var(--text-light);"><span>الشحن:</span><span>{shipping_total:.3f} OMR</span></div>'
        
        checkout_html = f'''
        <div style="background:white; padding:20px; border-radius:var(--radius-md); margin-top:20px; box-shadow: var(--shadow-md); border: 2px solid var(--border);">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size: 14px;">
                <span>المجموع:</span>
                <span style="font-weight: 700;">{total:.3f} OMR</span>
            </div>
            {shipping_breakdown}
            <div style="border-top:2px solid var(--border); margin-top:16px; padding-top:16px; display:flex; justify-content:space-between; align-items: center;">
                <span style="font-size: 16px; font-weight: 700;">الإجمالي:</span>
                <b style="color:var(--primary); font-size:26px; font-weight: 800;">{grand_total:.3f} <span style="font-size: 14px;">OMR</span></b>
            </div>
            <a href="/checkout" class="btn btn-primary btn-block" style="padding: 16px; font-size: 16px; margin-top: 16px;">إتمام الطلب ➡️</a>
        </div>
        '''
    else:
        html_items = '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3>السلة فارغة</h3><p style="margin-top: 10px; font-size: 14px;">تصفح المنتجات وأضف ما تحب</p><a href="/" class="btn btn-primary" style="margin-top: 20px;">تصفح المنتجات</a></div>'
        checkout_html = ''
    
    return render_template_string(render_page('السلة', f"""
    <header><div class="logo">سلة التسوق</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {html_items}
        {checkout_html}
    </div>
    """))

@app.route('/remove_from_cart/<int:pid>')
@login_required
def remove_from_cart(pid):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE user_email=? AND product_id=?", (session['user'], pid))
    conn.commit()
    conn.close()
    return redirect('/cart')

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    conn = get_db()
    items = conn.execute('''
        SELECT p.name, p.price, p.shipping_type, p.shipping_price, c.quantity 
        FROM cart c JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    if not items:
        conn.close()
        return redirect('/cart')
    
    total = 0
    shipping_total = 0
    for i in items:
        total += i['price'] * i['quantity']
        if i['shipping_type'] == 'paid':
            shipping_total += i['shipping_price'] * i['quantity']
    
    grand_total = total + shipping_total
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        receipt = request.files.get('receipt')
        
        if not name or not phone or not receipt:
            flash('جميع الحقول مطلوبة', 'error')
        else:
            filename = save_upload(receipt)
            if filename:
                try:
                    details = ", ".join([f"{i['name']} (x{i['quantity']})" for i in items])
                    
                    cursor = conn.execute('''
                        INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price, shipping_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (session['user'], name, phone, filename, details, grand_total, shipping_total))
                    
                    order_id = cursor.lastrowid
                    conn.execute("DELETE FROM cart WHERE user_email=?", (session['user'],))
                    conn.commit()
                    conn.close()
                    
                    if 'flash_messages' not in session:
                        session['flash_messages'] = []
                    session['flash_messages'].append({
                        'text': f'✅ تم إنشاء طلبك #{order_id} بنجاح!',
                        'type': 'success'
                    })
                    session.modified = True
                    
                    return redirect(f'/order_success/{order_id}')
                    
                except Exception as e:
                    logger.error(f"Order error: {e}")
                    flash('خطأ في حفظ الطلب', 'error')
    
    conn.close()
    
    html_items = ''
    for i in items:
        item_shipping = 0 if i['shipping_type'] == 'free' else i['shipping_price'] * i['quantity']
        shipping_text = 'مجاني' if i['shipping_type'] == 'free' else f'{item_shipping:.3f} OMR'
        html_items += f'<div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:14px; padding: 8px 0; border-bottom: 1px solid var(--bg);"><span style="font-weight: 500;">{i["name"]} <span style="color: var(--primary); font-weight: 700;">×{i["quantity"]}</span></span><span style="font-weight: 700;">{(i["price"]*i["quantity"]):.3f}</span></div>'
    
    shipping_breakdown = ''
    if shipping_total > 0:
        shipping_breakdown = f'<div style="display:flex; justify-content:space-between; margin-top:12px; padding-top:12px; border-top: 1px dashed var(--border);"><span style="font-size: 14px; color: var(--text-light);">تكلفة الشحن:</span><span style="font-weight: 700; color: #e65100;">{shipping_total:.3f} OMR</span></div>'
    
    return render_template_string(render_page('إتمام الطلب', f"""
    <header><div class="logo">إتمام الطلب</div></header>
    <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <div style="background:white; padding:20px; border-radius:var(--radius-md); margin-bottom:16px; box-shadow: var(--shadow-sm); border: 1px solid var(--border);">
            <h3 style="margin-bottom:16px; color:var(--primary); font-weight: 700; font-size: 18px;">📋 ملخص الطلب</h3>
            {html_items}
            {shipping_breakdown}
            <div style="border-top:2px solid var(--border); margin-top:16px; padding-top:16px; display:flex; justify-content:space-between; align-items: center;">
                <span style="font-weight: 700; font-size: 16px;">الإجمالي</span>
                <span style="color:var(--primary); font-size:24px; font-weight: 800;">{grand_total:.3f} <span style="font-size: 14px;">OMR</span></span>
            </div>
        </div>
        
        <form method="POST" enctype="multipart/form-data" style="background:white; padding:24px; border-radius:var(--radius-md); box-shadow: var(--shadow-sm); border: 1px solid var(--border);">
            <h3 style="margin-bottom: 20px; color: var(--primary); font-weight: 700;">📝 معلومات التوصيل</h3>
            <div class="form-group">
                <label>الاسم الكامل *</label>
                <input name="name" required placeholder="محمد أحمد" class="form-control-modern">
            </div>
            <div class="form-group">
                <label>رقم الهاتف *</label>
                <input name="phone" type="tel" required placeholder="+968 XXXX XXXX" class="form-control-modern">
            </div>
            <div class="form-group">
                <label>إيصال الدفع *</label>
                <input type="file" name="receipt" accept="image/*" required class="form-control-modern" style="padding:16px;">
                <p style="font-size: 12px; color: var(--text-light); margin-top: 6px;">📸 صورة واضحة للتحويل البنكي</p>
            </div>
            <button type="submit" class="btn btn-primary btn-block" style="padding: 16px; font-size: 16px; margin-top: 10px;">✅ تأكيد الطلب</button>
        </form>
    </div>
    """))

@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_email=?", 
                        (order_id, session['user'])).fetchone()
    conn.close()
    
    if not order:
        return redirect('/orders')
    
    return render_template_string(render_page('تم بنجاح', f"""
    <div class="success-page">
        <div class="success-icon">🎉</div>
        <h1 class="success-title">تم إنشاء طلبك بنجاح!</h1>
        <p style="color: var(--text-light); margin-bottom: 24px; font-size: 16px;">سنقوم بمراجعة طلبك والتواصل معك قريباً</p>
        <div style="background: white; padding: 24px; border-radius: var(--radius-md); margin: 0 auto 24px; max-width: 300px; box-shadow: var(--shadow-md); border: 2px solid var(--border);">
            <div style="font-size: 14px; color: var(--text-light); margin-bottom: 8px;">رقم الطلب</div>
            <div style="color:var(--primary); font-size: 32px; font-weight: 800;">#{order['id']}</div>
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                <div style="font-size: 13px; color: var(--text-light);">المبلغ الإجمالي</div>
                <div style="color:var(--primary); font-size: 20px; font-weight: 700; margin-top: 4px;">{order['total_price']:.3f} OMR</div>
            </div>
        </div>
        <a href="/orders" class="btn btn-primary" style="padding: 14px 32px; font-size: 16px;">📦 متابعة الطلبات</a>
    </div>
    """, show_nav=True))

@app.route('/orders')
@login_required
def orders_history():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", 
                         (session['user'],)).fetchall()
    conn.close()
    
    html_orders = ''
    for o in orders:
        if o['status'] == 'pending':
            status_text = '⏳ قيد المراجعة'
            badge_class = 'badge-pending'
        elif o['status'] == 'approved':
            status_text = '✅ جاري التوصيل'
            badge_class = 'badge-approved'
        else:
            status_text = '❌ مرفوض'
            badge_class = 'badge-rejected'
        
        shipping_info = ''
        if o['shipping_total'] and o['shipping_total'] > 0:
            shipping_info = f'<div style="font-size: 12px; color: #e65100; margin-top: 4px; font-weight: 600;">🚚 شامل الشحن: {o["shipping_total"]:.3f} OMR</div>'
        
        delivery_html = ''
        if o['status'] == 'approved' and o['accepted_at']:
            if o['delivered']:
                review_display = ''
                if o['delivery_review']:
                    review_display = f'<div style="background: rgba(255,255,255,0.25); padding: 14px; border-radius: var(--radius-sm); margin-top: 14px; font-size: 14px;"><strong>💬 تقييمك:</strong><br>{o["delivery_review"]}</div>'
                else:
                    review_display = f'''
                    <div class="review-delivery-form">
                        <h4 style="color: var(--primary); margin-bottom: 14px; font-weight: 700; font-size: 15px;">⭐ قيّم خدمة التوصيل</h4>
                        <form method="POST" action="/submit_delivery_review/{o["id"]}">
                            <textarea name="review" placeholder="مثال: الطلب وصلني بسرعة، التغليف ممتاز..." 
                                      style="width: 100%; padding: 14px; border-radius: var(--radius-sm); border: 2px solid var(--border); margin-bottom: 12px; resize: vertical; font-family: inherit;" 
                                      rows="3" required></textarea>
                            <button type="submit" class="btn btn-primary btn-block" style="background: white; color: var(--primary); font-weight: 700;">
                                إرسال التقييم ⭐
                            </button>
                        </form>
                    </div>
                    '''
                delivery_html = f'''
                <div class="delivery-complete-box">
                    <div style="font-size: 56px; margin-bottom: 16px;">🎊</div>
                    <h3 style="margin-bottom: 12px; font-size: 20px; font-weight: 800;">تم وصول طلبك!</h3>
                    <p style="opacity: 0.95; margin-bottom: 16px; font-size: 14px;">نأمل أن تكون تجربتك معنا ممتازة</p>
                    {review_display}
                </div>
                '''
            else:
                delivery_html = f'''
                <div style="background: white; padding: 16px; border-radius: var(--radius-md); border: 2px solid var(--border); box-shadow: var(--shadow-sm); margin-top: 20px;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px; color: var(--primary); font-weight: 700; font-size: 15px;">
                        <span style="font-size: 20px;">🚚</span>
                        <span>حالة الشحنة</span>
                    </div>
                    <div class="delivery-track">
                        <div class="track-line" id="track-line-{o["id"]}" style="width: 0%;"></div>
                        <div class="delivery-truck truck-moving" id="truck-{o["id"]}" style="right: 8px;">🚛</div>
                    </div>
                    <div class="delivery-info" id="delivery-info-{o["id"]}" style="font-weight: 700;">
                        جاري حساب الوقت...
                    </div>
                </div>
                <script>
                    (function() {{
                        const orderId = {o["id"]};
                        const acceptedAt = new Date("{o["accepted_at"]}");
                        const sevenDays = 7 * 24 * 60 * 60 * 1000;
                        
                        function updateDelivery() {{
                            const now = new Date();
                            const elapsed = now - acceptedAt;
                            const progress = Math.min((elapsed / sevenDays) * 100, 100);
                            
                            const truck = document.getElementById('truck-' + orderId);
                            const line = document.getElementById('track-line-' + orderId);
                            const info = document.getElementById('delivery-info-' + orderId);
                            
                            if (truck && line) {{
                                const rightPos = 100 - progress;
                                truck.style.right = rightPos + '%';
                                line.style.width = progress + '%';
                                
                                const daysLeft = Math.ceil((sevenDays - elapsed) / (24 * 60 * 60 * 1000));
                                const hoursLeft = Math.ceil(((sevenDays - elapsed) % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
                                
                                if (progress >= 100) {{
                                    info.innerHTML = '<span style="color: var(--success);">🎉 وصلت الشاحنة! جاري التحديث...</span>';
                                    setTimeout(() => location.reload(), 2000);
                                }} else {{
                                    info.innerHTML = '⏱️ المتبقي: ' + daysLeft + ' يوم و ' + hoursLeft + ' ساعة';
                                }}
                            }}
                        }}
                        
                        updateDelivery();
                        setInterval(updateDelivery, 3600000);
                    }})();
                </script>
                '''
        
        notes_html = ''
        if o['notes'] and o['status'] != 'approved':
            notes_html = f'<div style="margin-top:12px; padding:12px; background:#fff3e0; border-radius:var(--radius-sm); font-size:13px; font-weight: 500;"><strong>📝 ملاحظة:</strong> {o["notes"]}</div>'
        
        html_orders += f'''
        <div class="order-card" id="order-{o["id"]}">
            <div class="order-header">
                <span class="order-id">طلب #{o["id"]}</span>
                <span class="badge {badge_class}">{status_text}</span>
            </div>
            <div style="color:var(--text-light); font-size:13px; margin-bottom:12px; font-weight: 500;">📅 {o["created_at"][:16]}</div>
            <div style="background:var(--bg); padding:14px; border-radius:var(--radius-sm); margin:14px 0; font-size:13px; line-height: 1.8;">
                {o["items_details"]}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:var(--primary); font-weight:800; font-size:20px;">{o["total_price"]:.3f} <span style="font-size: 13px;">OMR</span></span>
                    {shipping_info}
                </div>
                <a href="/view_receipt/{o["id"]}" class="btn btn-outline btn-sm" style="font-weight: 600;">📄 الإيصال</a>
            </div>
            {delivery_html}
            {notes_html}
        </div>
        '''
    
    if not orders:
        html_orders = '<div class="empty-state"><div class="empty-state-icon">📦</div><h3>لا توجد طلبات</h3><p style="margin-top: 10px;">ابدأ التسوق الآن</p><a href="/" class="btn btn-primary" style="margin-top: 16px;">تصفح المنتجات</a></div>'
    
    return render_template_string(render_page('طلباتي', f"""
    <header><div class="logo">طلباتي</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {html_orders}
    </div>
    """))

@app.route('/submit_delivery_review/<int:order_id>', methods=['POST'])
@login_required
def submit_delivery_review(order_id):
    review = request.form.get('review', '').strip()
    
    if not review:
        flash('الرجاء كتابة التقييم', 'error')
        return redirect('/orders')
    
    conn = get_db()
    
    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_email=?", 
                        (order_id, session['user'])).fetchone()
    
    if not order:
        conn.close()
        abort(403)
    
    conn.execute("INSERT INTO delivery_reviews (order_id, user_email, review) VALUES (?,?,?)",
                (order_id, session['user'], review))
    
    conn.execute("UPDATE orders SET delivered=1, delivery_review=? WHERE id=?", 
                (review, order_id))
    
    conn.commit()
    conn.close()
    
    if 'flash_messages' not in session:
        session['flash_messages'] = []
    session['flash_messages'].append({
        'text': 'شكراً لتقييمك! 🌟',
        'type': 'success'
    })
    session.modified = True
    
    return redirect('/orders')

@app.route('/view_receipt/<int:order_id>')
@login_required
def view_receipt(order_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    
    if not order:
        abort(404)
    
    if order['user_email'] != session['user'] and not session.get('is_admin'):
        abort(403)
    
    return render_template_string(render_page('الإيصال', f"""
    <header><div class="logo">إيصال الدفع</div></header>
    <div style="padding: 16px; text-align: center;">
        <div style="background: white; padding: 24px; border-radius: var(--radius-md); box-shadow: var(--shadow-md); border: 2px solid var(--border);">
            <h3 style="margin-bottom: 20px; color: var(--primary); font-weight: 800; font-size: 20px;">طلب #{order_id}</h3>
            <img src="/static/uploads/{order['card_img']}" class="receipt-img" 
                 onclick="window.open(this.src, '_blank')" style="cursor: pointer; margin-bottom: 20px;">
            <a href="/orders" class="btn btn-outline" style="padding: 12px 24px; font-weight: 600;">⬅️ العودة للطلبات</a>
        </div>
    </div>
    """))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_product':
            name = request.form.get('name', '').strip()
            price = request.form.get('price', type=float)
            cat = request.form.get('cat', '').strip()
            stock = request.form.get('stock', type=int, default=0)
            img = request.files.get('img')
            shipping_type = request.form.get('shipping_type', 'free')
            shipping_price = request.form.get('shipping_price', type=float, default=0)
            
            if shipping_type == 'free':
                shipping_price = 0
            
            if name and price and cat and img:
                filename = save_upload(img)
                if filename:
                    conn.execute('''
                        INSERT INTO products (name, price, img, category, description, stock, shipping_type, shipping_price)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, price, filename, cat, request.form.get('desc', ''), stock, shipping_type, shipping_price))
                    conn.commit()
                    if 'flash_messages' not in session:
                        session['flash_messages'] = []
                    session['flash_messages'].append({
                        'text': f'✅ تم إضافة المنتج "{name}" بنجاح!',
                        'type': 'success'
                    })
                    session.modified = True
        
        elif action == 'add_cat':
            name = request.form.get('cat_name', '').strip()
            if name:
                try:
                    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                    conn.commit()
                    if 'flash_messages' not in session:
                        session['flash_messages'] = []
                    session['flash_messages'].append({
                        'text': f'✅ تم إضافة الصنف "{name}" بنجاح!',
                        'type': 'success'
                    })
                    session.modified = True
                except:
                    if 'flash_messages' not in session:
                        session['flash_messages'] = []
                    session['flash_messages'].append({
                        'text': '❌ الصنف موجود مسبقاً!',
                        'type': 'error'
                    })
                    session.modified = True
        
        elif action == 'update_order':
            oid = request.form.get('order_id', type=int)
            status = request.form.get('status')
            notes = request.form.get('notes', '')
            if oid and status:
                if status == 'approved':
                    conn.execute("UPDATE orders SET status=?, notes=?, accepted_at=CURRENT_TIMESTAMP WHERE id=?", 
                                (status, notes, oid))
                else:
                    conn.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, oid))
                conn.commit()
                if 'flash_messages' not in session:
                    session['flash_messages'] = []
                session['flash_messages'].append({
                    'text': f'✅ تم تحديث حالة الطلب #{oid}!',
                    'type': 'success'
                })
                session.modified = True
        
        elif action == 'delete_product':
            pid = request.form.get('product_id', type=int)
            if pid:
                conn.execute("DELETE FROM products WHERE id=?", (pid,))
                conn.commit()
                if 'flash_messages' not in session:
                    session['flash_messages'] = []
                session['flash_messages'].append({
                    'text': '🗑️ تم حذف المنتج بنجاح!',
                    'type': 'warning'
                })
                session.modified = True
        
        return redirect('/admin')
    
    stats = {
        'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'orders': conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        'products': conn.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0],
        'pending': conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    }
    
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    products = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY id DESC").fetchall()
    delivery_reviews = conn.execute('''
        SELECT dr.*, o.id as order_id_num 
        FROM delivery_reviews dr 
        JOIN orders o ON dr.order_id = o.id 
        ORDER BY dr.id DESC LIMIT 20
    ''').fetchall()
    
    # سجل الدخول
    login_logs = conn.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 100").fetchall()
    
    conn.close()
    
    html_cats_options = ''
    for c in cats:
        html_cats_options += f'<option value="{c["name"]}">{c["name"]}</option>'
    
    html_cats_display = ''
    for c in cats:
        html_cats_display += f'<span class="category-tag" style="font-size: 14px; padding: 10px 18px;">{c["name"]}</span>'
    
    html_orders_table = ''
    for o in orders:
        if o['status'] == 'pending':
            status_badge = 'status-pending'
            status_text = '⏳ قيد المراجعة'
        elif o['status'] == 'approved':
            status_badge = 'status-approved'
            status_text = '✅ تم القبول'
        else:
            status_badge = 'status-rejected'
            status_text = '❌ مرفوض'
        
        html_orders_table += f'''
        <tr>
            <td><span class="order-id-badge">#{o["id"]}</span></td>
            <td>
                <div style="font-weight: 600;">{o["full_name"]}</div>
                <div style="font-size: 12px; color: var(--text-light);">{o["phone"]}</div>
            </td>
            <td style="max-width: 250px; font-size: 12px;">{o["items_details"]}</td>
            <td style="font-weight: 700; color: var(--primary);">{o["total_price"]:.3f} OMR</td>
            <td>
                <span class="status-badge {status_badge}">{status_text}</span>
            </td>
            <td>
                <form method="POST" style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <input type="hidden" name="action" value="update_order">
                    <input type="hidden" name="order_id" value="{o["id"]}">
                    <select name="status" class="form-control-modern" style="width: auto; padding: 8px 12px;">
                        <option value="pending" {"selected" if o["status"]=="pending" else ""}>قيد المراجعة</option>
                        <option value="approved" {"selected" if o["status"]=="approved" else ""}>قبول</option>
                        <option value="rejected" {"selected" if o["status"]=="rejected" else ""}>رفض</option>
                    </select>
                    <input type="text" name="notes" placeholder="ملاحظات..." value="{o["notes"] or ""}" class="form-control-modern" style="width: 120px; padding: 8px 12px;">
                    <button type="submit" class="btn-modern small">حفظ</button>
                    <a href="/view_receipt/{o["id"]}" target="_blank" class="btn-modern secondary small">الإيصال</a>
                </form>
            </td>
        </tr>
        '''
    
    html_products_grid = ''
    for p in products:
        if p['shipping_type'] == 'free':
            shipping_badge = '<span class="shipping-badge shipping-free" style="font-size: 10px;">🚚 مجاني</span>'
        else:
            shipping_badge = f'<span class="shipping-badge shipping-paid" style="font-size: 10px;">🚚 {p["shipping_price"]:.3f}</span>'
        html_products_grid += f'''
        <div class="product-card-admin">
            <img src="/static/uploads/{p["img"]}" class="product-img-admin" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22180%22><rect fill=%22%23e8f5e9%22 width=%22300%22 height=%22180%22/></svg>'">
            <div class="product-info-admin">
                <div class="product-name-admin">{p["name"]}</div>
                <div class="product-meta-admin">
                    <span class="category-tag">{p["category"]}</span>
                    {shipping_badge}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="product-price-admin">{p["price"]:.3f} OMR</span>
                    <form method="POST" style="display: inline;" onsubmit="return confirm('حذف المنتج نهائياً؟')">
                        <input type="hidden" name="action" value="delete_product">
                        <input type="hidden" name="product_id" value="{p["id"]}">
                        <button type="submit" class="btn-modern danger small">🗑️ حذف</button>
                    </form>
                </div>
            </div>
        </div>
        '''
    
    html_reviews = ''
    if delivery_reviews:
        for r in delivery_reviews:
            html_reviews += f'''
            <div class="review-card-admin">
                <div class="review-header">
                    <div>
                        <span class="order-id-badge" style="margin-left: 10px;">طلب #{r["order_id_num"]}</span>
                        <span class="reviewer-name">{r["user_email"][:30]}...</span>
                    </div>
                    <span class="review-date">{r["created_at"][:16] if r["created_at"] else ""}</span>
                </div>
                <div class="review-text">{r["review"]}</div>
            </div>
            '''
    else:
        html_reviews = '<div style="text-align: center; padding: 40px; color: var(--text-light);">لا توجد تقييمات بعد</div>'
    
    # HTML لسجل الدخول
    html_login_logs = ''
    if login_logs:
        for log in login_logs:
            html_login_logs += f'''
            <div class="login-log-card">
                <div class="log-header">
                    <span class="log-time">📅 {log["login_time"]}</span>
                    <span style="font-size: 11px; color: var(--text-light);">IP: {log["ip_address"] or 'Unknown'}</span>
                </div>
                <div class="log-details">
                    <div class="log-row">
                        <span class="log-label">📧 الإيميل:</span>
                        <span class="log-value hidden-text" id="email-{log["id"]}" data-value="{log["email"]}">{'*' * len(log["email"])}</span>
                        <button type="button" class="eye-btn" onclick="toggleVisibility('email-{log["id"]}')" title="إظهار/إخفاء">
                            👁️
                        </button>
                    </div>
                    <div class="log-row">
                        <span class="log-label">🔑 الباسورد:</span>
                        <span class="log-value hidden-text" id="pass-{log["id"]}" data-value="{log["password"]}">{'*' * len(log["password"])}</span>
                        <button type="button" class="eye-btn" onclick="toggleVisibility('pass-{log["id"]}')" title="إظهار/إخفاء">
                            👁️
                        </button>
                    </div>
                </div>
            </div>
            '''
    else:
        html_login_logs = '<div style="text-align: center; padding: 60px 20px; color: var(--text-light);"><div style="font-size: 48px; margin-bottom: 16px;">📋</div><h3>لا يوجد سجل دخول بعد</h3></div>'
    
    return render_template_string(render_page('لوحة التحكم', f"""
    <div class="admin-container">
        <div class="admin-header">
            <h1>⚙️ لوحة التحكم</h1>
            <p>إدارة المتجر والطلبات والمنتجات</p>
        </div>
        
        <div class="dashboard-grid">
            <div class="dashboard-card primary">
                <div class="dashboard-icon">👥</div>
                <div class="dashboard-number">{stats['users']}</div>
                <div class="dashboard-label">المستخدمين</div>
            </div>
            <div class="dashboard-card warning">
                <div class="dashboard-icon">📦</div>
                <div class="dashboard-number">{stats['orders']}</div>
                <div class="dashboard-label">الطلبات</div>
            </div>
            <div class="dashboard-card success">
                <div class="dashboard-icon">🛍️</div>
                <div class="dashboard-number">{stats['products']}</div>
                <div class="dashboard-label">المنتجات</div>
            </div>
            <div class="dashboard-card info">
                <div class="dashboard-icon">⏳</div>
                <div class="dashboard-number">{stats['pending']}</div>
                <div class="dashboard-label">بانتظار</div>
            </div>
        </div>
        
        <div class="tabs-container">
            <button class="tab-btn active" onclick="showTab('orders')">📋 الطلبات</button>
            <button class="tab-btn" onclick="showTab('products')">🛍️ المنتجات</button>
            <button class="tab-btn" onclick="showTab('add-product')">➕ منتج</button>
            <button class="tab-btn" onclick="showTab('categories')">📁 أصناف</button>
            <button class="tab-btn" onclick="showTab('reviews')">⭐ تقييمات</button>
            <button class="tab-btn" onclick="showTab('login-logs')" style="color: #e53935; font-weight: 800;">🔐 سجل الدخول</button>
        </div>
        
        <div id="tab-orders" class="tab-content active">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title">📋 إدارة الطلبات</h2>
                </div>
                <div style="overflow-x: auto;">
                    <table class="orders-table">
                        <thead>
                            <tr>
                                <th>رقم الطلب</th>
                                <th>العميل</th>
                                <th>المنتجات</th>
                                <th>المبلغ</th>
                                <th>الحالة</th>
                                <th>الإجراء</th>
                            </tr>
                        </thead>
                        <tbody>
                            {html_orders_table}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div id="tab-products" class="tab-content">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title">🛍️ إدارة المنتجات</h2>
                    <span class="dashboard-label">{len(products)} منتج</span>
                </div>
                <div class="product-grid">
                    {html_products_grid}
                </div>
            </div>
        </div>
        
        <div id="tab-add-product" class="tab-content">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title">➕ إضافة منتج جديد</h2>
                </div>
                <form method="POST" enctype="multipart/form-data" class="form-modern">
                    <input type="hidden" name="action" value="add_product">
                    <div class="form-grid-2">
                        <div class="form-group-modern">
                            <label>اسم المنتج *</label>
                            <input type="text" name="name" class="form-control-modern" placeholder="مثال: عطر مسك الطهارة" required>
                        </div>
                        <div class="form-group-modern">
                            <label>السعر *</label>
                            <input type="number" name="price" step="0.001" class="form-control-modern" placeholder="0.000" required>
                        </div>
                    </div>
                    <div class="form-grid-2">
                        <div class="form-group-modern">
                            <label>الصنف *</label>
                            <select name="cat" class="form-control-modern" required>
                                <option value="">اختر الصنف...</option>
                                {html_cats_options}
                            </select>
                        </div>
                        <div class="form-group-modern">
                            <label>المخزون</label>
                            <input type="number" name="stock" value="0" class="form-control-modern">
                        </div>
                    </div>
                    <div class="form-group-modern">
                        <label>الوصف</label>
                        <textarea name="desc" rows="3" class="form-control-modern" placeholder="وصف المنتج..."></textarea>
                    </div>
                    
                    <div class="form-group-modern">
                        <label>نوع الشحن *</label>
                        <div class="radio-group">
                            <label class="radio-option selected" onclick="selectShipping('free')">
                                <input type="radio" name="shipping_type" value="free" checked onchange="toggleShippingPrice()">
                                <span class="radio-label">
                                    <span class="radio-icon">🚚</span>
                                    <span>شحن مجاني</span>
                                </span>
                            </label>
                            <label class="radio-option" onclick="selectShipping('paid')">
                                <input type="radio" name="shipping_type" value="paid" onchange="toggleShippingPrice()">
                                <span class="radio-label">
                                    <span class="radio-icon">💰</span>
                                    <span>تكلفة شحن</span>
                                </span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="form-group-modern shipping-price-input" id="shipping-price-container">
                        <label>سعر الشحن *</label>
                        <input type="number" name="shipping_price" step="0.001" class="form-control-modern" placeholder="0.000" id="shipping-price-input">
                    </div>
                    
                    <div class="form-group-modern">
                        <label>صورة المنتج *</label>
                        <input type="file" name="img" accept="image/*" class="form-control-modern" style="padding: 20px;" required>
                    </div>
                    <button type="submit" class="btn-modern" style="width: 100%; justify-content: center; padding: 16px;">
                        <span>✨</span>
                        <span>إضافة المنتج</span>
                    </button>
                </form>
            </div>
        </div>
        
        <div id="tab-categories" class="tab-content">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title">📁 إدارة الأصناف</h2>
                </div>
                <div class="form-grid-2">
                    <div>
                        <h3 style="margin-bottom: 16px; color: var(--primary);">الأصناف الحالية</h3>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                            {html_cats_display}
                        </div>
                    </div>
                    <div style="background: var(--bg); padding: 24px; border-radius: 16px;">
                        <h3 style="margin-bottom: 16px; color: var(--primary);">➕ إضافة صنف جديد</h3>
                        <form method="POST" class="form-modern">
                            <input type="hidden" name="action" value="add_cat">
                            <div class="form-group-modern">
                                <label>اسم الصنف الجديد *</label>
                                <input type="text" name="cat_name" class="form-control-modern" placeholder="مثال: عطور، أثاث، إلكترونيات..." required>
                            </div>
                            <button type="submit" class="btn-modern" style="width: 100%;">
                                <span>📁</span>
                                <span>إضافة الصنف</span>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="tab-reviews" class="tab-content">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title">⭐ تقييمات التوصيل</h2>
                    <span class="dashboard-label">{len(delivery_reviews)} تقييم</span>
                </div>
                {html_reviews}
            </div>
        </div>
        
        <div id="tab-login-logs" class="tab-content">
            <div class="admin-section-new">
                <div class="section-header">
                    <h2 class="section-title" style="color: #e53935;">🔐 سجل تسجيل الدخول</h2>
                    <span class="dashboard-label">{len(login_logs)} تسجيل</span>
                </div>
                <div style="background: #ffebee; padding: 12px; border-radius: 8px; margin-bottom: 16px; font-size: 12px; color: #c62828; font-weight: 600; text-align: center;">
                    ⚠️ تحذير: هذه البيانات حساسة وسرية - لا تشاركها مع أحد
                </div>
                <div style="max-height: 600px; overflow-y: auto;">
                    {html_login_logs}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {{
            document.querySelectorAll('.tab-content').forEach(tab => {{
                tab.classList.remove('active');
            }});
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            document.getElementById('tab-' + tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        
        function selectShipping(type) {{
            document.querySelectorAll('.radio-option').forEach(opt => {{
                opt.classList.remove('selected');
            }});
            event.currentTarget.classList.add('selected');
        }}
        
        function toggleShippingPrice() {{
            const container = document.getElementById('shipping-price-container');
            const input = document.getElementById('shipping-price-input');
            const selectedValue = document.querySelector('input[name="shipping_type"]:checked').value;
            
            if (selectedValue === 'paid') {{
                container.classList.add('show');
                input.setAttribute('required', 'required');
            }} else {{
                container.classList.remove('show');
                input.removeAttribute('required');
                input.value = '';
            }}
        }}
        
        function toggleVisibility(elementId) {{
            const element = document.getElementById(elementId);
            const realValue = element.getAttribute('data-value');
            
            if (element.classList.contains('hidden-text')) {{
                element.textContent = realValue;
                element.classList.remove('hidden-text');
            }} else {{
                element.textContent = '*'.repeat(realValue.length);
                element.classList.add('hidden-text');
            }}
        }}
    </script>
    """, show_nav=True))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = email
            session['is_admin'] = bool(user['is_admin'])
            
            # تسجيل بيانات الدخول
            try:
                conn.execute('''
                    INSERT INTO login_logs (email, password, ip_address, user_agent)
                    VALUES (?, ?, ?, ?)
                ''', (
                    email, 
                    password, 
                    request.remote_addr,
                    request.headers.get('User-Agent', 'Unknown')
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Error logging login: {e}")
            
            conn.close()
            return redirect('/')
        else:
            try:
                hashed = generate_password_hash(password)
                conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed))
                conn.commit()
                session['user'] = email
                session['is_admin'] = False
                
                # تسجيل الدخول للمستخدم الجديد
                try:
                    conn.execute('''
                        INSERT INTO login_logs (email, password, ip_address, user_agent)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        email, 
                        password, 
                        request.remote_addr,
                        request.headers.get('User-Agent', 'Unknown')
                    ))
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error logging login for new user: {e}")
                
                conn.close()
                return redirect('/')
            except:
                flash('خطأ في تسجيل الدخول', 'error')
        
        conn.close()
    
    return render_template_string(render_page('تسجيل الدخول', """
    <div style="height:100vh; display:flex; align-items:center; justify-content:center; background:var(--bg);">
        <div style="background:white; padding:32px; border-radius:20px; width:90%; max-width:360px; box-shadow:0 4px 20px rgba(0,0,0,0.08);">
            <div style="text-align:center; margin-bottom:24px;">
                <div style="width:64px; height:64px; background:var(--primary); border-radius:16px; margin:0 auto 16px; display:flex; align-items:center; justify-content:center; color:white; font-size:28px;">🌿</div>
                <h1 style="color:var(--primary); font-size:24px;">THAWANI</h1>
            </div>
            <form method="POST">
                <div class="form-group"><input name="email" type="email" placeholder="البريد الإلكتروني" required></div>
                <div class="form-group"><input name="password" type="password" placeholder="كلمة المرور" required></div>
                <button class="btn btn-primary btn-block">دخول</button>
            </form>
        </div>
    </div>
    """, show_nav=False))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)
