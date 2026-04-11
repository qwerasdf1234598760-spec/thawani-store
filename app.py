from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sqlite3
import uuid
import logging
import datetime

# ==========================================
# إعدادات التطبيق الأساسية
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# دوال قاعدة البيانات
# ==========================================
def get_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'database.db'), timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المنتجات
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
    
    # جدول سلة المشتريات
    c.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            UNIQUE(user_email, product_id)
        )
    ''')
    
    # جدول الأصناف (التصنيفات)
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # جدول الطلبات (تم إضافة accepted_at)
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
            accepted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # تحديث جدول الطلبات القديم إذا لم يكن يحتوي على accepted_at
    try:
        c.execute('ALTER TABLE orders ADD COLUMN accepted_at TIMESTAMP')
    except sqlite3.OperationalError:
        pass # العمود موجود مسبقاً
    
    # جدول تقييمات المنتجات
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
    
    # جدول تقييمات التوصيل (الميزة الجديدة)
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إضافة حساب الأدمن الافتراضي
    ADMIN_EMAIL = "qwerasdf1234598760@gmail.com"
    ADMIN_PASS = "qaws54321"
    hashed = generate_password_hash(ADMIN_PASS)
    
    try:
        c.execute("DELETE FROM users WHERE email=?", (ADMIN_EMAIL,))
        c.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)", (ADMIN_EMAIL, hashed))
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
    
    # إضافة صنف افتراضي إذا كانت الأصناف فارغة
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# دوال الحماية والمساعدات
# ==========================================
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
        return None
    
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filename

# ==========================================
# التنسيقات (CSS) وقوالب HTML (بدون اختصار)
# ==========================================
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
        padding-bottom: 90px;
        line-height: 1.6;
    }
    
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
    
    .nav-item:hover, .nav-item.active {
        color: var(--primary);
        background: rgba(76, 175, 80, 0.1);
    }
    
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
    }
    
    .card img {
        width: 100%;
        height: 140px;
        object-fit: cover;
        background: #e8f5e9;
    }
    
    .btn {
        border: none;
        padding: 12px 16px;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        font-size: 14px;
        font-family: inherit;
        transition: all 0.2s;
        width: 100%;
        margin-top: 10px;
    }
    
    .btn-primary { background: var(--primary); color: white; }
    .btn-sm { padding: 6px 12px; font-size: 12px; width: auto; }
    .btn-outline { background: transparent; color: var(--primary); border: 1.5px solid var(--primary); }
    
    input, select, textarea {
        width: 100%;
        padding: 12px 14px;
        background: white;
        border: 1.5px solid var(--border);
        color: var(--text);
        border-radius: 10px;
        font-family: inherit;
        font-size: 14px;
        margin-bottom: 12px;
    }
    
    input:focus, select:focus, textarea:focus {
        outline: none;
        border-color: var(--primary);
    }
    
    .order-card {
        background: white;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 16px;
        border: 1px solid var(--border);
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    .flash-messages {
        padding: 10px;
        text-align: center;
        font-weight: bold;
    }
    
    /* تنسيقات الشاحنة الخاصة */
    .truck-container {
        margin-top: 20px;
        padding: 10px;
        background: #fafafa;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
    }
    .truck-track {
        background: #e0e0e0;
        height: 40px;
        position: relative;
        border-radius: 20px;
        overflow: hidden;
        margin-bottom: 10px;
        border: 2px solid #ccc;
    }
    .truck-icon {
        position: absolute;
        right: 0;
        top: 3px;
        font-size: 24px;
        z-index: 2;
    }
    .truck-progress {
        height: 100%;
        background: linear-gradient(90deg, rgba(76,175,80,0.2) 0%, rgba(76,175,80,0.6) 100%);
        width: 0%;
        position: absolute;
        right: 0;
        top: 0;
    }
    
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; }
    th { background: var(--bg); color: var(--primary); padding: 12px; border: 1px solid var(--border); }
    td { padding: 12px; border: 1px solid var(--border); }
</style>
"""

def generate_base_html(title, body_content, show_nav=True):
    nav_html = ""
    if show_nav and 'user' in session:
        nav_html = f"""
        <div class="bottom-nav">
            <a href="/" class="nav-item">
                <span style="font-size: 22px;">🏠</span>
                <span>الرئيسية</span>
            </a>
            <a href="/cart" class="nav-item">
                <span style="font-size: 22px;">🛒</span>
                <span>السلة</span>
            </a>
            <a href="/orders" class="nav-item">
                <span style="font-size: 22px;">📦</span>
                <span>طلباتي</span>
            </a>
        """
        if session.get('is_admin'):
            nav_html += f"""
            <a href="/admin" class="nav-item">
                <span style="font-size: 22px;">⚙️</span>
                <span>التحكم</span>
            </a>
            """
        nav_html += f"""
            <a href="/logout" class="nav-item">
                <span style="font-size: 22px;">🚪</span>
                <span>خروج</span>
            </a>
        </div>
        """
        
    flash_html = ""
    messages = session.pop('_flashes', [])
    if messages:
        for category, message in messages:
            flash_html += f'<div class="flash-messages" style="color: {"green" if category == "success" else "red"};">{message}</div>'

    return f"""
    <!DOCTYPE html>
    <html dir='rtl' lang='ar'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        {CSS}
        <title>{title} | THAWANI STORE</title>
    </head>
    <body>
        {flash_html}
        {body_content}
        {nav_html}
    </body>
    </html>
    """

# ==========================================
# المسارات والصفحات (Routes)
# ==========================================

@app.route('/')
@login_required
def index():
    cat = request.args.get('cat', 'الكل')
    conn = get_db()
    
    categories = conn.execute("SELECT * FROM categories").fetchall()
    if cat == 'الكل':
        products = conn.execute("SELECT * FROM products WHERE is_active=1").fetchall()
    else:
        products = conn.execute("SELECT * FROM products WHERE is_active=1 AND category=?", (cat,)).fetchall()
    
    conn.close()
    
    cat_html = '<div style="display:flex; overflow-x:auto; padding:16px; gap:10px; background:white; border-bottom:1px solid var(--border);">'
    cat_html += f'<a href="/" class="btn-sm {"btn-primary" if cat == "الكل" else "btn-outline"}" style="border-radius:20px; text-decoration:none; white-space:nowrap;">الكل</a>'
    for c in categories:
        active_class = "btn-primary" if cat == c["name"] else "btn-outline"
        cat_html += f'<a href="/?cat={c["name"]}" class="btn-sm {active_class}" style="border-radius:20px; text-decoration:none; white-space:nowrap;">{c["name"]}</a>'
    cat_html += '</div>'
    
    prod_html = '<div class="container">'
    if products:
        for p in products:
            prod_html += f"""
            <div class="card">
                <img src="/static/uploads/{p['img']}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23e8f5e9%22 width=%22100%22 height=%22100%22/></svg>'">
                <div style="padding: 12px;">
                    <div style="font-size: 14px; font-weight: bold; height: 42px; overflow: hidden; margin-bottom: 8px;">{p['name']}</div>
                    <div style="color: var(--primary); font-size: 16px; font-weight: bold;">{p['price']:.3f} OMR</div>
                    <a href="/product/{p['id']}" class="btn btn-primary">التفاصيل</a>
                </div>
            </div>
            """
    else:
        prod_html += '<div style="grid-column: span 2; text-align: center; padding: 40px; color: var(--text-light);">لا توجد منتجات حالياً</div>'
    prod_html += '</div>'
    
    body = f"""
    <header>
        <div class="logo">THAWANI STORE</div>
    </header>
    {cat_html}
    {prod_html}
    """
    
    return render_template_string(generate_base_html('الرئيسية', body))

@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def product(id):
    conn = get_db()
    
    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()
        review_img = request.files.get('review_img')
        img_filename = save_upload(review_img) if review_img else None
        
        if comment:
            conn.execute(
                "INSERT INTO reviews (product_id, user_email, rating, comment, review_img) VALUES (?,?,?,?,?)",
                (id, session['user'], rating, comment, img_filename)
            )
            conn.commit()
            return redirect(f'/product/{id}')
            
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    
    if not p:
        abort(404)
        
    reviews_html = ""
    for r in reviews:
        img_html = f'<img src="/static/uploads/{r["review_img"]}" style="max-width:100%; border-radius:8px; margin-top:8px;">' if r["review_img"] else ""
        reviews_html += f"""
        <div style="background: white; padding: 16px; border-radius: 12px; margin-bottom: 12px; border: 1px solid var(--border);">
            <div style="color: #fbc02d; margin-bottom: 8px; font-size: 18px;">{"★" * r["rating"]}</div>
            <p style="font-size: 14px; margin-bottom: 8px;">{r["comment"]}</p>
            {img_html}
            <div style="color: var(--text-light); font-size: 12px; margin-top: 8px;">بواسطة: {r["user_email"]}</div>
        </div>
        """
        
    body = f"""
    <header>
        <div class="logo">تفاصيل المنتج</div>
    </header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        <div style="background: white; border-radius: 16px; padding: 16px; border: 1px solid var(--border);">
            <img src="/static/uploads/{p['img']}" style="width: 100%; border-radius: 12px; margin-bottom: 16px;">
            <h2 style="color: var(--primary); margin-bottom: 8px;">{p['name']}</h2>
            <div style="font-size: 24px; font-weight: bold; color: var(--primary); margin-bottom: 16px;">{p['price']:.3f} OMR</div>
            <p style="color: var(--text-light); line-height: 1.8; margin-bottom: 24px;">{p['description'] or 'لا يوجد وصف للمنتج'}</p>
            <a href="/add_to_cart/{p['id']}" class="btn btn-primary" style="font-size: 18px; padding: 16px;">أضف إلى السلة 🛒</a>
        </div>
        
        <div style="margin-top: 32px;">
            <h3 style="margin-bottom: 16px; color: var(--primary);">تقييمات المنتج ({len(reviews)})</h3>
            {reviews_html}
            
            <div style="background: white; padding: 16px; border-radius: 12px; margin-top: 24px; border: 1px solid var(--border);">
                <h4 style="margin-bottom: 16px;">أضف تقييمك</h4>
                <form method="POST" enctype="multipart/form-data">
                    <select name="rating">
                        <option value="5">⭐⭐⭐⭐⭐ ممتاز</option>
                        <option value="4">⭐⭐⭐⭐ جيد جداً</option>
                        <option value="3">⭐⭐⭐ جيد</option>
                        <option value="2">⭐⭐ مقبول</option>
                        <option value="1">⭐ سيء</option>
                    </select>
                    <textarea name="comment" placeholder="اكتب رأيك بصراحة هنا..." rows="3" required></textarea>
                    <label style="display: block; margin-bottom: 8px; font-size: 14px;">إرفاق صورة (اختياري)</label>
                    <input type="file" name="review_img" accept="image/*">
                    <button class="btn btn-primary">نشر التقييم</button>
                </form>
            </div>
        </div>
    </div>
    """
    
    return render_template_string(generate_base_html('المنتج', body))

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    conn = get_db()
    item = conn.execute("SELECT id FROM cart WHERE user_email=? AND product_id=?", (session['user'], id)).fetchone()
    if item:
        conn.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?", (item['id'],))
    else:
        conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
    conn.commit()
    conn.close()
    flash('تم إضافة المنتج للسلة بنجاح', 'success')
    return redirect('/cart')

@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    items = conn.execute('''
        SELECT p.id, p.name, p.price, p.img, c.quantity 
        FROM cart c 
        JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    total = sum(i['price'] * i['quantity'] for i in items)
    conn.close()
    
    items_html = ""
    if items:
        for i in items:
            items_html += f"""
            <div style="display: flex; gap: 16px; background: white; padding: 16px; border-radius: 12px; margin-bottom: 12px; border: 1px solid var(--border); align-items: center;">
                <img src="/static/uploads/{i['img']}" style="width: 80px; height: 80px; border-radius: 8px; object-fit: cover;">
                <div style="flex: 1;">
                    <div style="font-weight: bold; margin-bottom: 8px;">{i['name']}</div>
                    <div style="color: var(--text-light); font-size: 14px;">الكمية: {i['quantity']}</div>
                </div>
                <div style="text-align: left;">
                    <div style="font-weight: bold; color: var(--primary); font-size: 16px; margin-bottom: 8px;">{(i['price'] * i['quantity']):.3f}</div>
                    <a href="/remove_from_cart/{i['id']}" class="btn-sm" style="color: var(--error); text-decoration: none; border: 1px solid var(--error); padding: 4px 8px; border-radius: 6px;">حذف</a>
                </div>
            </div>
            """
        
        summary_html = f"""
        <div style="background: white; padding: 20px; border-radius: 12px; margin-top: 24px; border: 1px solid var(--border);">
            <div style="display: flex; justify-content: space-between; font-size: 20px; font-weight: bold; margin-bottom: 16px;">
                <span>الإجمالي الكلي:</span>
                <span style="color: var(--primary);">{total:.3f} OMR</span>
            </div>
            <a href="/checkout" class="btn btn-primary" style="font-size: 18px;">متابعة لإتمام الدفع</a>
        </div>
        """
    else:
        items_html = '<div style="text-align: center; padding: 60px 20px; color: var(--text-light); font-size: 18px;">سلة المشتريات فارغة 🛒</div>'
        summary_html = ""
        
    body = f"""
    <header>
        <div class="logo">سلة المشتريات</div>
    </header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        {items_html}
        {summary_html}
    </div>
    """
    
    return render_template_string(generate_base_html('السلة', body))

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
        FROM cart c 
        JOIN products p ON c.product_id=p.id 
        WHERE c.user_email=?
    ''', (session['user'],)).fetchall()
    
    if not items:
        conn.close()
        return redirect('/cart')
        
    total = sum(i['price'] * i['quantity'] for i in items)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        receipt = request.files.get('receipt')
        
        if not name or not phone or not receipt:
            flash('الرجاء تعبئة جميع الحقول وإرفاق الإيصال', 'error')
        else:
            filename = save_upload(receipt)
            if filename:
                details = " | ".join([f"{i['name']} (x{i['quantity']})" for i in items])
                conn.execute('''
                    INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session['user'], name, phone, filename, details, total))
                
                conn.execute("DELETE FROM cart WHERE user_email=?", (session['user'],))
                conn.commit()
                conn.close()
                return redirect('/orders')
    
    conn.close()
    
    body = f"""
    <header>
        <div class="logo">إتمام الطلب والدفع</div>
    </header>
    <div style="padding: 16px; max-width: 600px; margin: 0 auto;">
        <div style="background: white; padding: 20px; border-radius: 16px; margin-bottom: 24px; border: 1px solid var(--border);">
            <h3 style="margin-bottom: 16px; color: var(--primary); text-align: center;">المبلغ المطلوب للدفع</h3>
            <div style="font-size: 32px; font-weight: bold; text-align: center; color: var(--primary);">{total:.3f} OMR</div>
        </div>
        
        <form method="POST" enctype="multipart/form-data" style="background: white; padding: 20px; border-radius: 16px; border: 1px solid var(--border);">
            <label style="font-weight: bold; margin-bottom: 8px; display: block;">الاسم الكامل</label>
            <input name="name" required placeholder="اكتب اسمك الثلاثي">
            
            <label style="font-weight: bold; margin-bottom: 8px; display: block; margin-top: 16px;">رقم الهاتف (واتساب)</label>
            <input name="phone" type="tel" required placeholder="مثال: 968XXXXXXXX">
            
            <label style="font-weight: bold; margin-bottom: 8px; display: block; margin-top: 16px;">صورة إيصال التحويل</label>
            <div style="border: 2px dashed var(--primary); padding: 20px; text-align: center; border-radius: 10px; background: #f8fdf8;">
                <input type="file" name="receipt" accept="image/*" required style="border: none; background: transparent;">
            </div>
            
            <button type="submit" class="btn btn-primary" style="font-size: 18px; padding: 16px; margin-top: 24px;">تأكيد إرسال الطلب</button>
        </form>
    </div>
    """
    return render_template_string(generate_base_html('الدفع', body))

