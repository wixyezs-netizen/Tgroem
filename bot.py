#!/usr/bin/env python3
"""
Telegram бот для продажи Telegram Premium, звёзд и NFT с оплатой через ЮMoney
"""

import asyncio
import sqlite3
import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ConversationHandler, ContextTypes
)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8633048902:AAEBTjJtA-SBUSZI8WrKhcFajMA49XpOEVk"
ADMIN_ID = 8681521200

YOOMONEY_WALLET = "4100118889570559"
YOOMONEY_ACCESS_TOKEN = "4100118889570559.3288B2E716CEEB922A26BD6BEAC58648FBFB680CCF64E4E1447D714D6FB5EA5F01F1478FAC686BEF394C8A186C98982DE563C1ABCDF9F2F61D971B61DA3C7E486CA818F98B9E0069F1C0891E090DD56A11319D626A40F0AE8302A8339DED9EB7969617F191D93275F64C4127A3ECB7AED33FCDE91CA68690EB7534C67E6C219E"

# Товары
PRODUCTS = {
    "premium": {
        "name": "Telegram Premium (1 месяц)",
        "price": 100,
        "description": "Активация премиум подписки на месяц."
    },
    "stars": {
        "name": "⭐ 100 Звёзд",
        "price": 50,
        "description": "100 Telegram Stars на ваш аккаунт."
    },
    "nft": {
        "name": "🎨 Эксклюзивное NFT",
        "price": 200,
        "description": "Уникальный NFT-токен от нашего проекта."
    }
}

CHECK_INTERVAL = 30
DB_NAME = "bot.db"

# Состояния для ConversationHandler
SELECTING_PRODUCT, CONFIRMING, WAITING_PAYMENT = range(3)

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== РАБОТА С БАЗОЙ ДАННЫХ ====================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Таблица платежей
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
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_or_create_user(user_id: int, username: str = None, first_name: str = None):
    """Получить или создать пользователя"""
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
    conn.close()

def add_payment(user_id: int, product_key: str, payment_id: str, amount: int):
    """Добавить платёж"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (user_id, product, payment_id, amount) VALUES (?, ?, ?, ?)",
        (user_id, product_key, payment_id, amount)
    )
    conn.commit()
    conn.close()

def update_payment_status(payment_id: str, status: str, delivered: bool = False):
    """Обновить статус платежа"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status = ?, delivered = ? WHERE payment_id = ?",
        (status, delivered, payment_id)
    )
    conn.commit()
    conn.close()

def get_payment(payment_id: str) -> Optional[Dict]:
    """Получить информацию о платеже"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, product, amount, status, delivered FROM payments WHERE payment_id = ?",
        (payment_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "product": row[1],
            "amount": row[2],
            "status": row[3],
            "delivered": row[4]
        }
    return None

def get_pending_payment(user_id: int, product_key: str) -> Optional[str]:
    """Проверить, есть ли ожидающий платёж"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT payment_id FROM payments WHERE user_id = ? AND product = ? AND status = 'pending'",
        (user_id, product_key)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def get_pending_payments() -> list:
    """Получить все ожидающие платежи"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT payment_id, user_id, product, amount FROM payments WHERE status = 'pending' AND delivered = 0"
    )
    rows = cur.fetchall()
    conn.close()
    return [{"payment_id": r[0], "user_id": r[1], "product": r[2], "amount": r[3]} for r in rows]

def mark_delivered(payment_id: str):
    """Отметить товар как выданный"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE payments SET delivered = 1 WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()

