import sqlite3
import datetime
from config import PRODUCTS

DB_NAME = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            payment_id TEXT NOT NULL UNIQUE,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered BOOLEAN DEFAULT 0
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            type TEXT
        )
    ''')
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        for key, product in PRODUCTS.items():
            cur.execute(
                "INSERT INTO products (key, name, price, description, type) VALUES (?, ?, ?, ?, ?)",
                (key, product['name'], product['price'], product['description'], product['type'])
            )
    
    conn.commit()
    conn.close()

def get_or_create_user(user_id, username=None, first_name=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        conn.commit()
        user = (user_id, username, first_name, 0, datetime.datetime.now())
    conn.close()
    return {"user_id": user[0], "username": user[1], "first_name": user[2], "balance": user[3]}

def add_payment(user_id, product_key, payment_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (user_id, product, payment_id, amount) VALUES (?, ?, ?, ?)",
        (user_id, product_key, payment_id, amount)
    )
    conn.commit()
    conn.close()

def update_payment_status(payment_id, status, delivered=False):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status = ?, delivered = ? WHERE payment_id = ?",
        (status, delivered, payment_id)
    )
    conn.commit()
    conn.close()

def get_payment(payment_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, product, amount, status, delivered FROM payments WHERE payment_id = ?",
        (payment_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "product": row[1], "amount": row[2], "status": row[3], "delivered": row[4]}
    return None

def get_pending_payments():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT payment_id, user_id, product, amount FROM payments WHERE status = 'pending' AND delivered = 0"
    )
    rows = cur.fetchall()
    conn.close()
    return [{"payment_id": r[0], "user_id": r[1], "product": r[2], "amount": r[3]} for r in rows]

def get_pending_payment(user_id, product_key):
    """Возвращает payment_id, если есть ожидающий платёж для данного пользователя и товара"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT payment_id FROM payments WHERE user_id = ? AND product = ? AND status = 'pending'",
        (user_id, product_key)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def mark_delivered(payment_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE payments SET delivered = 1 WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()

def get_all_payments(limit=100):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, product, payment_id, amount, status, created_at, delivered FROM payments ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_user_payments(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, product, amount, status, created_at FROM payments WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_payment_by_record_id(record_id):
    """Получить платёж по числовому ID записи (для админки)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, product, payment_id, amount, status FROM payments WHERE id = ?",
        (record_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "product": row[1], "payment_id": row[2], "amount": row[3], "status": row[4]}
    return None