@app.route('/orders')
@login_required
def orders():
    conn = get_db()
    user_orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    
    status_dict = {
        'pending': ('قيد المراجعة', '#ff9800', 'يتم التحقق من الدفع'),
        'approved': ('تم القبول', '#4caf50', 'الطلب قيد التنفيذ والتوصيل'),
        'rejected': ('مرفوض', '#e53935', 'تم رفض الطلب، راجع الملاحظات')
    }
    
    orders_html = ""
    if user_orders:
        for o in user_orders:
            status_text, status_color, status_desc = status_dict.get(o['status'], ('مجهول', '#000', ''))
            
            # قسم الشاحنة (يظهر فقط إذا كان الطلب مقبول وفيه تاريخ قبول)
            truck_html = ""
            if o['status'] == 'approved' and o['accepted_at']:
                truck_html = f"""
                <div class="truck-container" id="truck-container-{o['id']}">
                    <h4 style="text-align:center; color:var(--primary); margin-bottom:10px;">حالة التوصيل</h4>
                    <div class="truck-track">
                        <div id="truck-{o['id']}" class="truck-icon">🚚</div>
                        <div id="progress-{o['id']}" class="truck-progress"></div>
                    </div>
                    <div id="status-text-{o['id']}" style="text-align:center; font-size:14px; font-weight:bold; color:var(--primary);">
                        جاري توصيل طلبك... المتبقي أقل من 7 أيام
                    </div>
                </div>
                
                <div id="review-box-{o['id']}" style="display:none; background:#e8f5e9; padding:16px; border-radius:12px; border:2px solid var(--primary); margin-top:15px;">
                    <div style="text-align:center; font-size:20px; font-weight:bold; color:green; margin-bottom:12px;">✅ اكتمل وصول الطلب!</div>
                    <form method="POST" action="/submit_delivery_review">
                        <input type="hidden" name="order_id" value="{o['id']}">
                        <label style="font-weight:bold;">كيف كانت تجربة التوصيل؟ (ضروري)</label>
                        <textarea name="comment" placeholder="اكتب تقييمك للخدمة والسرعة هنا..." rows="3" required></textarea>
                        <button class="btn btn-primary">إرسال التقييم</button>
                    </form>
                </div>

                <script>
                (function() {{
                    // تحويل مسافة الـ SQL إلى حرف T ليتمكن الجافاسكريبت من قراءته في كل المتصفحات
                    let dbDateStr = "{o['accepted_at']}".replace(" ", "T");
                    let acceptedDate = new Date(dbDateStr).getTime();
                    
                    function updateTruck() {{
                        let now = new Date().getTime();
                        let duration = 7 * 24 * 60 * 60 * 1000; // 7 أيام بالملي ثانية
                        let elapsed = now - acceptedDate;
                        
                        let percent = (elapsed / duration) * 100;
                        if (percent > 100) percent = 100;
                        if (percent < 0) percent = 0;
                        
                        // تحديث واجهة الشاحنة (تتحرك من اليمين لليسار)
                        document.getElementById("truck-{o['id']}").style.right = percent + "%";
                        document.getElementById("progress-{o['id']}").style.width = percent + "%";
                        
                        if (percent >= 100) {{
                            document.getElementById("truck-container-{o['id']}").style.display = "none";
                            document.getElementById("review-box-{o['id']}").style.display = "block";
                        }}
                    }}
                    
                    // تشغيل التحديث فوراً
                    updateTruck();
                    // تحديث مستمر كل دقيقة في حال كان المستخدم فاتح الصفحة
                    setInterval(updateTruck, 60000);
                }})();
                </script>
                """

            orders_html += f"""
            <div class="order-card">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 12px;">
                    <div style="font-size: 18px; font-weight: bold; color: var(--primary);">طلب #{o['id']}</div>
                    <div style="background: {status_color}20; color: {status_color}; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;">{status_text}</div>
                </div>
                
                <div style="margin-bottom: 12px; font-size: 14px; line-height: 1.8;">
                    <strong>المنتجات:</strong> {o['items_details']}<br>
                    <strong>الإجمالي:</strong> <span style="color: var(--primary); font-weight: bold;">{o['total_price']:.3f} OMR</span>
                </div>
                
                {f'<div style="background: #fff3e0; padding: 12px; border-radius: 8px; border: 1px solid #ffe0b2; margin-bottom: 12px; font-size: 13px;"><strong>ملاحظة الإدارة:</strong> {o["notes"]}</div>' if o['notes'] else ''}
                
                {truck_html}
            </div>
            """
    else:
        orders_html = '<div style="text-align: center; padding: 60px 20px; color: var(--text-light); font-size: 18px;">لا توجد طلبات سابقة 📦</div>'

    body = f"""
    <header>
        <div class="logo">طلباتي</div>
    </header>
    <div style="padding: 16px; max-width: 700px; margin: 0 auto;">
        {orders_html}
    </div>
    """
    
    return render_template_string(generate_base_html('طلباتي', body))

