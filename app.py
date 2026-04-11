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
app.secret_key = os.urandom(32).hex()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'), timeout=20)
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
            is_active INTEGER DEFAULT 1
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
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    :root {
        --primary: #1b5e20;
        --primary-light: #4caf50;
        --primary-dark: #0d3312;
        --accent: #2e7d32;
        --gold: #81c784;
        --bg: #f1f8e9;
        --card: #ffffff;
        --text: #212121;
        --text-light: #616161;
        --border: #c8e6c9;
        --success: #4caf50;
        --error: #e53935;
        --warning: #fb8c00;
    }
    
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
        font-family: 'Tajawal', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg);
        direction: rtl;
        color: var(--text);
        padding-bottom: 80px;
        line-height: 1.6;
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
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        text-align: center;
        font-weight: 500;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .flash.success { background: var(--success); color: white; }
    .flash.error { background: var(--error); color: white; }
    .flash.warning { background: var(--warning); color: white; }
    
    header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        padding: 16px 20px;
        text-align: center;
        position: sticky;
        top: 0;
        z-index: 1000;
        box-shadow: 0 2px 20px rgba(27, 94, 32, 0.3);
    }
    .logo {
        font-size: 24px;
        font-weight: 700;
        color: white;
        letter-spacing: 1px;
    }
    .user-info {
        color: var(--gold);
        font-size: 12px;
        margin-top: 4px;
        opacity: 0.9;
    }
    
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: white;
        display: flex;
        justify-content: space-around;
        padding: 12px 0 8px;
        border-top: 1px solid var(--border);
        z-index: 1000;
        box-shadow: 0 -2px 20px rgba(0,0,0,0.08);
    }
    .nav-item {
        color: var(--text-light);
        text-decoration: none;
        font-size: 11px;
        font-weight: 500;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        padding: 6px 16px;
        border-radius: 12px;
        transition: all 0.2s;
    }
    .nav-item:hover { color: var(--primary); }
    .nav-item.active {
        color: var(--primary);
        background: rgba(76, 175, 80, 0.1);
    }
    .nav-icon { font-size: 20px; }
    
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
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border);
        transition: all 0.2s;
    }
    .card:active { transform: scale(0.98); }
    .card img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        background: #e8f5e9;
    }
    .card-body { padding: 12px; }
    .product-title {
        font-size: 13px;
        font-weight: 500;
        color: var(--text);
        height: 38px;
        overflow: hidden;
        line-height: 1.4;
        margin-bottom: 8px;
    }
    .price {
        color: var(--primary);
        font-weight: 700;
        font-size: 15px;
    }
    
    .btn {
        border: none;
        padding: 10px 16px;
        border-radius: 10px;
        font-weight: 600;
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
        background: var(--primary);
        color: white;
        box-shadow: 0 2px 8px rgba(27, 94, 32, 0.3);
    }
    .btn-primary:active { transform: scale(0.98); }
    .btn-outline {
        background: transparent;
        color: var(--primary);
        border: 1.5px solid var(--primary);
    }
    .btn-block { width: 100%; margin-top: 10px; }
    .btn-sm { padding: 6px 12px; font-size: 12px; }
    .btn-danger {
        background: var(--error);
        color: white;
    }
    
    .cat-bar {
        display: flex;
        overflow-x: auto;
        padding: 12px 16px;
        gap: 8px;
        background: white;
        border-bottom: 1px solid var(--border);
        scrollbar-width: none;
    }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-item {
        background: var(--bg);
        color: var(--text-light);
        padding: 8px 16px;
        border-radius: 20px;
        text-decoration: none;
        font-size: 13px;
        font-weight: 500;
        white-space: nowrap;
        border: 1px solid var(--border);
    }
    .cat-item.active {
        background: var(--primary);
        color: white;
        border-color: var(--primary);
    }
    
    .form-group { margin-bottom: 16px; }
    label {
        display: block;
        margin-bottom: 6px;
        color: var(--text);
        font-size: 13px;
        font-weight: 500;
    }
    input, select, textarea {
        width: 100%;
        padding: 12px 14px;
        background: white;
        border: 1.5px solid var(--border);
        color: var(--text);
        border-radius: 10px;
        font-family: inherit;
        font-size: 14px;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--primary);
    }
    
    .order-card {
        background: white;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 12px;
        border: 1px solid var(--border);
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .order-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .order-id { font-weight: 600; color: var(--primary); }
    .badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .badge-pending { background: #fff3e0; color: #e65100; }
    .badge-approved { background: #e8f5e9; color: var(--primary); }
    .badge-rejected { background: #ffebee; color: var(--error); }
    
    .cart-item {
        display: flex;
        gap: 12px;
        background: white;
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid var(--border);
        align-items: center;
    }
    .cart-item img {
        width: 60px;
        height: 60px;
        object-fit: cover;
        border-radius: 8px;
        background: var(--bg);
    }
    
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: var(--text-light);
    }
    .empty-state-icon { font-size: 64px; margin-bottom: 16px; opacity: 0.5; }
    
    .admin-section {
        background: white;
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 16px;
        border: 1px solid var(--border);
    }
    .admin-section h3 {
        color: var(--primary);
        margin-bottom: 16px;
        font-size: 16px;
        font-weight: 600;
    }
    
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { background: var(--bg); color: var(--primary); padding: 10px; font-weight: 600; }
    td { border-bottom: 1px solid var(--border); padding: 10px; }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 16px;
    }
    .stat-card {
        background: var(--bg);
        padding: 16px;
        border-radius: 12px;
        text-align: center;
    }
    .stat-number { font-size: 24px; font-weight: 700; color: var(--primary); }
    .stat-label { font-size: 11px; color: var(--text-light); margin-top: 4px; }
    
    .receipt-img {
        max-width: 100%;
        border-radius: 12px;
        border: 2px solid var(--border);
        margin-top: 12px;
    }
    
    .success-page { text-align: center; padding: 40px 20px; }
    .success-icon { font-size: 80px; margin-bottom: 20px; }
    .success-title { color: var(--success); font-size: 24px; margin-bottom: 12px; }
    
    .review-img {
        max-width: 100%;
        border-radius: 8px;
        margin-top: 8px;
        border: 1px solid var(--border);
    }
    
    .delivery-track {
        background: #e0e0e0;
        height: 60px;
        border-radius: 30px;
        position: relative;
        margin: 20px 0;
        overflow: hidden;
        border: 3px solid var(--border);
    }
    
    .delivery-truck {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 32px;
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
        color: var(--text-light);
        font-size: 12px;
        margin-top: 8px;
    }
    
    .delivery-complete-box {
        background: linear-gradient(135deg, #4caf50 0%, #2e7d32 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        margin: 20px 0;
        animation: slideDown 0.5s ease;
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .review-delivery-form {
        background: white;
        padding: 20px;
        border-radius: 16px;
        margin-top: 16px;
        border: 2px solid var(--border);
    }
    
    .truck-moving {
        animation: bounce 0.5s infinite alternate;
    }
    
    @keyframes bounce {
        from { transform: translateY(-50%) translateY(0); }
        to { transform: translateY(-50%) translateY(-5px); }
    }
    
    .admin-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 24px;
    }
    
    .admin-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 10px 40px rgba(27, 94, 32, 0.3);
    }
    
    .admin-header h1 {
        font-size: 28px;
        margin-bottom: 8px;
        font-weight: 700;
    }
    
    .admin-header p {
        opacity: 0.9;
        font-size: 14px;
    }
    
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-bottom: 30px;
    }
    
    .dashboard-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border: 1px solid var(--border);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .dashboard-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .dashboard-icon {
        width: 50px;
        height: 50px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        margin-bottom: 12px;
    }
    
    .dashboard-card.primary .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.warning .dashboard-icon { background: #fff3e0; }
    .dashboard-card.success .dashboard-icon { background: #e8f5e9; }
    .dashboard-card.info .dashboard-icon { background: #e3f2fd; }
    
    .dashboard-number {
        font-size: 32px;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 4px;
    }
    
    .dashboard-label {
        color: var(--text-light);
        font-size: 13px;
    }
    
    .admin-section-new {
        background: white;
        border-radius: 20px;
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        border: 1px solid var(--border);
    }
    
    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 2px solid var(--bg);
    }
    
    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: var(--primary);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .btn-modern {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
    }
    
    .btn-modern:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(27, 94, 32, 0.3);
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
        padding: 8px 16px;
        font-size: 12px;
    }
    
    .orders-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 14px;
    }
    
    .orders-table th {
        background: var(--bg);
        color: var(--primary);
        font-weight: 600;
        padding: 16px;
        text-align: right;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .orders-table th:first-child { border-radius: 0 12px 12px 0; }
    .orders-table th:last-child { border-radius: 12px 0 0 12px; }
    
    .orders-table td {
        padding: 16px;
        border-bottom: 1px solid var(--border);
        vertical-align: middle;
    }
    
    .orders-table tr:hover td {
        background: #f9f9f9;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .status-pending { background: #fff3e0; color: #e65100; }
    .status-approved { background: #e8f5e9; color: #2e7d32; }
    .status-rejected { background: #ffebee; color: #c62828; }
    
    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
    }
    
    .product-card-admin {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--border);
        transition: all 0.3s;
    }
    
    .product-card-admin:hover {
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        transform: translateY(-3px);
    }
    
    .product-img-admin {
        width: 100%;
        height: 180px;
        object-fit: cover;
    }
    
    .product-info-admin {
        padding: 16px;
    }
    
    .product-name-admin {
        font-weight: 600;
        font-size: 15px;
        margin-bottom: 8px;
        color: var(--text);
    }
    
    .product-meta-admin {
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: var(--text-light);
        font-size: 13px;
        margin-bottom: 12px;
    }
    
    .product-price-admin {
        color: var(--primary);
        font-weight: 700;
        font-size: 18px;
    }
    
    .form-modern {
        display: grid;
        gap: 20px;
    }
    
    .form-grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }
    
    .form-group-modern {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .form-group-modern label {
        font-weight: 600;
        color: var(--text);
        font-size: 14px;
    }
    
    .form-control-modern {
        padding: 14px 16px;
        border: 2px solid var(--border);
        border-radius: 12px;
        font-size: 14px;
        transition: all 0.2s;
        background: white;
    }
    
    .form-control-modern:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 4px rgba(76, 175, 80, 0.1);
    }
    
    .tabs-container {
        display: flex;
        gap: 8px;
        margin-bottom: 24px;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0;
    }
    
    .tab-btn {
        padding: 12px 24px;
        background: none;
        border: none;
        color: var(--text-light);
        font-weight: 600;
        cursor: pointer;
        position: relative;
        transition: all 0.2s;
        font-size: 14px;
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
        gap: 6px;
        padding: 6px 14px;
        background: var(--bg);
        border-radius: 20px;
        font-size: 13px;
        color: var(--primary);
        font-weight: 500;
    }
    
    .review-card-admin {
        background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        border-right: 4px solid var(--primary);
    }
    
    .review-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    
    .reviewer-name {
        font-weight: 600;
        color: var(--primary);
    }
    
    .review-date {
        font-size: 12px;
        color: var(--text-light);
    }
    
    .review-text {
        color: var(--text);
        line-height: 1.6;
        font-size: 14px;
    }
    
    .order-id-badge {
        background: var(--primary);
        color: white;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 13px;
    }
    
    @media (max-width: 768px) {
        .dashboard-grid { grid-template-columns: repeat(2, 1fr); }
        .form-grid-2 { grid-template-columns: 1fr; }
        .admin-container { padding: 16px; }
        .orders-table { font-size: 12px; }
        .orders-table th, .orders-table td { padding: 12px 8px; }
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
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
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
    
    return render_template_string(render_page('الرئيسية', f"""
    <header>
        <div class="logo">THAWANI</div>
        <div class="user-info">{session['user'].split('@')[0]} | السلة: {cart_count} | {'👑 أدمن' if session.get('is_admin') else '👤 عميل'}</div>
    </header>
    <div class="cat-bar">
        <a href="/" class="cat-item {'active' if cat=='الكل' else ''}">الكل</a>
        {''.join([f'<a href="/?cat={c["name"]}" class="cat-item {"active" if cat==c["name"] else ""}">{c["name"]}</a>' for c in cats])}
    </div>
    <div class="container">
        {''.join([f'''
        <div class="card">
            <img src="/static/uploads/{p["img"]}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e8f5e9%22 width=%22100%22 height=%22100%22/></svg>'">
            <div class="card-body">
                <div class="product-title">{p["name"]}</div>
                <div class="price">{p["price"]:.3f} OMR</div>
                <a href="/product/{p["id"]}" class="btn btn-primary btn-block">التفاصيل</a>
            </div>
        </div>
        ''' for p in prods]) if prods else '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد منتجات</h3></div>'}
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
    
    return render_template_string(render_page('المنتج', f"""
    <header><div class="logo">تفاصيل المنتج</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        <img src="/static/uploads/{p['img']}" style="width:100%; border-radius:16px; margin-bottom:16px;">
        <h2 style="color:var(--primary); margin-bottom:8px;">{p['name']}</h2>
        <div class="price" style="font-size:22px; margin-bottom:12px;">{p['price']:.3f} OMR</div>
        <p style="color:var(--text-light); margin-bottom:20px;">{p['description'] or ''}</p>
        <a href="/add_to_cart/{p['id']}" class="btn btn-primary btn-block btn-lg">أضف للسلة</a>
        
        <div style="margin-top: 30px;">
            <h3 style="margin-bottom: 16px;">التقييمات ({len(revs)})</h3>
            {''.join([f'''
            <div style="background:white; padding:12px; border-radius:12px; margin-bottom:10px; border:1px solid var(--border);">
                <div style="color:var(--primary); margin-bottom:4px;">{"★"*r["rating"]}</div>
                <p style="font-size:13px;">{r["comment"]}</p>
                {f'<img src="/static/uploads/{r["review_img"]}" class="review-img" onclick="window.open(this.src)">' if r["review_img"] else ''}
                <div style="color:var(--text-light); font-size:11px; margin-top:8px;">{r["user_email"][:20]}...</div>
            </div>
            ''' for r in revs])}
            
            <form method="POST" enctype="multipart/form-data" style="margin-top: 20px;">
                <div class="form-group">
                    <select name="rating" class="btn btn-outline" style="width: auto;">
                        <option value="5">⭐⭐⭐⭐⭐</option>
                        <option value="4">⭐⭐⭐⭐</option>
                        <option value="3">⭐⭐⭐</option>
                        <option value="2">⭐⭐</option>
                        <option value="1">⭐</option>
                    </select>
                </div>
                <div class="form-group">
                    <textarea name="comment" placeholder="رأيك في المنتج..." rows="3" required></textarea>
                </div>
                <div class="form-group">
                    <label>📷 صورة (اختياري)</label>
                    <input type="file" name="review_img" accept="image/*" style="padding:10px;">
                </div>
                <button class="btn btn-primary btn-block">نشر التقييم</button>
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
        SELECT p.id, p.name, p.price, p.img, c.quantity 
        FROM cart c JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    total = sum(i['price']*i['quantity'] for i in items)
    conn.close()
    
    return render_template_string(render_page('السلة', f"""
    <header><div class="logo">سلة التسوق</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {''.join([f'''
        <div class="cart-item">
            <img src="/static/uploads/{i["img"]}">
            <div style="flex:1;">
                <div style="font-weight:600; font-size:14px;">{i["name"]}</div>
                <div style="color:var(--primary); font-size:13px;">{i["price"]:.3f} × {i["quantity"]}</div>
            </div>
            <div style="text-align:left;">
                <div style="font-weight:700;">{(i["price"]*i["quantity"]):.3f}</div>
                <a href="/remove_from_cart/{i["id"]}" class="btn btn-sm" style="color:var(--error);">حذف</a>
            </div>
        </div>
        ''' for i in items]) if items else '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3>السلة فارغة</h3></div>'}
        
        {f'<div style="background:white; padding:16px; border-radius:16px; margin-top:16px;"><div style="display:flex; justify-content:space-between; margin-bottom:16px;"><span>الإجمالي:</span><b style="color:var(--primary); font-size:20px;">{total:.3f} OMR</b></div><a href="/checkout" class="btn btn-primary btn-block">إتمام الطلب</a></div>' if items else ''}
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
        SELECT p.name, p.price, c.quantity 
        FROM cart c JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    if not items:
        conn.close()
        return redirect('/cart')
    
    total = sum(i['price']*i['quantity'] for i in items)
    
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
                        INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (session['user'], name, phone, filename, details, total))
                    
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
    
    return render_template_string(render_page('إتمام الطلب', f"""
    <header><div class="logo">إتمام الطلب</div></header>
    <div style="padding: 16px; max-width: 500px; margin: 0 auto;">
        <div style="background:white; padding:16px; border-radius:16px; margin-bottom:16px;">
            <h3 style="margin-bottom:12px; color:var(--primary);">ملخص الطلب</h3>
            {''.join([f'<div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px;"><span>{i["name"]} × {i["quantity"]}</span><span>{(i["price"]*i["quantity"]):.3f}</span></div>' for i in items])}
            <div style="border-top:2px solid var(--border); margin-top:12px; padding-top:12px; display:flex; justify-content:space-between; font-weight:700;">
                <span>الإجمالي</span>
                <span style="color:var(--primary);">{total:.3f} OMR</span>
            </div>
        </div>
        
        <form method="POST" enctype="multipart/form-data" style="background:white; padding:20px; border-radius:16px;">
            <div class="form-group">
                <label>الاسم الكامل</label>
                <input name="name" required placeholder="محمد أحمد">
            </div>
            <div class="form-group">
                <label>رقم الهاتف</label>
                <input name="phone" type="tel" required placeholder="+968XXXXXXXX">
            </div>
            <div class="form-group">
                <label>إيصال الدفع</label>
                <input type="file" name="receipt" accept="image/*" required style="padding:20px;">
            </div>
            <button type="submit" class="btn btn-primary btn-block">تأكيد الطلب</button>
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
        <div class="success-icon">✅</div>
        <h1 class="success-title">تم إنشاء طلبك!</h1>
        <div class="order-number" style="margin: 20px auto; max-width: 300px;">
            <div class="order-number-label">رقم الطلب</div>
            <div class="order-number-value" style="color:var(--primary);">#{order['id']}</div>
        </div>
        <a href="/orders" class="btn btn-primary">طلباتي</a>
    </div>
    """, show_nav=True))

@app.route('/orders')
@login_required
def orders_history():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", 
                         (session['user'],)).fetchall()
    conn.close()
    
    status_text = {
        'pending': ('قيد المراجعة', 'badge-pending'),
        'approved': ('تم القبول - جاري التوصيل', 'badge-approved'),
        'rejected': ('مرفوض', 'badge-rejected')
    }
    
    return render_template_string(render_page('طلباتي', f"""
    <header><div class="logo">طلباتي</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {''.join([f'''
        <div class="order-card" id="order-{o["id"]}">
            <div class="order-header">
                <span class="order-id">طلب #{o["id"]}</span>
                <span class="badge {status_text.get(o["status"], ("", "badge-pending"))[1]}">
                    {status_text.get(o["status"], (o["status"], ""))[0]}
                </span>
            </div>
            <div style="color:var(--text-light); font-size:12px; margin-bottom:8px;">{o["created_at"][:16]}</div>
            <div style="background:var(--bg); padding:12px; border-radius:8px; margin:12px 0; font-size:13px;">
                {o["items_details"]}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:var(--primary); font-weight:700; font-size:18px;">{o["total_price"]:.3f} OMR</span>
                <a href="/view_receipt/{o["id"]}" class="btn btn-outline btn-sm">عرض الإيصال</a>
            </div>
            
            {f"""
            <div class="delivery-section" style="margin-top: 20px;">
                {f'''
                <div class="delivery-complete-box">
                    <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                    <h3 style="margin-bottom: 10px;">تم وصول طلبك بنجاح!</h3>
                    <p style="opacity: 0.9; margin-bottom: 15px;">نأمل أن تكون تجربتك معنا ممتازة</p>
                    
                    {f'<div style="background: rgba(255,255,255,0.2); padding: 10px; border-radius: 8px; margin-top: 10px;"><strong>تقييمك:</strong> {o["delivery_review"]}</div>' if o["delivery_review"] else f"""
                    <div class="review-delivery-form">
                        <h4 style="color: var(--primary); margin-bottom: 12px;">قيّم خدمة التوصيل</h4>
                        <form method="POST" action="/submit_delivery_review/{o['id']}">
                            <textarea name="review" placeholder="مثال: الطلب ممتاز وصلني بسرعة..." 
                                      style="width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 10px; resize: vertical;" 
                                      rows="3" required></textarea>
                            <button type="submit" class="btn btn-primary btn-block" style="background: white; color: var(--primary);">
                                إرسال التقييم ⭐
                            </button>
                        </form>
                    </div>
                    """}
                </div>
                ''' if o["delivered"] else f'''
                <div style="background: white; padding: 15px; border-radius: 12px; border: 2px solid var(--border);">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; color: var(--primary); font-weight: 600;">
                        <span>🚚</span>
                        <span>حالة التوصيل</span>
                    </div>
                    <div class="delivery-track">
                        <div class="track-line" id="track-line-{o['id']}" style="width: 0%;"></div>
                        <div class="delivery-truck truck-moving" id="truck-{o['id']}" style="right: 10px;">🚛</div>
                    </div>
                    <div class="delivery-info" id="delivery-info-{o['id']}">
                        جاري حساب وقت التوصيل...
                    </div>
                </div>
                
                <script>
                    (function() {{
                        const orderId = {o['id']};
                        const acceptedAt = new Date("{o['accepted_at']}");
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
                                    info.innerHTML = '<span style="color: var(--success); font-weight: 600;">🎉 وصلت الشاحنة! جاري تحديث الصفحة...</span>';
                                    setTimeout(() => location.reload(), 2000);
                                }} else {{
                                    info.innerHTML = 'الوقت المتبقي: ' + daysLeft + ' يوم و ' + hoursLeft + ' ساعة';
                                }}
                            }}
                        }}
                        
                        updateDelivery();
                        setInterval(updateDelivery, 3600000);
                    }})();
                </script>
                '''}
            </div>
            """ if o["status"] == "approved" and o["accepted_at"] else ""}
            
            {f'<div style="margin-top:8px; padding:8px 12px; background:#fff3e0; border-radius:8px; font-size:12px;"><strong>ملاحظة:</strong> {o["notes"]}</div>' if o["notes"] and o["status"] != "approved" else ''}
        </div>
        ''' for o in orders]) if orders else '<div class="empty-state"><div class="empty-state-icon">📦</div><h3>لا توجد طلبات</h3></div>'}
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
        <div style="background: white; padding: 20px; border-radius: 16px;">
            <h3 style="margin-bottom: 16px; color: var(--primary);">طلب #{order_id}</h3>
            <img src="/static/uploads/{order['card_img']}" class="receipt-img" 
                 onclick="window.open(this.src, '_blank')" style="cursor: pointer;">
            <a href="/orders" class="btn btn-outline" style="margin-top: 16px;">العودة</a>
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
            
            if name and price and cat and img:
                filename = save_upload(img)
                if filename:
                    conn.execute('''
                        INSERT INTO products (name, price, img, category, description, stock)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (name, price, filename, cat, request.form.get('desc', ''), stock))
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
    conn.close()
    
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
                <div class="dashboard-label">إجمالي الطلبات</div>
            </div>
            <div class="dashboard-card success">
                <div class="dashboard-icon">🛍️</div>
                <div class="dashboard-number">{stats['products']}</div>
                <div class="dashboard-label">المنتجات النشطة</div>
            </div>
            <div class="dashboard-card info">
                <div class="dashboard-icon">⏳</div>
                <div class="dashboard-number">{stats['pending']}</div>
                <div class="dashboard-label">طلبات بانتظار</div>
            </div>
        </div>
        
        <div class="tabs-container">
            <button class="tab-btn active" onclick="showTab('orders')">📋 الطلبات</button>
            <button class="tab-btn" onclick="showTab('products')">🛍️ المنتجات</button>
            <button class="tab-btn" onclick="showTab('add-product')">➕ إضافة منتج</button>
            <button class="tab-btn" onclick="showTab('categories')">📁 الأصناف</button>
            <button class="tab-btn" onclick="showTab('reviews')">⭐ تقييمات التوصيل</button>
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
                            {''.join([f'''
                            <tr>
                                <td><span class="order-id-badge">#{o["id"]}</span></td>
                                <td>
                                    <div style="font-weight: 600;">{o["full_name"]}</div>
                                    <div style="font-size: 12px; color: var(--text-light);">{o["phone"]}</div>
                                </td>
                                <td style="max-width: 250px; font-size: 12px;">{o["items_details"]}</td>
                                <td style="font-weight: 700; color: var(--primary);">{o["total_price"]:.3f} OMR</td>
                                <td>
                                    <span class="status-badge status-{o['status']}">
                                        {"⏳" if o["status"]=="pending" else "✅" if o["status"]=="approved" else "❌"} 
                                        {"قيد المراجعة" if o["status"]=="pending" else "تم القبول" if o["status"]=="approved" else "مرفوض"}
                                    </span>
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
                            ''' for o in orders])}
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
                    {''.join([f'''
                    <div class="product-card-admin">
                        <img src="/static/uploads/{p["img"]}" class="product-img-admin" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22180%22><rect fill=%22%23e8f5e9%22 width=%22300%22 height=%22180%22/></svg>'">
                        <div class="product-info-admin">
                            <div class="product-name-admin">{p["name"]}</div>
                            <div class="product-meta-admin">
                                <span class="category-tag">{p["category"]}</span>
                                <span>مخزون: {p["stock"]}</span>
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
                    ''' for p in products])}
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
                                {''.join([f'<option value="{c["name"]}">{c["name"]}</option>' for c in cats])}
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
                            {''.join([f'<span class="category-tag" style="font-size: 14px; padding: 10px 18px;">{c["name"]}</span>' for c in cats])}
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
                {''.join([f'''
                <div class="review-card-admin">
                    <div class="review-header">
                        <div>
                            <span class="order-id-badge" style="margin-left: 10px;">طلب #{r["order_id_num"]}</span>
                            <span class="reviewer-name">{r["user_email"][:30]}...</span>
                        </div>
                        <span class="review-date">{r["created_at"][:16] if r["created_at"] else ''}</span>
                    </div>
                    <div class="review-text">{r["review"]}</div>
                </div>
                ''' for r in delivery_reviews]) if delivery_reviews else '<div style="text-align: center; padding: 40px; color: var(--text-light);">لا توجد تقييمات بعد</div>'}
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
            conn.close()
            return redirect('/')
        else:
            try:
                hashed = generate_password_hash(password)
                conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed))
                conn.commit()
                session['user'] = email
                session['is_admin'] = False
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

