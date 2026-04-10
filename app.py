from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sqlite3
import uuid
import datetime
import re
import logging
from pathlib import Path

# إعداد الـ Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# مفتاح سري عشوائي أو من متغير بيئة
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# --- إعداد قاعدة البيانات المحسن ---
def get_db():
    """إدارة الاتصال بقاعدة البيانات"""
    conn = sqlite3.connect('database.db', timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # تفعيل المفاتيح الخارجية
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # جدول المستخدمين (مشفر)
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
    
    # المنتجات
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
    
    # السلة
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
    
    # الأصناف
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # سجل النشاط (بدون باسوردات!)
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
    
    # الطلبات المحسنة
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            card_img TEXT NOT NULL,
            items_details TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'shipped', 'delivered')),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # التقييمات
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
    
    # إنشاء الأدمن الافتراضي (مشفر)
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@thawani.store')
    admin_pass = os.environ.get('ADMIN_PASS', 'Admin123!')
    hashed = generate_password_hash(admin_pass, method='pbkdf2:sha256')
    
    try:
        c.execute("INSERT OR IGNORE INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", 
                  (admin_email, hashed))
    except sqlite3.IntegrityError:
        pass
    
    # صنف افتراضي
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

init_db()

# --- الديكوريتورز (المحسنات) ---
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

