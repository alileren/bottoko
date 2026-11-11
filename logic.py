import sqlite3
from config import DATABASE

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # membuat tabel users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            address TEXT
        )
    ''')

    # membuat tabel produk
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            size TEXT,
            price REAL NOT NULL,
            discount REAL DEFAULT 0.0,
            image_url TEXT
        )
    ''')

    # tabel keranjang
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    # tabel transaksi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'PAID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    # data awal jika tabel produk masih kosong
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ('COOLMAX Relaxed Fit T-shirt', 'Pakaian', 'M', 299900, 15.0, 'https://id.hm.com/cdn/shop/files/ff410d9af237a4d9d096d510bd13fcb31790c371_xxl-1_2f9de307-5b9e-4222-88fd-471ca845e87d.jpg'),
            ('Relaxed Fit Zip-through hoodie', 'Pakaian', 'S', 499900, 0.0, 'https://id.hm.com/cdn/shop/files/5477d21c5fdf33bfdf22122bad50bab6a38bec52_xxl-1_8b9a8d21-8a5b-4c58-9982-372548276c71.jpg'),
            ('Onitsuka Tiger MEXICO 66', 'Sepatu', '43', 2600000, 0.0, 'https://images.asics.com/is/image/asics/1183C102_100_SR_RT_GLB?qlt=100&wid=1024&hei=768&bgc=255,255,255&resMode=bisharp'),
            ('Jordan Future', 'Sepatu', 'EU 40', 1299000, 0.0, 'https://static.nike.com/a/images/t_web_pdp_936_v2/f_auto,u_126ab356-44d8-4a06-89b4-fcdcc8df0245,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/1f694a2b-05b6-4698-98d3-f1c7ba0ccc41/JORDAN+FUTURE+MULE.png')
        ]
        cursor.executemany('''
            INSERT INTO products (name, category, size, price, discount, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)

    conn.commit()
    conn.close()

# fungsi produk

def get_all_products():
    conn = get_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return products

def get_all_categories():
    conn = get_connection()
    categories = conn.execute('SELECT DISTINCT category FROM products').fetchall()
    conn.close()
    return [c['category'] for c in categories]

def get_products_by_category(category):
    conn = get_connection()
    products = conn.execute('SELECT * FROM products WHERE LOWER(category) = LOWER(?)', (category,)).fetchall()
    conn.close()
    return products

def get_product_by_name(name):
    conn = get_connection()
    product = conn.execute('SELECT * FROM products WHERE LOWER(name) = LOWER(?)', (name,)).fetchall()
    conn.close()
    return product

# fungsi user dan alamat

def get_user_address(user_id):
    conn = get_connection()
    user = conn.execute('SELECT address FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user['address'] if user else None

def set_user_address(user_id, address):
    conn = get_connection()
    conn.execute('''
        INSERT INTO users (user_id, address) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET address = excluded.address
    ''', (user_id, address))
    conn.commit()
    conn.close()

# fungsi keranjang dan checkout

def add_to_cart(user_id, product_id):
    conn = get_connection()
    item = conn.execute('SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?', (user_id, product_id)).fetchone()
    if item:
        conn.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = ?', (item['id'],))
    else:
        conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)', (user_id, product_id))
    conn.commit()
    conn.close()

def get_user_cart(user_id):
    conn = get_connection()
    query = '''
        SELECT c.id as cart_id, p.name, p.price, p.discount, c.quantity
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    '''
    items = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return items

def clear_user_cart(user_id):
    conn = get_connection()
    conn.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def create_transaction(user_id, total_price):
    conn = get_connection()
    conn.execute('INSERT INTO transactions (user_id, total_price) VALUES (?, ?)', (user_id, total_price))
    conn.commit()
    conn.close()