def get_user_payments(user_id: int) -> list:
    """Получить историю платежей пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, product, amount, status, created_at FROM payments WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_payments(limit: int = 100) -> list:
    """Получить все платежи для админа"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, product, payment_id, amount, status, created_at, delivered FROM payments ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_payment_by_id(payment_id: int) -> Optional[Dict]:
    """Получить платеж по ID записи"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, product, payment_id, amount, status FROM payments WHERE id = ?",
        (payment_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "product": row[1],
            "payment_id": row[2],
            "amount": row[3],
            "status": row[4]
        }
    return None

# ==================== ИНТЕГРАЦИЯ С ЮMONEY ====================
async def create_yoomoney_payment(amount: int, product_name: str, user_id: int):
    """Создать платёж в ЮMoney"""
    import aiohttp
    
    payment_id = str(uuid.uuid4())
    label = f"payment_{user_id}_{payment_id}"
    
    url = "https://yoomoney.ru/api/request-payment"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "pattern_id": "p2p",
        "to": YOOMONEY_WALLET,
        "amount": str(amount),
        "comment": f"Покупка: {product_name}",
        "label": label,
        "test_payment": "true"  # Для тестов. Удалить для реальных платежей
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as resp:
                result = await resp.json()
                logger.info(f"Создание платежа: {result}")
                if result.get("status") == "success":
                    return payment_id, result.get("confirmation_url")
                else:
                    error = result.get("error", "Неизвестная ошибка")
                    return None, f"Ошибка: {error}"
        except Exception as e:
            logger.exception("Ошибка при создании платежа")
            return None, f"Ошибка сети: {e}"

async def check_yoomoney_payment(payment_id: str) -> bool:
    """Проверить статус платежа"""
    import aiohttp
    
    url = "https://yoomoney.ru/api/check-payment"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"payment_id": payment_id}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as resp:
                result = await resp.json()
                logger.info(f"Проверка платежа: {result}")
                return result.get("status") == "success"
        except Exception as e:
            logger.exception("Ошибка при проверке платежа")
            return False

# ==================== ВЫДАЧА ТОВАРОВ ====================
async def deliver_premium(user_id: int) -> tuple:
    """Выдача Telegram Premium"""
    logger.info(f"Выдача Premium пользователю {user_id}")
    # Здесь добавьте реальную логику выдачи Premium
    return True, "Telegram Premium активирован на 1 месяц! 🎉"

async def deliver_stars(user_id: int, amount: int) -> tuple:
    """Выдача Telegram Stars"""
    stars = amount * 2  # 1 рубль = 2 звезды
    logger.info(f"Выдача {stars} звёзд пользователю {user_id}")
    # Здесь добавьте реальную логику выдачи Stars
    return True, f"На ваш счёт зачислено {stars} звёзд! ⭐"

async def deliver_nft(user_id: int) -> tuple:
    """Выдача NFT"""
    logger.info(f"Выдача NFT пользователю {user_id}")
    # Здесь добавьте реальную логику выдачи NFT
    return True, "Ваше NFT отправлено на кошелёк! 🎨"

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
def get_products_keyboard():
    """Клавиатура с товарами"""
    keyboard = []
    for key, product in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            f"{product['name']} - {product['price']} руб.",
            callback_data=f"product_{key}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для покупки:\n"
        "• Telegram Premium\n"
        "• Telegram Stars\n"
        "• Эксклюзивных NFT\n\n"
        "Выберите товар:",
        reply_markup=get_products_keyboard()
    )
    return SELECTING_PRODUCT

async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора товара"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Действие отменено. Введите /start для выбора товара.")
        return ConversationHandler.END
    
    product_key = query.data.split("_")[1]
    product = PRODUCTS.get(product_key)
    
    if not product:
        await query.edit_message_text("❌ Товар не найден.")
        return SELECTING_PRODUCT
    
    context.user_data["product_key"] = product_key
    context.user_data["product_name"] = product["name"]
    context.user_data["price"] = product["price"]
    
    confirm_text = (
        f"🛍 *{product['name']}*\n\n"
        f"💰 Стоимость: {product['price']} руб.\n"
        f"📝 {product['description']}\n\n"
        "✅ Подтвердите покупку:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_products")]
    ]
    
    await query.edit_message_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CONFIRMING

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение покупки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_products":
        await query.edit_message_text(
            "Выберите товар:",
            reply_markup=get_products_keyboard()
        )
        return SELECTING_PRODUCT
    
    user_id = update.effective_user.id
    product_key = context.user_data["product_key"]
    product_name = context.user_data["product_name"]
    price = context.user_data["price"]
    
    # Проверяем, нет ли уже ожидающего платежа
    existing = get_pending_payment(user_id, product_key)
    if existing:
        await query.edit_message_text(
            "⚠️ У вас уже есть незавершённый платёж.\n"
            "Оплатите его или подождите. Если вы оплатили, нажмите /check."
        )
        return WAITING_PAYMENT
    
    # Создаём платёж
    payment_id, confirmation_url = await create_yoomoney_payment(price, product_name, user_id)
    
    if not confirmation_url:
        await query.edit_message_text(
            f"❌ Не удалось создать платёж: {payment_id}\n"
            "Попробуйте позже или обратитесь к администратору."
        )
        return ConversationHandler.END
    
    # Сохраняем в БД
    add_payment(user_id, product_key, payment_id, price)
    context.user_data["payment_id"] = payment_id
    
    pay_message = (
        f"💳 *Оплата*\n\n"
        f"Сумма: {price} руб.\n"
        f"Товар: {product_name}\n\n"
        f"🔗 *Ссылка для оплаты:*\n{confirmation_url}\n\n"
        "После оплаты нажмите кнопку ниже:"
    )
    
    keyboard = [[InlineKeyboardButton("✅ Проверить оплату", callback_data="check_payment")]]
    await query.edit_message_text(
        pay_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WAITING_PAYMENT

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка оплаты"""
    query = update.callback_query
    await query.answer()
    
    payment_id = context.user_data.get("payment_id")
    if not payment_id:
        await query.edit_message_text("❌ Не найден идентификатор платежа. Попробуйте заново /start")
        return ConversationHandler.END
    
    payment_info = get_payment(payment_id)
    if not payment_info:
        await query.edit_message_text("❌ Платёж не найден.")
        return ConversationHandler.END
    
    if payment_info["status"] == "success":
        await query.edit_message_text("✅ Этот платёж уже был успешно обработан.")
        return ConversationHandler.END
    
    # Проверяем через API
    success = await check_yoomoney_payment(payment_id)
    
    if success:
        update_payment_status(payment_id, "success")
        
        # Выдаём товар
        product_key = payment_info["product"]
        user_id = payment_info["user_id"]
        
        if product_key == "premium":
            ok, msg = await deliver_premium(user_id)
        elif product_key == "stars":
            ok, msg = await deliver_stars(user_id, payment_info["amount"])
        elif product_key == "nft":
            ok, msg = await deliver_nft(user_id)
        else:
            ok, msg = False, "Неизвестный товар"
        
        if ok:
            mark_delivered(payment_id)
            await query.edit_message_text(f"✅ {msg}\n\nСпасибо за покупку! 🎉")
        else:
            await query.edit_message_text(
                f"⚠️ {msg}\n"
                "Мы уведомили администратора. Товар будет выдан вручную."
            )
            # Уведомляем админа
            await context.bot.send_message(
                ADMIN_ID,
                f"❗️ Ошибка выдачи товара\n"
                f"Пользователь: {user_id}\n"
                f"Товар: {product_key}\n"
                f"Платёж: {payment_id}"
            )
        return ConversationHandler.END
    else:
        await query.edit_message_text(
            "⏳ Платёж пока не найден.\n"
            "Убедитесь, что вы оплатили, и попробуйте снова через минуту.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить снова", callback_data="check_payment")
            ]])
        )
        return WAITING_PAYMENT

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """История покупок"""
    user_id = update.effective_user.id
    payments = get_user_payments(user_id)
    
    if not payments:
        await update.message.reply_text("📭 У вас пока нет покупок.")
        return
    
    text = "📜 *Ваши покупки:*\n\n"
    for p in payments:
        status = "✅" if p[3] == "success" else "⏳"
        text += f"{status} {p[1]} - {p[2]} руб. ({p[4]})\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка"""
    text = (
        "📖 *Помощь*\n\n"
        "/start - начать покупку\n"
        "/history - история покупок\n"
        "/help - эта справка\n\n"
        "По вопросам обращайтесь к @support"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена"""
    await update.message.reply_text("❌ Действие отменено. Введите /start для выбора товара.")
    return ConversationHandler.END

# ==================== АДМИН-ПАНЕЛЬ ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📋 Список платежей", callback_data="admin_payments")],
        [InlineKeyboardButton("🔄 Ручная выдача", callback_data="admin_manual")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
    ]
    await update.message.reply_text(
        "👑 *Админ-панель*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка админ-кнопок"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Доступ запрещён.")
        return
    
    if query.data == "admin_payments":
        payments = get_all_payments(limit=20)
        if not payments:
            await query.edit_message_text("📭 Платежей пока нет.")
            return
        
        text = "📋 *Последние платежи:*\n\n"
        for p in payments:
            text += f"ID: {p[0]} | {p[2]} | {p[4]} руб. | {p[5]} | {p[6]}\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif query.data == "admin_manual":
        context.user_data["admin_action"] = "manual_delivery"
        await query.edit_message_text(
            "Введите ID платежа (число) для ручной выдачи:\n"
            "Или /cancel для отмены."
        )
    
    elif query.data == "admin_stats":
        payments = get_all_payments(limit=1000)
        total = len(payments)
        success = sum(1 for p in payments if p[5] == "success")
        pending = total - success
        
        text = (
            f"📊 *Статистика*\n\n"
            f"Всего платежей: {total}\n"
            f"Успешных: {success}\n"
            f"Ожидают: {pending}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода ID для ручной выдачи"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if context.user_data.get("admin_action") != "manual_delivery":
        return
    
    try:
        record_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Некорректный ID. Введите число.")
        return
    
    payment = get_payment_by_id(record_id)
    if not payment:
        await update.message.reply_text("❌ Платёж не найден.")
        return
    
    if payment["status"] == "success":
        await update.message.reply_text("✅ Этот платёж уже успешно обработан.")
    else:
        # Выдаём товар
        if payment["product"] == "premium":
            success, msg = await deliver_premium(payment["user_id"])
        elif payment["product"] == "stars":
            success, msg = await deliver_stars(payment["user_id"], payment["amount"])
        elif payment["product"] == "nft":
            success, msg = await deliver_nft(payment["user_id"])
        else:
            success, msg = False, "Неизвестный товар"
        
        if success:
            update_payment_status(payment["payment_id"], "success")
            mark_delivered(payment["payment_id"])
            await update.message.reply_text(f"✅ Товар выдан. {msg}")
            # Уведомляем пользователя
            try:
                await context.bot.send_message(
                    payment["user_id"],
                    f"✅ Администратор выдал вам товар: {msg}"
                )
            except:
                pass
        else:
            await update.message.reply_text(f"❌ Ошибка выдачи: {msg}")
    
    context.user_data["admin_action"] = None

# ==================== ФОНОВАЯ ПРОВЕРКА ПЛАТЕЖЕЙ ====================
async def background_checker(application: Application):
    """Фоновый процесс проверки платежей"""
    while True:
        try:
            pending = get_pending_payments()
            for p in pending:
                success = await check_yoomoney_payment(p["payment_id"])
                if success:
                    update_payment_status(p["payment_id"], "success")
                    
                    # Выдаём товар
                    if p["product"] == "premium":
                        ok, msg = await deliver_premium(p["user_id"])
                    elif p["product"] == "stars":
                        ok, msg = await deliver_stars(p["user_id"], p["amount"])
                    elif p["product"] == "nft":
                        ok, msg = await deliver_nft(p["user_id"])
                    else:
                        ok, msg = False, "Неизвестный товар"
                    
                    if ok:
                        mark_delivered(p["payment_id"])
                        await application.bot.send_message(
                            p["user_id"],
                            f"✅ Ваш платёж подтверждён! {msg}"
                        )
                    else:
                        await application.bot.send_message(
                            ADMIN_ID,
                            f"❗️ Ошибка автоматической выдачи\n"
                            f"Платёж: {p['payment_id']}\n"
                            f"Пользователь: {p['user_id']}\n"
                            f"Товар: {p['product']}\n"
                            f"Ошибка: {msg}"
                        )
                await asyncio.sleep(1)
        except Exception as e:
            logger.exception("Ошибка в фоновой проверке")
        await asyncio.sleep(CHECK_INTERVAL)

def run_background(loop: asyncio.AbstractEventLoop, app: Application):
    """Запуск фонового процесса"""
    asyncio.set_event_loop(loop)
    loop.create_task(background_checker(app))
    loop.run_forever()

# ==================== ЗАПУСК БОТА ====================
def main():
    """Главная функция"""
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для покупки
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_PRODUCT: [
                CallbackQueryHandler(product_callback, pattern="^(product_|cancel)$")
            ],
            CONFIRMING: [
                CallbackQueryHandler(confirm_callback, pattern="^(confirm|back_to_products)$")
            ],
            WAITING_PAYMENT: [
                CallbackQueryHandler(check_payment_callback, pattern="^check_payment$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    
    # Обычные команды
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Админские обработчики
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    application.add_handler(CommandHandler("start", start))
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.TEXT & filters.USER, handle_admin_message))
    
    # Запуск фоновой проверки в отдельном потоке
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=run_background, args=(loop, application), daemon=True)
    thread.start()
    
    # Запуск бота
    logger.info("🚀 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
