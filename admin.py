import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_all_payments, get_payment_by_record_id, update_payment_status, mark_delivered
from delivery import deliver_premium, deliver_stars, deliver_nft
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
        await query.edit_message_text(text, parse_mode="Markdown")
    elif data == "admin_manual":
        context.user_data["admin_action"] = "manual_delivery"
        await query.edit_message_text(
            "Введите ID платежа (число), который нужно выдать вручную.\n"
            "Или /cancel для отмены."
        )
    elif data == "admin_stats":
        all_p = get_all_payments(limit=1000)
        total = len(all_p)
        success = sum(1 for p in all_p if p[5] == "success")
        pending = total - success
        text = f"📊 *Статистика*\nВсего платежей: {total}\nУспешных: {success}\nОжидают: {pending}"
        await query.edit_message_text(text, parse_mode="Markdown")
    else:
        await query.edit_message_text("Неизвестная команда.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if context.user_data.get("admin_action") != "manual_delivery":
        return

    try:
        record_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Некорректный ID. Введите число.")
        return

    payment = get_payment_by_record_id(record_id)
    if not payment:
        await update.message.reply_text("Платёж не найден.")
        return

    if payment["status"] == "success":
        await update.message.reply_text("Этот платёж уже успешно обработан.")
    else:
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
            await update.message.reply_text(f"✅ Товар выдан. Сообщение: {msg}")
            try:
                await context.bot.send_message(payment["user_id"], f"Администратор выдал вам товар: {msg}")
            except:
                pass
        else:
            await update.message.reply_text(f"❌ Ошибка выдачи: {msg}")
    context.user_data["admin_action"] = None
