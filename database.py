import sqlite3
import datetime

DB_NAME = "payments.db"

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_payment(user_id, product, payment_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (user_id, product, payment_id, amount) VALUES (?, ?, ?, ?)",
        (user_id, product, payment_id, amount)
    )
    conn.commit()
    conn.close()

def update_payment_status(payment_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status = ? WHERE payment_id = ?",
        (status, payment_id)
    )
    conn.commit()
    conn.close()

def get_payment(payment_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, product, amount, status FROM payments WHERE payment_id = ?",
        (payment_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "product": row[1], "amount": row[2], "status": row[3]}
    return None

def get_pending_payment(user_id, product):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT payment_id FROM payments WHERE user_id = ? AND product = ? AND status = 'pending'",
        (user_id, product)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
