from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_all_payments, get_payment, update_payment_status, mark_delivered
from config import ADMIN_ID

def is_admin(user_id):
    return user_id == ADMIN_ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    keyboard = [
        [InlineKeyboardButton("📋 Список платежей", callback_data="admin_payments")],
        [InlineKeyboardButton("🔄 Ручная выдача", callback_data="admin_manual")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
    ]
    await update.message.reply_text("👑 *Админ-панель*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return

    data = query.data
    if data == "admin_payments":
        payments = get_all_payments(limit=20)
        if not payments:
            await query.edit_message_text("Платежей пока нет.")
            return
        text = "📋 *Последние платежи:*\n"
        for p in payments:
            # p: id, user_id, product, payment_id, amount, status, created_at, delivered
            text += f"ID: {p[0]} | Пользователь: {p[1]} | {p[2]} | {p[4]} руб. | {p[5]} | {p[6]}\n"
        # Если много, можно разбить на страницы, но для простоты так
        await query.edit_message_text(text, parse_mode="Markdown")
    elif data == "admin_manual":
        # Предложим ввести ID платежа для ручной выдачи
        context.user_data["admin_action"] = "manual_delivery"
        await query.edit_message_text(
            "Введите ID платежа (число), который нужно выдать вручную.\n"
            "Или /cancel для отмены."
        )
        # Переключаем состояние (можно через ConversationHandler, но для простоты используем callback)
        # Пользователь введёт число, и мы обработаем в отдельном обработчике сообщений
    elif data == "admin_stats":
        # Простая статистика
        from database import get_all_payments
        all_p = get_all_payments(limit=1000)
        total = len(all_p)
        success = sum(1 for p in all_p if p[5] == "success")
        pending = total - success
        text = f"📊 *Статистика*\nВсего платежей: {total}\nУспешных: {success}\nОжидают: {pending}"
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await query.edit_message_text("Неизвестная команда.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод ID платежа для ручной выдачи"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if context.user_data.get("admin_action") != "manual_delivery":
        return

    try:
        payment_id_int = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Некорректный ID. Введите число.")
        return

    # Получаем платеж по ID (не payment_id, а id в таблице)
    conn = sqlite3.connect("bot.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, product, payment_id, status FROM payments WHERE id = ?", (payment_id_int,))
    row = cur.fetchone()
    conn.close()
    if not row:
        await update.message.reply_text("Платёж не найден.")
        return
    user_id_db, product_key, payment_id, status = row
    if status == "success":
        await update.message.reply_text("Этот платёж уже успешно обработан.")
    else:
        # Выдаём товар
        from delivery import deliver_premium, deliver_stars, deliver_nft
        # Вызываем соответствующую функцию
        if product_key == "premium":
            success, msg = await deliver_premium(user_id_db)
        elif product_key == "stars":
            # нужно узнать сумму из базы
            cur = conn.cursor()
            cur.execute("SELECT amount FROM payments WHERE id = ?", (payment_id_int,))
            amount = cur.fetchone()[0]
            success, msg = await deliver_stars(user_id_db, amount)
        elif product_key == "nft":
            success, msg = await deliver_nft(user_id_db)
        else:
            success, msg = False, "Неизвестный товар"
        if success:
            update_payment_status(payment_id, "success")
            mark_delivered(payment_id)
            await update.message.reply_text(f"✅ Товар выдан. Сообщение: {msg}")
            # Уведомить пользователя
            try:
                await context.bot.send_message(user_id_db, f"Администратор выдал вам товар: {msg}")
            except:
                pass
        else:
            await update.message.reply_text(f"❌ Ошибка выдачи: {msg}")
    context.user_data["admin_action"] = None