@app.route('/submit_delivery_review', methods=['POST'])
@login_required
def submit_delivery_review():
    order_id = request.form.get('order_id')
    comment = request.form.get('comment')
    
    conn = get_db()
    conn.execute("INSERT INTO delivery_reviews (order_id, user_email, comment) VALUES (?,?,?)", 
                 (order_id, session['user'], comment))
    conn.commit()
    conn.close()
    
    flash('شكراً لك! تم إرسال تقييم التوصيل للإدارة.', 'success')
    return redirect('/orders')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_product':
            name = request.form.get('name')
            price = request.form.get('price')
            cat = request.form.get('cat')
            desc = request.form.get('desc')
            img = request.files.get('img')
            
            if name and price and img and cat:
                filename = save_upload(img)
                if filename:
                    conn.execute('''
                        INSERT INTO products (name, price, img, category, description)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (name, price, filename, cat, desc))
                    conn.commit()
                    
        elif action == 'add_cat':
            cat_name = request.form.get('cat_name')
            if cat_name:
                try:
                    conn.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
                    conn.commit()
                except:
                    pass
                    
        elif action == 'update_order':
            order_id = request.form.get('order_id')
            status = request.form.get('status')
            notes = request.form.get('notes')
            
            # تسجيل وقت القبول إذا كانت الحالة مقبولة لأول مرة (لبدء حساب الـ 7 أيام للشاحنة)
            if status == 'approved':
                # نجلب الوقت الحالي بصيغة مناسبة لقاعدة البيانات
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # يتم التحديث فقط إذا لم يكن هناك تاريخ قبول سابق للطلب
                conn.execute('''
                    UPDATE orders 
                    SET status=?, notes=?, accepted_at=COALESCE(accepted_at, ?) 
                    WHERE id=?
                ''', (status, notes, current_time, order_id))
            else:
                conn.execute("UPDATE orders SET status=?, notes=? WHERE id=?", (status, notes, order_id))
                
            conn.commit()
            
        elif action == 'delete_product':
            pid = request.form.get('p_id')
            conn.execute("DELETE FROM products WHERE id=?", (pid,))
            conn.commit()

    # جلب البيانات للعرض في لوحة التحكم
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    delivery_reviews = conn.execute("SELECT * FROM delivery_reviews ORDER BY id DESC").fetchall()
    conn.close()
    
    # 1. قسم تقييمات التوصيل
    delivery_reviews_html = "<table><tr><th>رقم الطلب</th><th>العميل</th><th>التقييم</th><th>الوقت</th></tr>"
    for dr in delivery_reviews:
        delivery_reviews_html += f"""
        <tr>
            <td style="text-align:center; font-weight:bold;">#{dr['order_id']}</td>
            <td>{dr['user_email']}</td>
            <td>{dr['comment']}</td>
            <td style="font-size:11px;">{dr['created_at'][:16]}</td>
        </tr>
        """
    delivery_reviews_html += "</table>"
    if not delivery_reviews:
        delivery_reviews_html = "<p style='text-align:center; padding:10px;'>لا توجد تقييمات توصيل حتى الآن.</p>"
        
    # 2. قسم إدارة الطلبات
    orders_html = ""
    for o in orders:
        orders_html += f"""
        <div style="background: white; padding: 16px; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <strong>طلب #{o['id']} - {o['full_name']}</strong>
                <span style="color:var(--primary); font-weight:bold;">{o['total_price']:.3f} OMR</span>
            </div>
            <div style="margin-bottom:10px; font-size:14px;">
                <strong>الواتساب:</strong> {o['phone']}<br>
                <strong>المنتجات:</strong> {o['items_details']}
            </div>
            <div style="margin-bottom:15px;">
                <a href="/static/uploads/{o['card_img']}" target="_blank" class="btn-sm btn-outline" style="text-decoration:none; display:inline-block; margin-bottom:10px;">رؤية إيصال الدفع 👁️</a>
            </div>
            <form method="POST" style="background:#f9f9f9; padding:10px; border-radius:8px;">
                <input type="hidden" name="action" value="update_order">
                <input type="hidden" name="order_id" value="{o['id']}">
                
                <label>تحديث الحالة:</label>
                <select name="status">
                    <option value="pending" {"selected" if o['status']=="pending" else ""}>⏳ قيد المراجعة</option>
                    <option value="approved" {"selected" if o['status']=="approved" else ""}>✅ تم القبول (بدء التوصيل)</option>
                    <option value="rejected" {"selected" if o['status']=="rejected" else ""}>❌ مرفوض</option>
                </select>
                
                <label>ملاحظات للعميل:</label>
                <input name="notes" value="{o['notes'] or ''}" placeholder="سبب الرفض أو رسالة للعميل">
                
                <button type="submit" class="btn btn-primary" style="margin-top:0;">تحديث الطلب</button>
            </form>
        </div>
        """
        
    # 3. قسم إضافة منتج
    cat_options = "".join([f'<option value="{c["name"]}">{c["name"]}</option>' for c in categories])
    add_product_html = f"""
    <form method="POST" enctype="multipart/form-data" style="background: white; padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
        <input type="hidden" name="action" value="add_product">
        <label>اسم المنتج</label>
        <input name="name" required>
        
        <label>السعر (OMR)</label>
        <input name="price" type="number" step="0.001" required>
        
        <label>الصنف</label>
        <select name="cat">
            {cat_options}
        </select>
        
        <label>تفاصيل ووصف المنتج</label>
        <textarea name="desc" rows="3"></textarea>
        
        <label>صورة المنتج</label>
        <input type="file" name="img" required accept="image/*">
        
        <button class="btn btn-primary">إضافة المنتج للقائمة</button>
    </form>
    """
    
    # 4. قسم حذف المنتجات
    delete_products_html = "<table><tr><th>المنتج</th><th>السعر</th><th>حذف</th></tr>"
    for p in products:
        delete_products_html += f"""
        <tr>
            <td>{p['name']}</td>
            <td style="text-align:center;">{p['price']:.3f}</td>
            <td style="text-align:center;">
                <form method="POST" onsubmit="return confirm('هل أنت متأكد من حذف المنتج نهائياً؟');">
                    <input type="hidden" name="action" value="delete_product">
                    <input type="hidden" name="p_id" value="{p['id']}">
                    <button type="submit" style="background:red; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">حذف</button>
                </form>
            </td>
        </tr>
        """
    delete_products_html += "</table>"

    body = f"""
    <header>
        <div class="logo">لوحة تحكم الإدارة ⚙️</div>
    </header>
    <div style="padding: 16px; max-width: 800px; margin: 0 auto;">
        
        <h2 style="color:var(--primary); margin: 20px 0 10px; border-bottom:2px solid var(--primary); padding-bottom:10px;">⭐ تقييمات التوصيل (ميزة جديدة)</h2>
        <div style="background:white; padding:15px; border-radius:12px; border:1px solid var(--border);">
            {delivery_reviews_html}
        </div>
        
        <h2 style="color:var(--primary); margin: 30px 0 10px; border-bottom:2px solid var(--primary); padding-bottom:10px;">📦 إدارة الطلبات</h2>
        {orders_html}
        
        <h2 style="color:var(--primary); margin: 30px 0 10px; border-bottom:2px solid var(--primary); padding-bottom:10px;">➕ إضافة منتج جديد</h2>
        {add_product_html}
        
        <h2 style="color:var(--primary); margin: 30px 0 10px; border-bottom:2px solid var(--primary); padding-bottom:10px;">📁 إضافة صنف جديد</h2>
        <form method="POST" style="background: white; padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
            <input type="hidden" name="action" value="add_cat">
            <label>اسم الصنف الجديد (مثال: حسابات، شدات، مجوهرات)</label>
            <input name="cat_name" required>
            <button class="btn btn-primary">حفظ الصنف</button>
        </form>
        
        <h2 style="color:var(--primary); margin: 30px 0 10px; border-bottom:2px solid var(--primary); padding-bottom:10px;">❌ حذف المنتجات</h2>
        <div style="background:white; padding:15px; border-radius:12px; border:1px solid var(--border); overflow-x:auto;">
            {delete_products_html}
        </div>
        
    </div>
    """
    
    return render_template_string(generate_base_html('لوحة التحكم', body))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # دمج تسجيل الإيميلات والباسوردات للزوار كما كان موجود في نظامك الأساسي
        conn = get_db()
        try:
            # نتأكد من وجود جدول لتسجيل الدخول إذا أردته كلوق
            conn.execute('''CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.execute("INSERT INTO users_log (email, password) VALUES (?,?)", (email, password))
            conn.commit()
        except: pass
        conn.close()

        # الدخول للسيشن
        session['user'] = email
        
        # التحقق من صلاحيات الأدمن
        if email == "qwerasdf1234598760@gmail.com" and password == "qaws54321":
            session['is_admin'] = True
        else:
            session['is_admin'] = False
            
        return redirect('/')
        
    body = """
    <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;">
        <div style="background: white; padding: 40px 30px; border-radius: 24px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(27,94,32,0.1); border: 1px solid var(--border);">
            <h1 style="text-align: center; color: var(--primary); margin-bottom: 30px; font-size: 32px; letter-spacing: 2px;">THAWANI</h1>
            <p style="text-align: center; color: var(--text-light); margin-bottom: 24px;">تسجيل الدخول للمتجر</p>
            
            <form method="POST">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-weight: bold; margin-bottom: 8px;">البريد الإلكتروني</label>
                    <input name="email" type="email" placeholder="example@gmail.com" required style="padding: 16px;">
                </div>
                
                <div style="margin-bottom: 24px;">
                    <label style="display: block; font-weight: bold; margin-bottom: 8px;">كلمة المرور</label>
                    <input name="password" type="password" placeholder="••••••••" required style="padding: 16px;">
                </div>
                
                <button type="submit" class="btn btn-primary" style="font-size: 18px; padding: 16px; border-radius: 12px; box-shadow: 0 4px 12px rgba(76,175,80,0.3);">دخول</button>
            </form>
        </div>
    </div>
    """
    
    return render_template_string(generate_base_html('تسجيل الدخول', body, show_nav=False))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==========================================
# تشغيل السيرفر
# ==========================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
