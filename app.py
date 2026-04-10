from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sqlite3
import uuid
import re
import logging

# إعداد Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

logger.info(f"Upload folder: {UPLOAD_FOLDER}")

# ========== قاعدة البيانات ==========
def get_db():
    conn = sqlite3.connect('database.db', timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL CHECK(price > 0),
            img TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1 CHECK(quantity > 0),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_email, product_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            action TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@thawani.store')
    admin_pass = os.environ.get('ADMIN_PASS', 'Admin123!')
    hashed = generate_password_hash(admin_pass, method='pbkdf2:sha256')
    
    try:
        c.execute("INSERT OR IGNORE INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", 
                  (admin_email, hashed))
    except:
        pass
    
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# ========== الديكوريتورز ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ========== المساعدات ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_upload(file):
    if not file or file.filename == '':
        flash('لم يتم اختيار ملف', 'error')
        return None
    
    if not allowed_file(file.filename):
        flash('نوع الملف غير مسموح', 'error')
        return None
    
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_CONTENT_LENGTH or size == 0:
        flash('حجم الملف غير صالح', 'error')
        return None
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        if os.path.exists(filepath):
            logger.info(f"File uploaded: {filename}")
            return filename
    except Exception as e:
        logger.error(f"Upload error: {e}")
        flash('خطأ في رفع الملف', 'error')
    return None

def log_activity(user_email, action):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO activity_log (user_email, action, ip_address, user_agent) VALUES (?, ?, ?, ?)",
            (user_email, action, request.remote_addr, str(request.user_agent)[:200])
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Log error: {e}")

def save_flash_message(text, type_='info'):
    if 'flash_messages' not in session:
        session['flash_messages'] = []
    session['flash_messages'].append({'text': text, 'type': type_})
    session.modified = True

# ========== CSS ==========
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    :root { 
        --primary: #000; 
        --accent: #d4af37; 
        --gold-light: #f1e5ac; 
        --bg: #121212; 
        --card: #1e1e1e;
        --success: #2ecc71;
        --error: #e74c3c;
        --warning: #f39c12;
        --info: #3498db;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body { 
        font-family: 'Tajawal', sans-serif; 
        background: var(--bg); 
        direction: rtl; 
        color: #fff; 
        padding-bottom: 100px;
        line-height: 1.6;
        min-height: 100vh;
    }
    
    .flash-messages {
        position: fixed;
        top: 90px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        width: 90%;
        max-width: 400px;
    }
    .flash {
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 10px;
        text-align: center;
        font-weight: bold;
        animation: slideDown 0.4s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border: 2px solid;
    }
    .flash.success { background: var(--success); color: #fff; border-color: #27ae60; }
    .flash.error { background: var(--error); color: #fff; border-color: #c0392b; }
    .flash.warning { background: var(--warning); color: #000; border-color: #d68910; }
    
    @keyframes slideDown {
        from { transform: translate(-50%, -100%); opacity: 0; }
        to { transform: translate(-50%, 0); opacity: 1; }
    }
    
    header { 
        background: linear-gradient(135deg, #000 0%, #1a1a1a 100%); 
        padding: 20px; 
        text-align: center; 
        border-bottom: 3px solid var(--accent);
        box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
        position: sticky; 
        top: 0; 
        z-index: 1000; 
    }
    .logo { 
        font-size: 28px; 
        font-weight: 900; 
        color: var(--accent); 
        letter-spacing: 3px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .user-info {
        color: var(--gold-light);
        font-size: 12px;
        margin-top: 8px;
    }
    
    .bottom-nav { 
        position: fixed; 
        bottom: 0; 
        left: 0; 
        width: 100%; 
        background: linear-gradient(to top, #000, #1a1a1a); 
        display: flex; 
        justify-content: space-around; 
        padding: 12px 0; 
        border-top: 2px solid var(--accent); 
        z-index: 1000;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.5);
    }
    .nav-item { 
        color: #888; 
        text-decoration: none; 
        font-size: 12px; 
        font-weight: bold;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        transition: all 0.3s;
        padding: 8px 12px;
        border-radius: 12px;
        flex: 1;
    }
    .nav-item:hover { color: var(--gold-light); background: rgba(255,255,255,0.05); }
    .nav-item.active { 
        color: var(--accent); 
        background: rgba(212, 175, 55, 0.15);
    }
    .nav-icon { font-size: 22px; margin-bottom: 2px; }
    
    .container { 
        padding: 15px; 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
        gap: 15px; 
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .card { 
        background: var(--card); 
        border-radius: 15px; 
        border: 1px solid #333; 
        overflow: hidden;
        transition: all 0.3s ease;
        position: relative;
        display: flex;
        flex-direction: column;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(212, 175, 55, 0.15);
        border-color: var(--accent);
    }
    .card-img-container {
        position: relative;
        overflow: hidden;
        height: 180px;
    }
    .card img { 
        width: 100%; 
        height: 100%; 
        object-fit: cover;
        transition: transform 0.3s;
    }
    .card:hover img { transform: scale(1.05); }
    .card-body { 
        padding: 15px; 
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    .product-title { 
        font-weight: bold; 
        font-size: 14px;
        margin-bottom: 10px;
        line-height: 1.4;
        flex: 1;
    }
    .price { 
        color: var(--accent); 
        font-weight: 900; 
        font-size: 18px;
        margin-bottom: 10px;
    }
    .stock-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        background: var(--accent);
        color: #000;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: bold;
        z-index: 10;
    }
    .out-of-stock-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: bold;
        font-size: 16px;
        z-index: 5;
    }
    
    .btn { 
        border: none; 
        padding: 12px 20px; 
        border-radius: 10px; 
        font-weight: bold; 
        cursor: pointer; 
        text-decoration: none; 
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        text-align: center;
        transition: all 0.3s;
        font-size: 14px;
        font-family: inherit;
    }
    .btn-gold { 
        background: linear-gradient(45deg, var(--accent), var(--gold-light)); 
        color: #000;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
    }
    .btn-gold:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(212, 175, 55, 0.4);
    }
    .btn-red { 
        background: linear-gradient(45deg, #e74c3c, #c0392b); 
        color: #fff; 
    }
    .btn-green { 
        background: linear-gradient(45deg, #2ecc71, #27ae60); 
        color: #fff; 
    }
    .btn-blue {
        background: linear-gradient(45deg, #3498db, #2980b9);
        color: #fff;
    }
    .btn-gray {
        background: linear-gradient(45deg, #666, #555);
        color: #fff;
    }
    .btn-block { display: flex; width: 100%; margin-top: auto; }
    .btn-sm { padding: 8px 12px; font-size: 12px; }
    .btn-lg { padding: 15px 25px; font-size: 16px; }
    
    .form-group { margin-bottom: 20px; }
    label {
        display: block;
        margin-bottom: 8px;
        color: var(--gold-light);
        font-size: 14px;
        font-weight: bold;
    }
    input, select, textarea { 
        width: 100%; 
        padding: 14px; 
        background: #222; 
        border: 2px solid #444; 
        color: #fff; 
        border-radius: 10px; 
        transition: all 0.3s;
        font-family: inherit;
        font-size: 14px;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
    }
    input::placeholder { color: #666; }
    
    .table-container {
        overflow-x: auto;
        background: #1a1a1a;
        border-radius: 12px;
        padding: 15px;
        margin: 15px 0;
        border: 1px solid #333;
    }
    table { 
        width: 100%; 
        border-collapse: collapse; 
        font-size: 13px;
    }
    th { 
        background: var(--accent); 
        color: #000; 
        padding: 12px;
        font-weight: bold;
        text-align: center;
    }
    td { 
        border-bottom: 1px solid #333; 
        padding: 12px; 
        text-align: center; 
    }
    tr:hover { background: rgba(212, 175, 55, 0.05); }
    
    .cat-bar { 
        display: flex; 
        overflow-x: auto; 
        padding: 15px; 
        gap: 10px; 
        background: #1a1a1a;
        scrollbar-width: none;
        border-bottom: 1px solid #333;
    }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-item { 
        background: #333; 
        color: #fff; 
        padding: 10px 20px; 
        border-radius: 25px; 
        text-decoration: none; 
        font-size: 13px; 
        white-space: nowrap;
        transition: all 0.3s;
        border: 2px solid transparent;
        font-weight: bold;
    }
    .cat-item:hover {
        background: #444;
        border-color: var(--accent);
    }
    .cat-item.active { 
        background: var(--accent); 
        color: #000; 
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
    }
    
    .review-card {
        background: #222;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border-right: 4px solid var(--accent);
    }
    .stars { color: var(--accent); font-size: 20px; letter-spacing: 2px; }
    .review-meta {
        color: #888;
        font-size: 12px;
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
    }
    
    .badge {
        padding: 6px 15px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-pending { background: var(--warning); color: #000; }
    .badge-approved { background: var(--success); color: #fff; }
    .badge-rejected { background: var(--error); color: #fff; }
    .badge-shipped { background: #3498db; color: #fff; }
    .badge-delivered { background: #9b59b6; color: #fff; }
    
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #666;
    }
    .empty-state-icon {
        font-size: 80px;
        margin-bottom: 20px;
        opacity: 0.5;
    }
    .empty-state h3 {
        color: #888;
        margin-bottom: 20px;
    }
    
    .order-card {
        background: #1a1a1a;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        border-right: 4px solid var(--accent);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .order-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .order-id {
        font-size: 20px;
        font-weight: bold;
    }
    .order-items {
        background: #222;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        font-size: 14px;
    }
    .order-total {
        font-size: 22px;
        font-weight: bold;
        color: var(--accent);
    }
    
    .cart-item {
        display: flex;
        gap: 15px;
        background: #1a1a1a;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 15px;
        align-items: center;
        border: 1px solid #333;
    }
    .cart-item img {
        width: 80px;
        height: 80px;
        object-fit: cover;
        border-radius: 10px;
        border: 2px solid var(--accent);
    }
    .cart-item-info {
        flex: 1;
    }
    .cart-item-title {
        font-weight: bold;
        margin-bottom: 5px;
        font-size: 15px;
    }
    .cart-item-price {
        color: var(--accent);
        font-size: 16px;
    }
    .cart-item-qty {
        color: #888;
        font-size: 13px;
    }
    .cart-item-total {
        text-align: left;
        font-weight: bold;
        font-size: 18px;
    }
    
    .checkout-summary {
        background: #1a1a1a;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 2px solid var(--accent);
    }
    .checkout-summary h3 {
        color: var(--accent);
        margin-bottom: 20px;
        font-size: 20px;
    }
    .summary-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid #333;
    }
    .summary-total {
        display: flex;
        justify-content: space-between;
        font-size: 24px;
        font-weight: bold;
        border-top: 2px solid var(--accent);
        padding-top: 15px;
        margin-top: 15px;
    }
    .summary-total span:last-child {
        color: var(--accent);
    }
    
    .admin-section {
        background: #1a1a1a;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid #333;
    }
    .admin-section h3 {
        color: var(--accent);
        margin-bottom: 25px;
        font-size: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
        margin-bottom: 25px;
    }
    .stat-card {
        background: linear-gradient(135deg, #222, #2a2a2a);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 2px solid var(--accent);
        transition: transform 0.3s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
    }
    .stat-number {
        font-size: 36px;
        font-weight: 900;
        color: var(--accent);
        margin-bottom: 5px;
    }
    .stat-label {
        color: #888;
        font-size: 13px;
        font-weight: bold;
    }
    
    .success-page {
        text-align: center;
        padding: 40px 20px;
    }
    .success-icon {
        font-size: 100px;
        margin-bottom: 20px;
        animation: scaleIn 0.5s ease;
    }
    @keyframes scaleIn {
        from { transform: scale(0); }
        to { transform: scale(1); }
    }
    .success-title {
        color: var(--success);
        font-size: 28px;
        margin-bottom: 15px;
    }
    .success-message {
        color: #888;
        font-size: 16px;
        margin-bottom: 30px;
    }
    .order-number {
        background: #222;
        padding: 20px;
        border-radius: 15px;
        margin: 25px 0;
        border: 2px solid var(--accent);
    }
    .order-number-label {
        color: #888;
        font-size: 14px;
        margin-bottom: 5px;
    }
    .order-number-value {
        color: var(--accent);
        font-size: 32px;
        font-weight: bold;
    }
    
    @media (max-width: 480px) {
        .container { grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 10px; }
        .logo { font-size: 24px; }
        .card-img-container { height: 150px; }
        .stats-grid { grid-template-columns: 1fr; }
        .order-header { flex-direction: column; align-items: flex-start; }
    }
    
    @media (min-width: 768px) {
        .container { grid-template-columns: repeat(3, 1fr); }
        .stats-grid { grid-template-columns: repeat(4, 1fr); }
    }
    
    @media (min-width: 1024px) {
        .container { grid-template-columns: repeat(4, 1fr); }
    }
    
    .receipt-img {
        max-width: 100%;
        border-radius: 10px;
        border: 2px solid var(--accent);
        margin-top: 15px;
        cursor: zoom-in;
    }
</style>
"""

BASE_HTML = """
<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
    <meta name="theme-color" content="#000000">
    <meta name="description" content="ثواني ستور - وجهتك الأولى للتسوق الفاخر">
    {css}
    <title>{title} | THAWANI STORE</title>
</head>
<body>
    {flash_messages}
    {content}
    {nav}
</body>
</html>
"""

def render_page(title, content, show_nav=True):
    flash_html = ""
    if 'flash_messages' in session:
        flash_html = '<div class="flash-messages">' + ''.join([
            f'<div class="flash {msg["type"]}">{msg["text"]}</div>' 
            for msg in session.pop('flash_messages')
        ]) + '</div>'
        session.modified = True
    
    nav_html = get_nav() if show_nav and 'user' in session else ""
    
    return BASE_HTML.format(
        css=CSS,
        title=title,
        flash_messages=flash_html,
        content=content,
        nav=nav_html
    )

def get_nav():
    items = [
        ('/', 'الرئيسية', '🏠'),
        ('/cart', 'السلة', '🛒'),
        ('/orders_history', 'طلباتي', '📦'),
    ]
    
    if session.get('is_admin'):
        items.append(('/admin', 'التحكم', '⚙️'))
    
    items.append(('/logout', 'خروج', '🚪'))
    
    current_path = request.path
    nav_html = '<div class="bottom-nav">'
    
    for path, label, icon in items:
        active = 'active' if current_path == path else ''
        nav_html += f'<a href="{path}" class="nav-item {active}"><span class="nav-icon">{icon}</span><span>{label}</span></a>'
    
    nav_html += '</div>'
    return nav_html

# ========== المسارات ==========

@app.route('/')
@login_required
def index():
    try:
        cat = request.args.get('cat', 'الكل')
        search = request.args.get('search', '').strip()
        
        conn = get_db()
        cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        
        query = "SELECT * FROM products WHERE is_active = 1"
        params = []
        
        if cat != 'الكل':
            query += " AND category = ?"
            params.append(cat)
        
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += " ORDER BY created_at DESC"
        prods = conn.execute(query, params).fetchall()
        
        cart_count = conn.execute(
            "SELECT SUM(quantity) FROM cart WHERE user_email = ?", 
            (session['user'],)
        ).fetchone()[0] or 0
        
        conn.close()
        
        content = f"""
        <header>
            <div class="logo">👑 THAWANI STORE</div>
            <div class="user-info">مرحباً، {session['user'].split('@')[0]} | 🛒 السلة: ({cart_count})</div>
        </header>
        
        <div class="cat-bar">
            <a href="/" class="cat-item {'active' if cat == 'الكل' else ''}">الكل</a>
            {''.join([f'<a href="/?cat={c["name"]}" class="cat-item {"active" if cat == c["name"] else ""}">{c["name"]}</a>' for c in cats])}
        </div>
        
        <div style="padding: 15px;">
            <form method="GET" action="/" style="display: flex; gap: 10px; margin-bottom: 15px;">
                <input type="text" name="search" placeholder="🔍 ابحث عن منتج..." value="{search}" style="flex: 1;">
                <button type="submit" class="btn btn-gold" style="width: auto; padding: 12px 20px;">بحث</button>
            </form>
        </div>
        
        <div class="container">
            {''.join([f"""
            <div class="card">
                <div class="card-img-container">
                    {'<div class="stock-badge">✅ متوفر</div>' if p['stock'] > 0 else '<div class="out-of-stock-overlay">❌ نفذت الكمية</div>'}
                    <img src="/static/uploads/{p['img']}" loading="lazy" alt="{p['name']}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23333%22 width=%22100%22 height=%22100%22/><text fill=%22%23666%22 x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22>لا توجد صورة</text></svg>'">
                </div>
                <div class="card-body">
                    <div class="product-title">{p['name']}</div>
                    <div class="price">{p['price']:.3f} OMR</div>
                    <a href="/product/{p['id']}" class="btn btn-gold btn-block">التفاصيل 👁️</a>
                </div>
            </div>
            """ for p in prods]) if prods else '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد منتجات</h3><p>جرب تصنيف آخر أو أضف منتجات جديدة</p></div>'}
        </div>
        """
        
        return render_template_string(render_page('الرئيسية', content))
    except Exception as e:
        logger.error(f"Index error: {e}")
        flash('خطأ في تحميل الصفحة', 'error')
        return redirect(url_for('login'))

@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def product(id):
    try:
        conn = get_db()
        
        if request.method == 'POST':
            rating = request.form.get('rating', type=int)
            comment = request.form.get('comment', '').strip()
            
            if not rating or not (1 <= rating <= 5):
                save_flash_message('التقييم يجب أن يكون بين 1 و 5', 'error')
            elif not comment:
                save_flash_message('الرجاء كتابة تعليق', 'error')
            else:
                try:
                    conn.execute(
                        "INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)",
                        (id, session['user'], rating, comment)
                    )
                    conn.commit()
                    log_activity(session['user'], f'أضاف تقييم للمنتج #{id}')
                    save_flash_message('تم نشر تقييمك بنجاح! ⭐', 'success')
                except Exception as e:
                    logger.error(f"Review error: {e}")
                    save_flash_message('خطأ في إضافة التقييم', 'error')
                return redirect(url_for('product', id=id))
        
        p = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
        if not p:
            conn.close()
            abort(404)
        
        revs = conn.execute(
            "SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC", (id,)
        ).fetchall()
        
        avg_rating = conn.execute(
            "SELECT AVG(rating) FROM reviews WHERE product_id = ?", (id,)
        ).fetchone()[0] or 0
        
        conn.close()
        
        content = f"""
        <header><div class="logo">📦 تفاصيل المنتج</div></header>
        <div style="padding: 15px; max-width: 800px; margin: 0 auto;">
            <div style="position: relative;">
                <img src="/static/uploads/{p['img']}" style="width: 100%; border-radius: 15px; border: 3px solid var(--accent);" onerror="this.style.display='none'">
                {f'<div class="stock-badge" style="top: 20px; right: 20px; font-size: 14px;">المخزون: {p["stock"]} قطعة</div>' if p['stock'] > 0 else '<div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.9); padding: 20px; border-radius: 10px; font-size: 20px;">❌ نفذت الكمية</div>'}
            </div>
            
            <h2 style="color: var(--accent); margin-top: 25px;">{p['name']}</h2>
            <div style="display: flex; align-items: center; gap: 15px; margin: 15px 0;">
                <div class="stars">{'★' * int(avg_rating)}{'☆' * (5-int(avg_rating))}</div>
                <span style="color: #888;">({len(revs)} تقييم)</span>
            </div>
            <div class="price" style="font-size: 32px; margin: 20px 0;">{p['price']:.3f} OMR</div>
            <p style="color: #ccc; line-height: 1.8;">{p['description'] or 'لا يوجد وصف'}</p>
            
            {f'<a href="/add_to_cart/{p["id"]}" class="btn btn-gold btn-block btn-lg">🛒 أضف للسلة</a>' if p['stock'] > 0 else '<button class="btn btn-block btn-lg" disabled style="background: #333; color: #666;">⚠️ نفذت الكمية</button>'}
            
            <hr style="border: 0; border-top: 2px solid #333; margin: 40px 0;">
            
            <h3>⭐ تقييمات العملاء ({len(revs)})</h3>
            {''.join([f"""
            <div class="review-card">
                <div class="stars">{'★' * r['rating']}{'☆' * (5-r['rating'])}</div>
                <p style="margin: 10px 0;">{r['comment']}</p>
                <div class="review-meta">{r['user_email']} • {r['created_at'][:10]}</div>
            </div>
            """ for r in revs]) if revs else '<p style="color: #666;">لا توجد تقييمات بعد.</p>'}
            
            <div style="background: #1a1a1a; padding: 25px; border-radius: 15px; margin-top: 30px;">
                <h4 style="color: var(--accent);">أضف تقييمك</h4>
                <form method="POST">
                    <div class="form-group">
                        <label>التقييم</label>
                        <select name="rating" required>
                            <option value="5">⭐⭐⭐⭐⭐ ممتاز</option>
                            <option value="4">⭐⭐⭐⭐ جيد جداً</option>
                            <option value="3">⭐⭐⭐ متوسط</option>
                            <option value="2">⭐⭐ ضعيف</option>
                            <option value="1">⭐ سيء</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>تعليقك</label>
                        <textarea name="comment" rows="4" required></textarea>
                    </div>
                    <button class="btn btn-gold btn-block">نشر التقييم</button>
                </form>
            </div>
        </div>
        """
        
        return render_template_string(render_page(p['name'], content))
    except Exception as e:
        logger.error(f"Product error: {e}")
        flash('خطأ في تحميل المنتج', 'error')
        return redirect(url_for('index'))

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    try:
        conn = get_db()
        product = conn.execute("SELECT stock, name FROM products WHERE id = ?", (id,)).fetchone()
        
        if not product:
            conn.close()
            save_flash_message('المنتج غير موجود', 'error')
            return redirect(url_for('index'))
        
        if product['stock'] <= 0:
            conn.close()
            save_flash_message(f'❌ المنتج "{product["name"]}" غير متوفر', 'error')
            return redirect(url_for('index'))
        
        cart_item = conn.execute(
            "SELECT id, quantity FROM cart WHERE user_email = ? AND product_id = ?", 
            (session['user'], id)
        ).fetchone()
        
        if cart_item:
            new_qty = cart_item['quantity'] + 1
            if new_qty > product['stock']:
                conn.close()
                save_flash_message(f'⚠️ المخزون المتبقي: {product["stock"]}', 'warning')
                return redirect(url_for('cart'))
            
            conn.execute("UPDATE cart SET quantity = ? WHERE id = ?", (new_qty, cart_item['id']))
            message = f'تم تحديث الكمية ({new_qty})'
        else:
            conn.execute(
                "INSERT INTO cart (user_email, product_id, quantity) VALUES (?, ?, 1)", 
                (session['user'], id)
            )
            message = 'تمت إضافة المنتج للسلة'
        
        conn.commit()
        conn.close()
        
        log_activity(session['user'], f'أضاف منتج #{id} للسلة')
        save_flash_message(f'✅ {message}!', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Add to cart error: {e}")
        save_flash_message('خطأ في إضافة المنتج', 'error')
        return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    try:
        conn = get_db()
        items = conn.execute('''
            SELECT p.id, p.name, p.price, p.img, c.quantity, p.stock 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_email = ?
        ''', (session['user'],)).fetchall()
        
        total = sum(i['price'] * i['quantity'] for i in items)
        conn.close()
        
        content = f"""
        <header><div class="logo">🛒 سلة التسوق</div></header>
        <div style="padding: 15px; max-width: 700px; margin: 0 auto;">
            {''.join([f"""
            <div class="cart-item">
                <img src="/static/uploads/{i['img']}" alt="{i['name']}">
                <div class="cart-item-info">
                    <div class="cart-item-title">{i['name']}</div>
                    <div class="cart-item-price">{i['price']:.3f} OMR</div>
                    <div class="cart-item-qty">الكمية: {i['quantity']} | المخزون: {i['stock']}</div>
                </div>
                <div class="cart-item-total">
                    <div style="color: var(--accent);">{(i['price'] * i['quantity']):.3f}</div>
                    <a href="/remove_from_cart/{i['id']}" class="btn btn-red btn-sm" onclick="return confirm('حذف؟')">🗑️</a>
                </div>
            </div>
            """ for i in items]) if items else '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3>السلة فارغة</h3><a href="/" class="btn btn-gold btn-lg">تصفح المنتجات</a></div>'}
            
            {f'''
            <div style="background: var(--card); padding: 25px; border-radius: 15px; margin-top: 25px; border: 2px solid var(--accent);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                    <span style="font-size: 18px;">المجموع:</span>
                    <b style="font-size: 28px; color: var(--accent);">{total:.3f} OMR</b>
                </div>
                <a href="/checkout" class="btn btn-gold btn-block btn-lg">💳 إتمام الشراء</a>
            </div>
            ''' if items else ''}
        </div>
        """
        
        return render_template_string(render_page('السلة', content))
    except Exception as e:
        logger.error(f"Cart error: {e}")
        flash('خطأ في تحميل السلة', 'error')
        return redirect(url_for('index'))

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    try:
        conn = get_db()
        conn.execute("DELETE FROM cart WHERE user_email = ? AND product_id = ?", 
                     (session['user'], product_id))
        conn.commit()
        conn.close()
        save_flash_message('🗑️ تم الحذف من السلة', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Remove from cart error: {e}")
        save_flash_message('خطأ في الحذف', 'error')
        return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    try:
        conn = get_db()
        items = conn.execute('''
            SELECT p.id, p.name, p.price, c.quantity, p.stock 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_email = ?
        ''', (session['user'],)).fetchall()
        
        if not items:
            conn.close()
            save_flash_message('السلة فارغة', 'error')
            return redirect(url_for('index'))
        
        for item in items:
            if item['quantity'] > item['stock']:
                conn.close()
                save_flash_message(f'⚠️ المنتج "{item["name"]}" غير متوفر بالكمية المطلوبة', 'error')
                return redirect(url_for('cart'))
        
        total = sum(i['price'] * i['quantity'] for i in items)
        
        if request.method == 'POST':
            logger.info(f"Processing checkout for: {session['user']}")
            
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            receipt = request.files.get('receipt')
            
            if not name or len(name) < 2:
                save_flash_message('الاسم يجب أن يكون حرفين على الأقل', 'error')
                conn.close()
                return redirect(url_for('checkout'))
            
            if not phone or not re.match(r'^[\d\s\+\-]{8,20}$', phone):
                save_flash_message('رقم الهاتف غير صحيح', 'error')
                conn.close()
                return redirect(url_for('checkout'))
            
            filename = secure_upload(receipt)
            if not filename:
                conn.close()
                return redirect(url_for('checkout'))
            
            try:
                details = ", ".join([f"{i['name']} (x{i['quantity']})" for i in items])
                
                cursor = conn.execute('''
                    INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price, status) 
                    VALUES (?,?,?,?,?,?, 'pending')
                ''', (session['user'], name, phone, filename, details, total))
                
                order_id = cursor.lastrowid
                logger.info(f"Order created: #{order_id}")
                
                for i in items:
                    conn.execute(
                        "UPDATE products SET stock = stock - ? WHERE id = ?", 
                        (i['quantity'], i['id'])
                    )
                
                conn.execute("DELETE FROM cart WHERE user_email = ?", (session['user'],))
                conn.commit()
                
                log_activity(session['user'], f'أنشأ طلب #{order_id}')
                conn.close()
                
                save_flash_message(f'🎉 تم إنشاء طلبك! رقم الطلب: #{order_id}', 'success')
                return redirect(url_for('order_success', order_id=order_id))
                
            except Exception as e:
                logger.error(f"Checkout error: {e}")
                conn.rollback()
                conn.close()
                save_flash_message(f'خطأ في معالجة الطلب: {str(e)}', 'error')
                return redirect(url_for('checkout'))
        
        conn.close()
        
        content = f"""
        <header><div class="logo">💳 إتمام الدفع</div></header>
        <div style="padding: 15px; max-width: 600px; margin: 0 auto;">
            <div class="checkout-summary">
                <h3>📋 ملخص الطلب</h3>
                {''.join([f'<div class="summary-row"><span>{i["name"]} × {i["quantity"]}</span><span>{(i["price"] * i["quantity"]):.3f} OMR</span></div>' for i in items])}
                <div class="summary-total">
                    <span>الإجمالي:</span>
                    <span>{total:.3f} OMR</span>
                </div>
            </div>
            
            <div style="background: #1a1a1a; padding: 25px; border-radius: 15px;">
                <h4 style="color: var(--accent); margin-bottom: 20px;">معلومات التوصيل</h4>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>الاسم الكامل *</label>
                        <input name="name" required minlength="2" placeholder="محمد أحمد">
                    </div>
                    <div class="form-group">
                        <label>رقم الواتساب *</label>
                        <input name="phone" type="tel" required placeholder="+968XXXXXXXX">
                    </div>
                    <div class="form-group">
                        <label>إيصال الدفع (صورة) *</label>
                        <input type="file" name="receipt" accept="image/*" required style="padding: 20px; border-style: dashed;">
                        <small style="color: #666;">JPG, PNG, GIF (الحد الأقصى 16MB)</small>
                    </div>
                    <button type="submit" class="btn btn-gold btn-block btn-lg">✅ تأكيد الطلب</button>
                </form>
            </div>
        </div>
        """
        
        return render_template_string(render_page('إتمام الدفع', content))
    except Exception as e:
        logger.error(f"Checkout page error: {e}")
        flash('خطأ في تحميل الصفحة', 'error')
        return redirect(url_for('cart'))

@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    try:
        conn = get_db()
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ? AND user_email = ?", 
            (order_id, session['user'])
        ).fetchone()
        conn.close()
        
        if not order:
            flash('الطلب غير موجود', 'error')
            return redirect(url_for('orders_history'))
        
        content = f"""
        <header><div class="logo">🎉 تم بنجاح!</div></header>
        <div class="success-page">
            <div class="success-icon">✅</div>
            <h1 class="success-title">تم إنشاء طلبك بنجاح!</h1>
            <p class="success-message">شكراً لثقتك بنا. سنتواصل معك قريباً.</p>
            
            <div class="order-number">
                <div class="order-number-label">رقم الطلب</div>
                <div class="order-number-value">#{order['id']}</div>
            </div>
            
            <div style="background: #1a1a1a; padding: 20px; border-radius: 15px; margin: 25px 0; text-align: right;">
                <div style="margin-bottom: 15px;"><span style="color: #888;">الاسم:</span> <span style="float: left;">{order['full_name']}</span></div>
                <div style="margin-bottom: 15px;"><span style="color: #888;">الهاتف:</span> <span style="float: left;">{order['phone']}</span></div>
                <div style="margin-bottom: 15px;"><span style="color: #888;">المنتجات:</span> <div style="margin-top: 10px;">{order['items_details']}</div></div>
                <div style="border-top: 2px solid var(--accent); padding-top: 15px;">
                    <span style="color: #888;">الإجمالي:</span>
                    <span style="float: left; color: var(--accent); font-size: 24px; font-weight: bold;">{order['total_price']:.3f} OMR</span>
                </div>
            </div>
            
            <div style="display: flex; gap: 15px; justify-content: center;">
                <a href="/orders_history" class="btn btn-gold btn-lg">📦 طلباتي</a>
                <a href="/" class="btn btn-gray btn-lg">🏠 الرئيسية</a>
            </div>
        </div>
        """
        
        return render_template_string(render_page('تم بنجاح', content))
    except Exception as e:
        logger.error(f"Order success error: {e}")
        return redirect(url_for('orders_history'))

@app.route('/orders_history')
@login_required
def orders_history():
    try:
        conn = get_db()
        orders = conn.execute(
            "SELECT * FROM orders WHERE user_email = ? ORDER BY created_at DESC", 
            (session['user'],)
        ).fetchall()
        conn.close()
        
        status_map = {
            'pending': ('⏳ قيد الانتظار', 'badge-pending'),
            'approved': ('✅ تم القبول', 'badge-approved'),
            'rejected': ('❌ مرفوض', 'badge-rejected'),
            'shipped': ('🚚 تم الشحن', 'badge-shipped'),
            'delivered': ('📦 تم التوصيل', 'badge-delivered')
        }
        
        content = f"""
        <header><div class="logo">📦 طلباتي</div></header>
        <div style="padding: 15px; max-width: 800px; margin: 0 auto;">
            {''.join([f"""
            <div class="order-card">
                <div class="order-header">
                    <div>
                        <div class="order-id">طلب #{o['id']}</div>
                        <div style="color: #888; font-size: 13px;">{o['created_at'][:16]}</div>
                    </div>
                    <span class="badge {status_map.get(o['status'], ('', 'badge-pending'))[1]}">
                        {status_map.get(o['status'], (o['status'], ''))[0]}
                    </span>
                </div>
                
                <div class="order-items">
                    <div style="font-weight: bold; margin-bottom: 10px; color: var(--gold-light);">المنتجات:</div>
                    {o['items_details']}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
                    <div class="order-total">{o['total_price']:.3f} OMR</div>
                    <div>
                        <a href="/view_receipt/{o['id']}" class="btn btn-blue btn-sm">🖼️ الإيصال</a>
                    </div>
                </div>
                
                {f'<div style="margin-top: 15px; padding: 12px; background: #222; border-radius: 8px;"><strong>ملاحظات:</strong> {o["notes"]}</div>' if o['notes'] else ''}
            </div>
            """ for o in orders]) if orders else '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد طلبات</h3><a href="/" class="btn btn-gold btn-lg">ابدأ التسوق</a></div>'}
        </div>
        """
        
        return render_template_string(render_page('طلباتي', content))
    except Exception as e:
        logger.error(f"Orders history error: {e}")
        flash('خطأ في تحميل الطلبات', 'error')
        return redirect(url_for('index'))

@app.route('/view_receipt/<int:order_id>')
@login_required
def view_receipt(order_id):
    try:
        conn = get_db()
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        conn.close()
        
        if not order:
            abort(404)
        
        if order['user_email'] != session['user'] and not session.get('is_admin'):
            abort(403)
        
        receipt_path = os.path.join(app.config['UPLOAD_FOLDER'], order['card_img'])
        
        if not os.path.exists(receipt_path):
            logger.error(f"Receipt not found: {receipt_path}")
            return render_template_string(render_page('خطأ', '''
            <div class="empty-state" style="padding-top: 100px;">
                <div class="empty-state-icon">🖼️</div>
                <h2>الصورة غير موجودة</h2>
                <a href="/orders_history" class="btn btn-gold">العودة</a>
            </div>
            '''))
        
        content = f"""
        <header><div class="logo">🖼️ إيصال الدفع</div></header>
        <div style="padding: 20px; max-width: 800px; margin: 0 auto; text-align: center;">
            <div style="background: #1a1a1a; padding: 20px; border-radius: 15px; border: 2px solid var(--accent);">
                <h3 style="color: var(--accent); margin-bottom: 20px;">إيصال الطلب #{order_id}</h3>
                <img src="/static/uploads/{order['card_img']}" 
                     style="max-width: 100%; border-radius: 10px; border: 3px solid #333; cursor: pointer;"
                     onclick="window.open(this.src, '_blank')"
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22><rect fill=%22%23222%22 width=%22400%22 height=%22300%22/><text fill=%22%23666%22 x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22>لا يمكن تحميل الصورة</text></svg>'">
                <p style="color: #888; margin-top: 15px;">اضغط على الصورة لتكبيرها</p>
                <a href="/orders_history" class="btn btn-gold" style="margin-top: 20px;">⬅️ العودة للطلبات</a>
            </div>
        </div>
        """
        
        return render_template_string(render_page('إيصال الدفع', content))
    except Exception as e:
        logger.error(f"View receipt error: {e}")
        flash('خطأ في عرض الإيصال', 'error')
        return redirect(url_for('orders_history'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    try:
        conn = get_db()
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add_product':
                name = request.form.get('name', '').strip()
                price = request.form.get('price', type=float)
                cat = request.form.get('cat', '').strip()
                desc = request.form.get('desc', '').strip()
                stock = request.form.get('stock', type=int, default=0)
                img = request.files.get('img')
                
                if not all([name, price, cat, img]):
                    save_flash_message('جميع الحقول المطلوبة يجب ملؤها', 'error')
                elif price <= 0:
                    save_flash_message('السعر يجب أن يكون أكبر من صفر', 'error')
                else:
                    filename = secure_upload(img)
                    if filename:
                        try:
                            conn.execute('''
                                INSERT INTO products (name, price, img, category, description, stock) 
                                VALUES (?,?,?,?,?,?)
                            ''', (name, price, filename, cat, desc, max(0, stock)))
                            conn.commit()
                            log_activity(session['user'], f'أضاف منتج: {name}')
                            save_flash_message('تم إضافة المنتج بنجاح!', 'success')
                        except Exception as e:
                            logger.error(f"Add product error: {e}")
                            save_flash_message('خطأ في إضافة المنتج', 'error')
            
            elif action == 'add_cat':
                cat_name = request.form.get('cat_name', '').strip()
                if cat_name:
                    try:
                        conn.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
                        conn.commit()
                        save_flash_message('تم إضافة القسم', 'success')
                    except sqlite3.IntegrityError:
                        save_flash_message('هذا القسم موجود مسبقاً', 'error')
            
            elif action == 'update_order':
                order_id = request.form.get('order_id', type=int)
                status = request.form.get('status')
                notes = request.form.get('notes', '').strip()
                
                if order_id and status:
                    conn.execute(
                        "UPDATE orders SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                        (status, notes, order_id)
                    )
                    conn.commit()
                    save_flash_message(f'تم تحديث الطلب #{order_id}', 'success')
            
            elif action == 'delete_product':
                product_id = request.form.get('product_id', type=int)
                if product_id:
                    conn.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
                    conn.commit()
                    save_flash_message('تم إخفاء المنتج', 'success')
        
        stats = {
            'users': conn.execute("SELECT COUNT(DISTINCT email) FROM users").fetchone()[0],
            'orders': conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            'products': conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1").fetchone()[0],
            'pending': conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'").fetchone()[0]
        }
        
        logs = conn.execute('''
            SELECT a.*, u.is_admin 
            FROM activity_log a 
            LEFT JOIN users u ON a.user_email = u.email 
            ORDER BY a.timestamp DESC LIMIT 50
        ''').fetchall()
        
        orders = conn.execute('''
            SELECT o.*, u.email as user_email 
            FROM orders o 
            LEFT JOIN users u ON o.user_email = u.email 
            ORDER BY o.created_at DESC
        ''').fetchall()
        
        cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        products = conn.execute('''
            SELECT p.*, c.name as cat_name 
            FROM products p 
            LEFT JOIN categories c ON p.category = c.name 
            WHERE p.is_active = 1 
            ORDER BY p.created_at DESC
        ''').fetchall()
        
        conn.close()
        
        content = f"""
        <header><div class="logo">⚙️ لوحة التحكم</div></header>
        <div style="padding: 15px; max-width: 1200px; margin: 0 auto;">
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{stats['users']}</div>
                    <div class="stat-label">المستخدمين</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['orders']}</div>
                    <div class="stat-label">الطلبات</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['products']}</div>
                    <div class="stat-label">المنتجات</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{stats['pending']}</div>
                    <div class="stat-label">بانتظار الموافقة</div>
                </div>
            </div>
            
            <div class="admin-section">
                <h3>📋 سجل النشاط</h3>
                <div class="table-container">
                    <table>
                        <tr><th>المستخدم</th><th>النشاط</th><th>الوقت</th></tr>
                        {''.join([f"<tr><td>{l['user_email']} {'👑' if l['is_admin'] else ''}</td><td>{l['action']}</td><td>{l['timestamp'][:16]}</td></tr>" for l in logs])}
                    </table>
                </div>
            </div>
            
            <div class="admin-section">
                <h3>📦 إدارة الطلبات</h3>
                {''.join([f"""
                <div style="background: #222; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <b>طلب #{o['id']} - {o['full_name']}</b>
                        <span class="badge {'badge-pending' if o['status'] == 'pending' else 'badge-approved' if o['status'] == 'approved' else 'badge-rejected' if o['status'] == 'rejected' else 'badge-shipped'}">{o['status']}</span>
                    </div>
                    <div style="color: #888; font-size: 13px; margin-bottom: 10px;">
                        {o['user_email']} | {o['phone']} | {o['total_price']:.3f} OMR
                    </div>
                    <p>{o['items_details']}</p>
                    <a href="/view_receipt/{o['id']}" target="_blank" class="btn btn-blue btn-sm">🖼️ عرض الإيصال</a>
                    
                    <form method="POST" style="margin-top: 15px;">
                        <input type="hidden" name="action" value="update_order">
                        <input type="hidden" name="order_id" value="{o['id']}">
                        <div style="display: flex; gap: 10px;">
                            <select name="status" style="flex: 1;">
                                <option value="pending" {'selected' if o['status'] == 'pending' else ''}>⏳ قيد الانتظار</option>
                                <option value="approved" {'selected' if o['status'] == 'approved' else ''}>✅ قبول</option>
                                <option value="rejected" {'selected' if o['status'] == 'rejected' else ''}>❌ رفض</option>
                                <option value="shipped" {'selected' if o['status'] == 'shipped' else ''}>🚚 شحن</option>
                                <option value="delivered" {'selected' if o['status'] == 'delivered' else ''}>📦 توصيل</option>
                            </select>
                            <button class="btn btn-green btn-sm">💾 حفظ</button>
                        </div>
                        <input type="text" name="notes" placeholder="ملاحظات..." value="{o['notes'] or ''}" style="margin-top: 10px;">
                    </form>
                </div>
                """ for o in orders]) if orders else '<p style="color: #666;">لا توجد طلبات</p>'}
            </div>
            
            <div class="admin-section">
                <h3>➕ إضافة منتج</h3>
                <form method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="add_product">
                    <div style="display: grid; gap: 15px; grid-template-columns: 1fr 1fr;">
                        <div class="form-group">
                            <label>الاسم *</label>
                            <input name="name" required>
                        </div>
                        <div class="form-group">
                            <label>السعر (OMR) *</label>
                            <input name="price" type="number" step="0.001" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>القسم *</label>
                        <select name="cat" required>
                            {''.join([f'<option value="{c["name"]}">{c["name"]}</option>' for c in cats])}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>الوصف</label>
                        <textarea name="desc" rows="3"></textarea>
                    </div>
                    <div style="display: grid; gap: 15px; grid-template-columns: 1fr 1fr;">
                        <div class="form-group">
                            <label>المخزون</label>
                            <input name="stock" type="number" value="0" min="0">
                        </div>
                        <div class="form-group">
                            <label>الصورة *</label>
                            <input type="file" name="img" accept="image/*" required>
                        </div>
                    </div>
                    <button class="btn btn-gold btn-block" style="margin-top: 20px;">🚀 نشر المنتج</button>
                </form>
            </div>
            
            <div class="admin-section">
                <h3>🛍️ المنتجات</h3>
                <div class="table-container">
                    <table>
                        <tr><th>الصورة</th><th>الاسم</th><th>السعر</th><th>المخزون</th><th>إجراء</th></tr>
                        {''.join([f"""
                        <tr>
                            <td><img src="/static/uploads/{p['img']}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;"></td>
                            <td>{p['name']}</td>
                            <td>{p['price']:.3f}</td>
                            <td>{p['stock']}</td>
                            <td>
                                <form method="POST" style="display: inline;">
                                    <input type="hidden" name="action" value="delete_product">
                                    <input type="hidden" name="product_id" value="{p['id']}">
                                    <button class="btn btn-red btn-sm" onclick="return confirm('حذف؟')">🗑️</button>
                                </form>
                            </td>
                        </tr>
                        """ for p in products])}
                    </table>
                </div>
            </div>
            
            <div class="admin-section">
                <h3>📁 إضافة قسم</h3>
                <form method="POST">
                    <input type="hidden" name="action" value="add_cat">
                    <div style="display: flex; gap: 10px;">
                        <input name="cat_name" placeholder="اسم القسم" required style="flex: 1;">
                        <button class="btn btn-gold">➕ إضافة</button>
                    </div>
                </form>
            </div>
        </div>
        """
        
        return render_template_string(render_page('لوحة التحكم', content))
    except Exception as e:
        logger.error(f"Admin error: {e}")
        flash('خطأ في تحميل لوحة التحكم', 'error')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get        password = request.form.get('password', '')
        
        if not email or not password:
            save_flash_message('الرجاء إدخال البريد وكلمة المرور', 'error')
        else:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user'] = email
                session['is_admin'] = bool(user['is_admin'])
                
                conn = get_db()
                conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
                conn.commit()
                conn.close()
                
                log_activity(email, 'تسجيل دخول ناجح')
                
                next_page = request.args.get('next') or url_for('index')
                return redirect(next_page)
            else:
                # إنشاء مستخدم جديد إذا لم يكن موجوداً (للتسهيل)
                try:
                    hashed = generate_password_hash(password, method='pbkdf2:sha256')
                    conn = get_db()
                    cursor = conn.execute(
                        "INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 0)",
                        (email, hashed)
                    )
                    conn.commit()
                    conn.close()
                    
                    session['user'] = email
                    session['is_admin'] = False
                    
                    log_activity(email, 'تسجيل دخول (مستخدم جديد)')
                    save_flash_message('تم إنشاء حسابك وتسجيل الدخول!', 'success')
                    return redirect(url_for('index'))
                except sqlite3.IntegrityError:
                    log_activity(email, 'محاولة دخول فاشلة')
                    save_flash_message('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
    
    return render_template_string(render_page('تسجيل الدخول', """
    <div style="height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #000 0%, #1a1a1a 100%);">
        <div style="background: #111; padding: 40px; border-radius: 20px; border: 2px solid var(--accent); width: 90%; max-width: 400px; box-shadow: 0 20px 60px rgba(212, 175, 55, 0.2);">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 48px; margin-bottom: 10px;">👑</div>
                <h1 style="color: var(--accent); margin: 0; font-size: 32px;">THAWANI</h1>
                <p style="color: #666; margin-top: 10px;">تسوق بأناقة، ادفع بثقة</p>
            </div>
            <form method="POST">
                <div class="form-group">
                    <input name="email" type="email" placeholder="📧 بريدك الإلكتروني" required style="text-align: center;">
                </div>
                <div class="form-group">
                    <input name="password" type="password" placeholder="🔒 كلمة المرور" required style="text-align: center;">
                </div>
                <button class="btn btn-gold btn-block" style="padding: 15px; font-size: 16px;">دخول</button>
            </form>
            <p style="text-align: center; color: #888; margin-top: 20px; font-size: 12px;">
                إذا لم يكن لديك حساب، سيتم إنشاؤه تلقائياً
            </p>
        </div>
    </div>
    """, show_nav=False))

@app.route('/logout')
def logout():
    if 'user' in session:
        log_activity(session['user'], 'تسجيل خروج')
    session.clear()
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(e):
    return render_template_string(render_page('غير موجود', """
    <div class="empty-state" style="padding-top: 100px;">
        <div class="empty-state-icon" style="font-size: 100px;">🔍</div>
        <h2>الصفحة غير موجودة</h2>
        <a href="/" class="btn btn-gold">العودة للرئيسية</a>
    </div>
    """), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template_string(render_page('غير مسموح', """
    <div class="empty-state" style="padding-top: 100px;">
        <div class="empty-state-icon" style="font-size: 100px;">🚫</div>
        <h2>غير مصرح لك بالوصول</h2>
        <a href="/" class="btn btn-gold">العودة للرئيسية</a>
    </div>
    """), 403

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template_string(render_page('خطأ', """
    <div class="empty-state" style="padding-top: 100px;">
        <div class="empty-state-icon" style="font-size: 100px;">⚠️</div>
        <h2>حدث خطأ في الخادم</h2>
        <p style="color: #666;">الرجاء المحاولة مرة أخرى</p>
        <a href="/" class="btn btn-gold">إعادة المحاولة</a>
    </div>
    """), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000, debug=False)

