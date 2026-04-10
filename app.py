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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ✅ الأدمن الصحيح
    ADMIN_EMAIL = "qwerasdf1234598760@gmail.com"
    ADMIN_PASS = "qaws54321"
    
    hashed = generate_password_hash(ADMIN_PASS)
    
    # حذف الأدمن القديم وإضافة الجديد
    try:
        c.execute("DELETE FROM users WHERE email=?", (ADMIN_EMAIL,))
        c.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", 
                  (ADMIN_EMAIL, hashed))
        logger.info(f"Admin created: {ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"Admin creation error: {e}")
    
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
        if comment:
            conn.execute("INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)",
                        (id, session['user'], rating, comment))
            conn.commit()
    
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
            {''.join([f'<div style="background:white; padding:12px; border-radius:12px; margin-bottom:10px; border:1px solid var(--border);"><div style="color:var(--primary); margin-bottom:4px;">{"★"*r["rating"]}</div><p style="font-size:13px;">{r["comment"]}</p></div>' for r in revs])}
            
            <form method="POST" style="margin-top: 20px;">
                <div class="form-group">
                    <select name="rating" class="btn btn-outline" style="width: auto;">
                        <option value="5">⭐⭐⭐⭐⭐</option>
                        <option value="4">⭐⭐⭐⭐</option>
                        <option value="3">⭐⭐⭐</option>
                    </select>
                </div>
                <div class="form-group">
                    <textarea name="comment" placeholder="رأيك في المنتج..." rows="3" required></textarea>
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
        'approved': ('تم القبول', 'badge-approved'),
        'rejected': ('مرفوض', 'badge-rejected')
    }
    
    return render_template_string(render_page('طلباتي', f"""
    <header><div class="logo">طلباتي</div></header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {''.join([f'''
        <div class="order-card">
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
            {f'<div style="margin-top:8px; padding:8px 12px; background:#fff3e0; border-radius:8px; font-size:12px;"><strong>ملاحظة:</strong> {o["notes"]}</div>' if o["notes"] else ''}
        </div>
        ''' for o in orders]) if orders else '<div class="empty-state"><div class="empty-state-icon">📦</div><h3>لا توجد طلبات</h3></div>'}
    </div>
    """))

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
        
        elif action == 'add_cat':
            name = request.form.get('cat_name', '').strip()
            if name:
                try:
                    conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                    conn.commit()
                except:
                    pass
        
        elif action == 'update_order':
            oid = request.form.get('order_id', type=int)
            status = request.form.get('status')
            notes = request.form.get('notes', '')
            if oid and status:
                conn.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, oid))
                conn.commit()
    
    stats = {
        'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'orders': conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        'products': conn.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0],
        'pending': conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    }
    
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    products = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template_string(render_page('لوحة التحكم', f"""
    <header><div class="logo">لوحة التحكم</div></header>
    <div style="padding: 16px; max-width: 900px; margin: 0 auto;">
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{stats['users']}</div><div class="stat-label">المستخدمين</div></div>
            <div class="stat-card"><div class="stat-number">{stats['orders']}</div><div class="stat-label">الطلبات</div></div>
            <div class="stat-card"><div class="stat-number">{stats['products']}</div><div class="stat-label">المنتجات</div></div>
            <div class="stat-card"><div class="stat-number">{stats['pending']}</div><div class="stat-label">بانتظار</div></div>
        </div>
        
        <div class="admin-section">
            <h3>📦 الطلبات</h3>
            {''.join([f'''
            <div style="background:var(--bg); padding:12px; border-radius:12px; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <b>#{o["id"]} - {o["full_name"]}</b>
                    <span class="badge {"badge-pending" if o["status"]=="pending" else "badge-approved" if o["status"]=="approved" else "badge-rejected"}">{o["status"]}</span>
                </div>
                <div style="font-size:12px; color:var(--text-light); margin-bottom:8px;">{o["items_details"]}</div>
                <div style="font-size:12px; margin-bottom:8px;">{o["total_price"]:.3f} OMR | {o["phone"]}</div>
                <a href="/view_receipt/{o["id"]}" target="_blank" class="btn btn-sm btn-outline">الإيصال</a>
                <form method="POST" style="margin-top:8px; display:flex; gap:8px;">
                    <input type="hidden" name="action" value="update_order">
                    <input type="hidden" name="order_id" value="{o["id"]}">
                    <select name="status" class="btn btn-outline" style="flex:1; padding:6px;">
                        <option value="pending" {"selected" if o["status"]=="pending" else ""}>قيد المراجعة</option>
                        <option value="approved" {"selected" if o["status"]=="approved" else ""}>قبول</option>
                        <option value="rejected" {"selected" if o["status"]=="rejected" else ""}>رفض</option>
                    </select>
                    <input type="text" name="notes" placeholder="ملاحظات" value="{o["notes"] or ""}" style="flex:2;">
                    <button class="btn btn-primary btn-sm">حفظ</button>
                </form>
            </div>
            ''' for o in orders[:20]])}
        </div>
        
        <div class="admin-section">
            <h3>➕ منتج جديد</h3>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="add_product">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div class="form-group"><label>الاسم</label><input name="name" required></div>
                    <div class="form-group"><label>السعر</label><input name="price" type="number" step="0.001" required></div>
                </div>
                <div class="form-group">
                    <label>القسم</label>
                    <select name="cat" required><option value=""></option>{''.join([f'<option value="{c["name"]}">{c["name"]}</option>' for c in cats])}</select>
                </div>
                <div class="form-group"><label>الوصف</label><textarea name="desc" rows="2"></textarea></div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div class="form-group"><label>المخزون</label><input name="stock" type="number" value="0"></div>
                    <div class="form-group"><label>الصورة</label><input type="file" name="img" accept="image/*" required></div>
                </div>
                <button class="btn btn-primary btn-block">إضافة</button>
            </form>
        </div>
        
        <div class="admin-section">
            <h3>📁 قسم جديد</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add_cat">
                <div style="display:flex; gap:8px;">
                    <input name="cat_name" placeholder="اسم القسم" required style="flex:1;">
                    <button class="btn btn-primary">إضافة</button>
                </div>
            </form>
        </div>
        
        <div class="admin-section">
            <h3>🛍️ المنتجات</h3>
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>الصورة</th><th>الاسم</th><th>السعر</th><th>المخزون</th></tr>
                    {''.join([f'<tr><td><img src="/static/uploads/{p["img"]}" style="width:40px; height:40px; object-fit:cover; border-radius:6px;"></td><td>{p["name"]}</td><td>{p["price"]:.3f}</td><td>{p["stock"]}</td></tr>' for p in products[:10]])}
                </table>
            </div>
        </div>
    </div>
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
            conn.close()
            logger.info(f"Login successful: {email} (admin={user['is_admin']})")
            return redirect('/')
        else:
            # إنشاء حساب جديد
            try:
                hashed = generate_password_hash(password)
                conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed))
                conn.commit()
                session['user'] = email
                session['is_admin'] = False
                conn.close()
                logger.info(f"New user created: {email}")
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
