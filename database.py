import aiosqlite
import datetime

DB_PATH = "bot_database.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_type TEXT,
                product_key TEXT,
                amount_rub INTEGER,
                status TEXT DEFAULT 'pending',
                payment_label TEXT,
                created_at TEXT,
                paid_at TEXT
            )
        """)
        await db.commit()


async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, datetime.datetime.now().isoformat()))
        await db.commit()


async def create_order(user_id: int, product_type: str, product_key: str,
                       amount_rub: int, payment_label: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO orders (user_id, product_type, product_key, amount_rub,
                                status, payment_label, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (user_id, product_type, product_key, amount_rub,
              payment_label, datetime.datetime.now().isoformat()))
        await db.commit()
        return cursor.lastrowid


async def complete_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = 'paid', paid_at = ?
            WHERE order_id = ?
        """, (datetime.datetime.now().isoformat(), order_id))
        await db.commit()


async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM orders WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 10
        """, (user_id,))
        return await cursor.fetchall()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        users_count = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'paid'"
        )
        paid_orders = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_rub), 0) FROM orders WHERE status = 'paid'"
        )
        total_revenue = (await cursor.fetchone())[0]

        return users_count, paid_orders, total_revenue
