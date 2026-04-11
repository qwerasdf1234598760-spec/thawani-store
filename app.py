import os
import uuid
import logging
import datetime
import traceback
import psycopg2 # المكتبة المطلوبة للربط مع Neon
from psycopg2.extras import DictCursor
from functools import wraps
from flask import Flask, request, render_template_string, redirect, session, url_for, flash, abort
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

# ==========================================
# 1. إعدادات السيرفر والربط بـ Neon
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "Thawani_Store_Secure_2026_Fixed"

# رابط قاعدة البيانات الذي أرسلته
DATABASE_URL = "postgresql://neondb_owner:npg_LfrcOy0oTV6F@ep-bold-voice-an2t0k43.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# 2. وظائف قاعدة البيانات (PostgreSQL)
# ==========================================
def get_db_connection():
    """الاتصال بقاعدة بيانات Neon الخارجية"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    return conn

def init_db():
    """إنشاء الجداول في Neon لأول مرة"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # إنشاء الجداول بنظام PostgreSQL (يختلف قليلاً عن SQLite)
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, 
            email TEXT UNIQUE NOT NULL, 
            password_hash TEXT NOT NULL, 
            is_admin INTEGER DEFAULT 0)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY, 
            name TEXT NOT NULL, 
            price DECIMAL NOT NULL, 
            img TEXT NOT NULL, 
            category TEXT NOT NULL, 
            description TEXT, 
            is_active INTEGER DEFAULT 1)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS cart (
            id SERIAL PRIMARY KEY, 
            user_email TEXT NOT NULL, 
            product_id INTEGER NOT NULL, 
            quantity INTEGER DEFAULT 1, 
            UNIQUE(user_email, product_id))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY, 
            name TEXT UNIQUE NOT NULL)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY, 
            user_email TEXT NOT NULL, 
            full_name TEXT NOT NULL, 
            phone TEXT NOT NULL, 
            card_img TEXT NOT NULL, 
            items_details TEXT NOT NULL, 
            total_price DECIMAL NOT NULL, 
            status TEXT DEFAULT 'pending', 
            notes TEXT, 
            accepted_at TIMESTAMP, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY, 
            product_id INTEGER NOT NULL, 
            user_email TEXT NOT NULL, 
            rating INTEGER, 
            comment TEXT, 
            review_img TEXT)''')

        # إنشاء حساب المدير التلقائي
        cur.execute("SELECT id FROM users WHERE email='qwerasdf1234598760@gmail.com'")
        if not cur.fetchone():
            hashed = generate_password_hash("qaws54321")
            cur.execute("INSERT INTO users (email, password_hash, is_admin) VALUES (%s, %s, 1)", 
                       ('qwerasdf1234598760@gmail.com', hashed))
        
        # إضافة صنف افتراضي
        cur.execute("SELECT id FROM categories LIMIT 1")
        if not cur.fetchone():
            cur.execute("INSERT INTO categories (name) VALUES ('الكل')")

        conn.commit()
        logger.info("تم تحديث جداول Neon بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
    finally:
        cur.close()
        conn.close()

init_db()

# ==========================================
# 3. تعديل معالجة الصور لتعمل مع الروابط (CSS الأساسي)
# ==========================================
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    body { font-family: 'Tajawal', sans-serif; direction: rtl; background: #f4f7f6; margin: 0; padding-bottom: 70px; }
    header { background: #1a237e; color: white; padding: 20px; text-align: center; font-weight: bold; font-size: 22px; }
    .container { padding: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .card img { width: 100%; height: 120px; object-fit: cover; }
    .btn { background: #1a237e; color: white; border: none; padding: 10px; width: 100%; border-radius: 8px; cursor: pointer; text-decoration: none; display: block; text-align: center; }
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: white; display: flex; justify-content: space-around; padding: 10px 0; border-top: 2px solid #eee; }
    input, textarea, select { width: 100%; padding: 12px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #ddd; }
</style>
"""

# (بقية الدوال والمسارات Flask تبقى مشابهة لما سبق مع تغيير استعلامات SQL لتناسب %s بدلاً من ?)

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE is_active=1")
    products = cur.fetchall()
    cur.close()
    conn.close()
    
    prod_html = ""
    for p in products:
        prod_html += f'<div class="card"><img src="/static/uploads/{p["img"]}"><div style="padding:10px;"><b>{p["name"]}</b><p style="color:green;">{p["price"]} OMR</p><a href="/add_to_cart/{p["id"]}" class="btn">شراء</a></div></div>'
    
    body = f'<header>THAWANI STORE</header><div class="container">{prod_html}</div>'
    return render_template_string(f"<html><head>{CSS}</head><body>{body}</body></html>")

# ... (بقية المسارات: login, cart, checkout, admin يتم تعديلها لاستخدام cur.execute بجمل %s)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form.get('email')
        session['is_admin'] = (request.form.get('email') == "qwerasdf1234598760@gmail.com")
        return redirect('/')
    return render_template_string(f"<html><head>{CSS}</head><body><div style='padding:50px;'><header>دخول المتجر</header><form method='POST'><input name='email' type='email' placeholder='الايميل'><input name='password' type='password' placeholder='كلمة السر'><button class='btn'>دخول</button></form></div></body></html>")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