# --- المساعدات (Helper Functions) ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_upload(file):
    """رفع ملف آمن مع التحقق"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        flash('نوع الملف غير مسموح. استخدم: PNG, JPG, JPEG, GIF', 'error')
        return None
    
    # التحقق من حجم الملف
    file.seek(0, 2)  # الذهاب لنهاية الملف
    size = file.tell()
    file.seek(0)  # العودة للبداية
    
    if size > MAX_CONTENT_LENGTH:
        flash('حجم الملف كبير جداً (الحد الأقصى 16MB)', 'error')
        return None
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        logger.info(f"File uploaded: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Upload error: {e}")
        flash('خطأ في رفع الملف', 'error')
        return None

def log_activity(user_email, action):
    """تسجيل النشاط بدون باسوردات"""
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO activity_log (user_email, action, ip_address, user_agent) VALUES (?, ?, ?, ?)",
            (user_email, action, request.remote_addr, request.user_agent.string[:200])
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Activity log error: {e}")

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# --- التنسيق المحسن (Black & Gold Ultra + تحسينات) ---
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    :root { 
        --primary: #000; 
        --accent: #d4af37; 
        --gold-light: #f1e5ac; 
        --gold-dark: #b8860b;
        --bg: #121212; 
        --card: #1e1e1e;
        --success: #2ecc71;
        --error: #e74c3c;
        --warning: #f39c12;
    }
    
    * { box-sizing: border-box; }
    
    body { 
        font-family: 'Tajawal', sans-serif; 
        background: var(--bg); 
        margin: 0; 
        padding: 0; 
        direction: rtl; 
        color: #fff; 
        padding-bottom: 90px;
        line-height: 1.6;
    }
    
    /* Flash Messages */
    .flash-messages {
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 2000;
        width: 90%;
        max-width: 400px;
    }
    .flash {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        text-align: center;
        font-weight: bold;
        animation: slideDown 0.3s ease;
    }
    .flash.success { background: var(--success); color: #fff; }
    .flash.error { background: var(--error); color: #fff; }
    .flash.warning { background: var(--warning); color: #000; }
    
    @keyframes slideDown {
        from { transform: translateY(-100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    /* Header */
    header { 
        background: linear-gradient(135deg, #000 0%, #1a1a1a 100%); 
        padding: 20px; 
        text-align: center; 
        border-bottom: 3px solid var(--accent);
        box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
        position: sticky; 
        top:0; 
        z-index:1000; 
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
        margin-top: 5px;
    }
    
    /* Bottom Navigation */
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
        font-size: 13px; 
        font-weight: bold;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        transition: all 0.3s;
        padding: 5px 15px;
        border-radius: 10px;
    }
    .nav-item:hover { color: var(--gold-light); }
    .nav-item.active { 
        color: var(--accent); 
        background: rgba(212, 175, 55, 0.1);
    }
    .nav-icon { font-size: 20px; }
    
    /* Container & Grid */
    .container { 
        padding: 15px; 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
        gap: 15px; 
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Cards */
    .card { 
        background: var(--card); 
        border-radius: 15px; 
        border: 1px solid #333; 
        overflow: hidden;
        transition: transform 0.3s, box-shadow 0.3s;
        position: relative;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(212, 175, 55, 0.2);
        border-color: var(--accent);
    }
    .card img { 
        width: 100%; 
        height: 180px; 
        object-fit: cover;
        transition: transform 0.3s;
    }
    .card:hover img { transform: scale(1.05); }
    .card-body { padding: 15px; }
    .product-title { 
        font-weight: bold; 
        height: 45px; 
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin-bottom: 10px;
    }
    .price { 
        color: var(--accent); 
        font-weight: 900; 
        font-size: 20px;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    }
    .old-price {
        text-decoration: line-through;
        color: #666;
        font-size: 14px;
        margin-right: 10px;
    }
    .stock-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        background: var(--accent);
        color: #000;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: bold;
    }
    .out-of-stock {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: bold;
        font-size: 18px;
    }
    
    /* Buttons */
    .btn { 
        border: none; 
        padding: 12px 20px; 
        border-radius: 10px; 
        font-weight: bold; 
        cursor: pointer; 
        text-decoration: none; 
        display: inline-block;
        text-align: center;
        transition: all 0.3s;
        font-size: 14px;
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
    .btn-block { display: block; width: 100%; margin-top: 10px; }
    .btn-sm { padding: 8px 12px; font-size: 12px; }
    
    /* Forms */
    .form-group { margin-bottom: 15px; }
    label {
        display: block;
        margin-bottom: 5px;
        color: var(--gold-light);
        font-size: 14px;
    }
    input, select, textarea { 
        width: 100%; 
        padding: 14px; 
        background: #222; 
        border: 2px solid #444; 
        color: #fff; 
        border-radius: 10px; 
        transition: border-color 0.3s;
        font-family: inherit;
    }
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--accent);
    }
    input::placeholder { color: #666; }
    
    /* Tables */
    .table-container {
        overflow-x: auto;
        background: #1a1a1a;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
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
    }
    td { 
        border-bottom: 1px solid #333; 
        padding: 12px; 
        text-align: center; 
    }
    tr:hover { background: rgba(212, 175, 55, 0.05); }
    
    /* Category Bar */
    .cat-bar { 
        display: flex; 
        overflow-x: auto; 
        padding: 15px; 
        gap: 10px; 
        background: #1a1a1a;
        scrollbar-width: none;
    }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-item { 
        background: #333; 
        color: #fff; 
        padding: 8px 20px; 
        border-radius: 25px; 
        text-decoration: none; 
        font-size: 13px; 
        white-space: nowrap;
        transition: all 0.3s;
        border: 2px solid transparent;
    }
    .cat-item:hover {
        background: #444;
        border-color: var(--accent);
    }
    .cat-item.active { 
        background: var(--accent); 
        color: #000; 
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
    }
    
    /* Reviews */
    .review-card {
        background: #222;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-right: 3px solid var(--accent);
    }
    .stars { color: var(--accent); font-size: 18px; }
    .review-meta {
        color: #888;
        font-size: 12px;
        margin-top: 5px;
    }
    
    /* Order Status Badges */
    .badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-pending { background: var(--warning); color: #000; }
    .badge-approved { background: var(--success); color: #fff; }
    .badge-rejected { background: var(--error); color: #fff; }
    .badge-shipped { background: #3498db; color: #fff; }
    
    /* Empty State */
    .empty-state {
        text-align: center;
        padding: 50px 20px;
        color: #666;
    }
    .empty-state-icon {
        font-size: 60px;
        margin-bottom: 20px;
        opacity: 0.5;
    }
    
    /* Loading Spinner */
    .spinner {
        border: 3px solid #333;
        border-top: 3px solid var(--accent);
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    
    /* Responsive */
    @media (max-width: 480px) {
        .container { grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px; }
        .logo { font-size: 22px; }
        .card img { height: 150px; }
    }
    
    @media (min-width: 768px) {
        .container { grid-template-columns: repeat(3, 1fr); }
    }
    
    @media (min-width: 1024px) {
        .container { grid-template-columns: repeat(4, 1fr); }
    }
    
    /* Admin Dashboard */
    .admin-section {
        background: #1a1a1a;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .admin-section h3 {
        color: var(--accent);
        margin-top: 0;
        border-bottom: 2px solid var(--accent);
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: linear-gradient(135deg, #222, #333);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid var(--accent);
    }
    .stat-number {
        font-size: 32px;
        font-weight: 900;
        color: var(--accent);
    }
    .stat-label {
        color: #888;
        font-size: 12px;
        margin-top: 5px;
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
    """دالة مساعدة لعرض الصفحات"""
    flash_html = ""
    if 'flash_messages' in session:
        flash_html = '<div class="flash-messages">' + ''.join([
            f'<div class="flash {msg["type"]}">{msg["text"]}</div>' 
            for msg in session.pop('flash_messages')
        ]) + '</div>'
    
    nav_html = get_nav() if show_nav and 'user' in session else ""
    
    html = BASE_HTML.format(
        css=CSS,
        title=title,
        flash_messages=flash_html,
        content=content,
        nav=nav_html
    )
    return html

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

# --- المسارات (Routes) ---

@app.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'الكل')
    search = request.args.get('search', '').strip()
    
    conn = get_db()
    
    # جلب الأصناف
    cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    
    # بناء استعلام المنتجات
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
    
    # جلب عدد عناصر السلة
    cart_count = conn.execute(
        "SELECT SUM(quantity) FROM cart WHERE user_email = ?", 
        (session['user'],)
    ).fetchone()[0] or 0
    
    conn.close()
    
    content = f"""
    <header>
        <div class="logo">THAWANI STORE</div>
        <div class="user-info">مرحباً، {session['user'].split('@')[0]} | السلة: {cart_count} 🛒</div>
    </header>
    
    <div class="cat-bar">
        <a href="/" class="cat-item {'active' if cat == 'الكل' else ''}">الكل</a>
        {''.join([f'<a href="/?cat={c["name"]}" class="cat-item {"active" if cat == c["name"] else ""}">{c["name"]}</a>' for c in cats])}
    </div>
    
    <div style="padding: 15px;">
        <form method="GET" action="/" style="display: flex; gap: 10px; margin-bottom: 15px;">
            <input type="text" name="search" placeholder="ابحث عن منتج..." value="{search}" style="flex: 1;">
            <button type="submit" class="btn btn-gold" style="width: auto;">🔍</button>
        </form>
    </div>
    
    <div class="container">
        {''.join([f"""
        <div class="card">
            {'<div class="stock-badge">متوفر</div>' if p['stock'] > 0 else ''}
            <img src="/static/uploads/{p['img']}" loading="lazy" alt="{p['name']}">
            <div class="card-body">
                <div class="product-title">{p['name']}</div>
                <div class="price">{p['price']:.3f} OMR</div>
                <a href="/product/{p['id']}" class="btn btn-gold btn-block">التفاصيل</a>
            </div>
            {f'<div class="out-of-stock">نفذت الكمية</div>' if p['stock'] == 0 else ''}
        </div>
        """ for p in prods]) if prods else '<div class="empty-state"><div class="empty-state-icon">📭</div><h3>لا توجد منتجات</h3></div>'}
    </div>
    """
    
    return render_template_string(render_page('الرئيسية', content))

@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def product(id):
    conn = get_db()
    
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()
        
        if not rating or not (1 <= rating <= 5):
            flash('التقييم يجب أن يكون بين 1 و 5', 'error')
        elif not comment:
            flash('الرجاء كتابة تعليق', 'error')
        else:
            try:
                conn.execute(
                    "INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)",
                    (id, session['user'], rating, comment)
                )
                conn.commit()
                log_activity(session['user'], f'أضاف تقييم للمنتج #{id}')
                flash('تم نشر تقييمك بنجاح!', 'success')
            except Exception as e:
                logger.error(f"Review error: {e}")
                flash('خطأ في إضافة التقييم', 'error')
    
    p = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if not p:
        conn.close()
        abort(404)
    
    revs = conn.execute(
        "SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC", 
        (id,)
    ).fetchall()
    
    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM reviews WHERE product_id = ?", 
        (id,)
    ).fetchone()[0] or 0
    
    conn.close()
    
    content = f"""
    <header><div class="logo">تفاصيل المنتج</div></header>
    <div style="padding: 15px; max-width: 800px; margin: 0 auto;">
        <div style="position: relative;">
            <img src="/static/uploads/{p['img']}" style="width: 100%; border-radius: 15px; border: 2px solid var(--accent);">
            {f'<div class="stock-badge">الكمية: {p["stock"]}</div>' if p['stock'] > 0 else ''}
        </div>
        
        <h2 style="color: var(--accent); margin-top: 20px;">{p['name']}</h2>
        <div style="display: flex; align-items: center; gap: 10px; margin: 10px 0;">
            <div class="stars">{'★' * int(avg_rating)}{'☆' * (5-int(avg_rating))}</div>
            <span style="color: #888;">({len(revs)} تقييم)</span>
        </div>
        <div class="price" style="font-size: 28px; margin: 15px 0;">{p['price']:.3f} OMR</div>
        <p style="color: #ccc; line-height: 1.8;">{p['description'] or 'لا يوجد وصف'}</p>
        
        {f'<a href="/add_to_cart/{p["id"]}" class="btn btn-gold btn-block" style="font-size: 18px; padding: 15px;">🛒 أضف للسلة</a>' if p['stock'] > 0 else '<button class="btn btn-block" disabled style="background: #333; color: #666;">⚠️ نفذت الكمية</button>'}
        
        <hr style="border: 0; border-top: 2px solid #333; margin: 30px 0;">
        
        <h3>التقييمات ⭐</h3>
        {''.join([f"""
        <div class="review-card">
            <div class="stars">{'★' * r['rating']}{'☆' * (5-r['rating'])}</div>
            <p style="margin: 10px 0;">{r['comment']}</p>
            <div class="review-meta">{r['user_email']} • {r['created_at'][:10]}</div>
        </div>
        """ for r in revs]) if revs else '<p style="color: #666;">لا توجد تقييمات بعد. كن أول من يقيم!</p>'}
        
        <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-top: 20px;">
            <h4>أضف تقييمك</h4>
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
                    <textarea name="comment" rows="4" placeholder="شاركنا رأيك في المنتج..." required></textarea>
                </div>
                <button class="btn btn-gold btn-block">نشر التقييم</button>
            </form>
        </div>
    </div>
    """
    
    return render_template_string(render_page(p['name'], content))

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    conn = get_db()
    
    # التحقق من المخزون
    product = conn.execute("SELECT stock FROM products WHERE id = ?", (id,)).fetchone()
    if not product or product['stock'] <= 0:
        conn.close()
        flash('المنتج غير متوفر في المخزون', 'error')
        return redirect(url_for('index'))
    
    # التحقد من الكمية في السلة
    cart_item = conn.execute(
        "SELECT id, quantity FROM cart WHERE user_email = ? AND product_id = ?", 
        (session['user'], id)
    ).fetchone()
    
    if cart_item:
        if cart_item['quantity'] >= product['stock']:
            conn.close()
            flash('لا يمكن إضافة المزيد، الكمية محدودة', 'warning')
            return redirect(url_for('cart'))
        
        conn.execute(
            "UPDATE cart SET quantity = quantity + 1 WHERE id = ?", 
            (cart_item['id'],)
        )
    else:
        conn.execute(
            "INSERT INTO cart (user_email, product_id, quantity) VALUES (?, ?, 1)", 
            (session['user'], id)
        )
    
    conn.commit()
    conn.close()
    
    log_activity(session['user'], f'أضاف منتج #{id} للسلة')
    flash('تمت الإضافة للسلة!', 'success')
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
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
    <header><div class="logo">سلة التسوق</div></header>
    <div style="padding: 15px; max-width: 600px; margin: 0 auto;">
        {''.join([f"""
        <div style="display: flex; gap: 15px; background: #1a1a1a; padding: 15px; border-radius: 10px; margin-bottom: 15px; align-items: center;">
            <img src="/static/uploads/{i['img']}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px;">
            <div style="flex: 1;">
                <div style="font-weight: bold; margin-bottom: 5px;">{i['name']}</div>
                <div style="color: var(--accent);">{i['price']:.3f} OMR × {i['quantity']}</div>
                <div style="color: #666; font-size: 12px;">المخزون: {i['stock']}</div>
            </div>
            <div style="text-align: left;">
                <div style="font-weight: bold; font-size: 18px;">{i['price'] * i['quantity']:.3f}</div>
                <a href="/remove_from_cart/{i['id']}" class="btn btn-red btn-sm" style="margin-top: 5px;">🗑️</a>
            </div>
        </div>
        """ for i in items]) if items else '<div class="empty-state"><div class="empty-state-icon">🛒</div><h3>السلة فارغة</h3><a href="/" class="btn btn-gold">تصفح المنتجات</a></div>'}
        
        {f'''
        <div style="background: var(--card); padding: 20px; border-radius: 10px; margin-top: 20px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span>المجموع:</span>
                <b>{total:.3f} OMR</b>
            </div>
            <a href="/checkout" class="btn btn-gold btn-block" style="font-size: 18px;">💳 إتمام الدفع</a>
        </div>
        ''' if items else ''}
    </div>
    """
    
    return render_template_string(render_page('السلة', content))

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE user_email = ? AND product_id = ?", 
                 (session['user'], product_id))
    conn.commit()
    conn.close()
    flash('تم الحذف من السلة', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    conn = get_db()
    items = conn.execute('''
        SELECT p.id, p.name, p.price, c.quantity, p.stock 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_email = ?
    ''', (session['user'],)).fetchall()
    
    if not items:
        conn.close()
        flash('السلة فارغة', 'error')
        return redirect(url_for('index'))
    
    # التحقق من المخزون
    for item in items:
        if item['quantity'] > item['stock']:
            conn.close()
            flash(f'المنتج {item["name"]} غير متوفر بالكمية المطلوبة', 'error')
            return redirect(url_for('cart'))
    
    total = sum(i['price'] * i['quantity'] for i in items)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        receipt = request.files.get('receipt')
        
        # Validation
        if not name or len(name) < 3:
            flash('الاسم يجب أن يكون 3 أحرف على الأقل', 'error')
        elif not phone or not re.match(r'^\+?\d{8,15}$', phone):
            flash('رقم الهاتف غير صحيح', 'error')
        else:
            filename = secure_upload(receipt)
            if filename:
                try:
                    details = ", ".join([f"{i['name']} (x{i['quantity']})" for i in items])
                    
                    conn.execute('''
                        INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price, status) 
                        VALUES (?,?,?,?,?,?, 'pending')
                    ''', (session['user'], name, phone, filename, details, total))
                    
                    # تحديث المخزون
                    for i in items:
                        conn.execute(
                            "UPDATE products SET stock = stock - ? WHERE id = ?", 
                            (i['quantity'], i['id'])
                        )
                    
                    # تفريغ السلة
                    conn.execute("DELETE FROM cart WHERE user_email = ?", (session['user'],))
                    
                    conn.commit()
                    log_activity(session['user'], f'أنشأ طلب جديد بقيمة {total:.3f} OMR')
                    conn.close()
                    
                    flash('تم تأكيد طلبك بنجاح! سنتواصل معك قريباً', 'success')
                    return redirect(url_for('orders_history'))
                    
                except Exception as e:
                    logger.error(f"Checkout error: {e}")
                    conn.rollback()
                    flash('خطأ في معالجة الطلب', 'error')
    
    conn.close()
    
    content = f"""
    <header><div class="logo">إتمام الدفع</div></header>
    <div style="padding: 15px; max-width: 500px; margin: 0 auto;">
        <div style="background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: var(--accent);">ملخص الطلب</h3>
            {''.join([f'<div style="display: flex; justify-content: space-between; margin-bottom: 8px;"><span>{i["name"]} × {i["quantity"]}</span><span>{i["price"] * i["quantity"]:.3f} OMR</span></div>' for i in items])}
            <hr style="border-color: #333;">
            <div style="display: flex; justify-content: space-between; font-size: 20px; font-weight: bold;">
                <span>الإجمالي:</span>
                <span style="color: var(--accent);">{total:.3f} OMR</span>
            </div>
        </div>
        
        <div style="background: #1a1a1a; padding: 20px; border-radius: 10px;">
            <h4>معلومات التوصيل</h4>
            <form method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>الاسم الكامل *</label>
                    <input name="name" required minlength="3" placeholder="محمد أحمد">
                </div>
                <div class="form-group">
                    <label>رقم الواتساب *</label>
                    <input name="phone" type="tel" required placeholder="+968XXXXXXXX">
                </div>
                <div class="form-group">
                    <label>إيصال الدفع (صورة) *</label>
                    <input type="file" name="receipt" accept="image/*" required>
                    <small style="color: #666;">الصيغ المسموحة: JPG, PNG, GIF (الحد الأقصى 16MB)</small>
                </div>
                <button class="btn btn-gold btn-block" style="font-size: 18px; padding: 15px;">✅ تأكيد الطلب</button>
            </form>
        </div>
    </div>
    """
    
    return render_template_string(render_page('إتمام الدفع', content))

@app.route('/orders_history')
@login_required
def orders_history():
    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_email = ? ORDER BY created_at DESC", 
        (session['user'],)
    ).fetchall()
    conn.close()
    
    status_map = {
        'pending': ('قيد الانتظار', 'badge-pending'),
        'approved': ('تم القبول', 'badge-approved'),
        'rejected': ('مرفوض', 'badge-rejected'),
        'shipped': ('تم الشحن', 'badge-shipped'),
        'delivered': ('تم التوصيل', 'badge-delivered')
    }
    
    content = f"""
    <header><div class="logo">طلباتي</div></header>
    <div style="padding: 15px; max-width: 800px; margin: 0 auto;">
        {''.join([f"""
        <div style="background: #1a1a1a; padding: 20px; border-radius: 15px; margin-bottom: 15px; border-right: 4px solid var(--accent);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <b style="font-size: 18px;">طلب #{o['id']}</b>
                <span class="badge {status_map.get(o['status'], ('', ''))[1]}">{status_map.get(o['status'], (o['status'], ''))[0]}</span>
            </div>
            <div style="color: #888; margin-bottom: 10px;">{o['created_at'][:16]}</div>
            <div style="margin-bottom: 10px;">{o['items_details']}</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="color: var(--accent); font-size: 20px;">{o['total_price']:.3f} OMR</b>
                <a href="/static/uploads/{o['card_img']}" target="_blank" class="btn btn-blue btn-sm">📄 الإيصال</a>
            </div>
            {f'<div style="margin-top: 10px; padding: 10px; background: #222; border-radius: 5px; color: #888;">ملاحظات: {o["notes"]}</div>' if o['notes'] else ''}
        </div>
        """ for o in orders]) if orders else '<div class="empty-state"><div class="empty-state-icon">📦</div><h3>لا توجد طلبات</h3></div>'}
    </div>
    """
    
    return render_template_string(render_page('طلباتي', content))

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
            desc = request.form.get('desc', '').strip()
            stock = request.form.get('stock', type=int, default=0)
            img = request.files.get('img')
            
            if not all([name, price, cat, img]):
                flash('جميع الحقول المطلوبة يجب ملؤها', 'error')
            elif price <= 0:
                flash('السعر يجب أن يكون أكبر من صفر', 'error')
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
                        flash('تم إضافة المنتج بنجاح!', 'success')
                    except Exception as e:
                        logger.error(f"Add product error: {e}")
                        flash('خطأ في إضافة المنتج', 'error')
        
        elif action == 'add_cat':
            cat_name = request.form.get('cat_name', '').strip()
            if cat_name:
                try:
                    conn.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
                    conn.commit()
                    flash('تم إضافة القسم', 'success')
                except sqlite3.IntegrityError:
                    flash('هذا القسم موجود مسبقاً', 'error')
        
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
                flash(f'تم تحديث حالة الطلب #{order_id}', 'success')
        
        elif action == 'delete_product':
            product_id = request.form.get('product_id', type=int)
            if product_id:
                conn.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
                conn.commit()
                flash('تم إخفاء المنتج', 'success')
    
    # جلب البيانات
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
        
        <!-- الإحصائيات -->
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
        
        <!-- سجل النشاط -->
        <div class="admin-section">
            <h3>📋 سجل النشاط الأخير</h3>
            <div class="table-container">
                <table>
                    <tr><th>المستخدم</th><th>النشاط</th><th>الوقت</th></tr>
                    {''.join([f"<tr><td>{l['user_email']} {'👑' if l['is_admin'] else ''}</td><td>{l['action']}</td><td>{l['timestamp'][:16]}</td></tr>" for l in logs])}
                </table>
            </div>
        </div>
        
        <!-- إدارة الطلبات -->
        <div class="admin-section">
            <h3>📦 إدارة الطلبات</h3>
            {''.join([f"""
            <div style="background: #222; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <b>طلب #{o['id']} - {o['full_name']}</b>
                    <span class="badge {'badge-pending' if o['status'] == 'pending' else 'badge-approved' if o['status'] == 'approved' else 'badge-rejected' if o['status'] == 'rejected' else 'badge-shipped'}">{o['status']}</span>
                </div>
                <div style="color: #888; font-size: 13px; margin-bottom: 10px;">
                    📧 {o['user_email']} | 📱 {o['phone']} | 💰 {o['total_price']:.3f} OMR
                </div>
                <p style="margin: 10px 0;">{o['items_details']}</p>
                <a href="/static/uploads/{o['card_img']}" target="_blank" class="btn btn-blue btn-sm">🖼️ عرض الإيصال</a>
                
                <form method="POST" style="margin-top: 15px; display: grid; gap: 10px;">
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
                    <input type="text" name="notes" placeholder="ملاحظات للعميل..." value="{o['notes'] or ''}">
                </form>
            </div>
            """ for o in orders]) if orders else '<p style="color: #666;">لا توجد طلبات</p>'}
        </div>
        
        <!-- إضافة منتج -->
        <div class="admin-section">
            <h3>➕ إضافة منتج جديد</h3>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="add_product">
                <div style="display: grid; gap: 15px; grid-template-columns: 1fr 1fr;">
                    <div class="form-group">
                        <label>اسم المنتج *</label>
                        <input name="name" required placeholder="مثال: ساعة ذكية">
                    </div>
                    <div class="form-group">
                        <label>السعر (OMR) *</label>
                        <input name="price" type="number" step="0.001" required placeholder="10.000">
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
                    <textarea name="desc" rows="3" placeholder="وصف تفصيلي للمنتج..."></textarea>
                </div>
                <div style="display: grid; gap: 15px; grid-template-columns: 1fr 1fr;">
                    <div class="form-group">
                        <label>المخزون</label>
                        <input name="stock" type="number" value="0" min="0">
                    </div>
                    <div class="form-group">
                        <label>صورة المنتج *</label>
                        <input type="file" name="img" accept="image/*" required>
                    </div>
                </div>
                <button class="btn btn-gold btn-block" style="margin-top: 20px;">🚀 نشر المنتج</button>
            </form>
        </div>
        
        <!-- إدارة المنتجات -->
        <div class="admin-section">
            <h3>🛍️ المنتجات الحالية</h3>
            <div class="table-container">
                <table>
                    <tr><th>الصورة</th><th>الاسم</th><th>السعر</th><th>المخزون</th><th>الحالة</th><th>إجراء</th></tr>
                    {''.join([f"""
                    <tr>
                        <td><img src="/static/uploads/{p['img']}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;"></td>
                        <td>{p['name']}</td>
                        <td>{p['price']:.3f}</td>
                        <td>{p['stock']}</td>
                        <td>{'✅' if p['stock'] > 0 else '❌'}</td>
                        <td>
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="action" value="delete_product">
                                <input type="hidden" name="product_id" value="{p['id']}">
                                <button class="btn btn-red btn-sm" onclick="return confirm('هل أنت متأكد؟')">🗑️</button>
                            </form>
                        </td>
                    </tr>
                    """ for p in products])}
                </table>
            </div>
        </div>
        
        <!-- إضافة قسم -->
        <div class="admin-section">
            <h3>📁 إضافة قسم جديد</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add_cat">
                <div style="display: flex; gap: 10px;">
                    <input name="cat_name" placeholder="اسم القسم الجديد" required style="flex: 1;">
                    <button class="btn btn-gold">➕ إضافة</button>
                </div>
            </form>
        </div>
    </div>
    """
    
    return render_template_string(render_page('لوحة التحكم', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not validate_email(email):
            flash('البريد الإلكتروني غير صحيح', 'error')
        else:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user'] = email
                session['is_admin'] = bool(user['is_admin'])
                
                # تحديث آخر دخول
                conn = get_db()
                conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
                conn.commit()
                conn.close()
                
                log_activity(email, 'تسجيل دخول ناجح')
                
                next_page = request.args.get('next') or url_for('index')
                return redirect(next_page)
            else:
                log_activity(email, 'محاولة تسجيل دخول فاشلة')
                flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
    
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
            <p style="text-align: center; color: #666; margin-top: 20px; font-size: 12px;">
                ليس لديك حساب؟ <a href="#" onclick="alert('تواصل مع الإدارة لفتح حساب'); return false;" style="color: var(--accent);">تواصل معنا</a>
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
        <p style="color: #666;">فريقنا يعمل على إصلاح المشكلة</p>
        <a href="/" class="btn btn-gold">إعادة المحاولة</a>
    </div>
    """), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000, debug=False)

