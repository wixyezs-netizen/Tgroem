from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from config import PRODUCTS, ADMIN_ID
from database import (
    add_payment, update_payment_status, get_pending_payment,
    get_payment, get_or_create_user, mark_delivered
)
from yoomoney import create_payment, check_payment
from delivery import deliver_premium, deliver_stars, deliver_nft

logger = logging.getLogger(__name__)

SELECTING_PRODUCT, CONFIRMING, WAITING_PAYMENT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n"
        "Я бот для покупки Telegram Premium, звёзд и NFT.\n"
        "Выберите товар из меню ниже.",
        reply_markup=get_products_keyboard()
    )
    return SELECTING_PRODUCT

def get_products_keyboard():
    keyboard = []
    for key, product in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            f"{product['name']} - {product['price']} руб.",
            callback_data=f"product_{key}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)

async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cancel":
        await query.edit_message_text("Действие отменено. Введите /start для выбора товара.")
        return ConversationHandler.END

    product_key = data.split("_")[1]
    product = PRODUCTS.get(product_key)
    if not product:
        await query.edit_message_text("Товар не найден.")
        return SELECTING_PRODUCT

    context.user_data["product_key"] = product_key
    context.user_data["product_name"] = product["name"]
    context.user_data["price"] = product["price"]

    confirm_text = (
        f"Вы выбрали: {product['name']}\n"
        f"Стоимость: {product['price']} руб.\n\n"
        f"{product['description']}\n\n"
        "Подтвердите покупку."
    )
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_products")]
    ]
    await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMING

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    existing = get_pending_payment(user_id, product_key)
    if existing:
        await query.edit_message_text(
            "У вас уже есть незавершённый платёж. Оплатите его или подождите.\n"
            "Если вы оплатили, нажмите /check."
        )
        return WAITING_PAYMENT

    payment_id, confirmation_url = await create_payment(price, product_name, user_id)
    if not confirmation_url:
        await query.edit_message_text(
            f"Не удалось создать платёж: {payment_id}\nПопробуйте позже или обратитесь к администратору."
        )
        return ConversationHandler.END

    add_payment(user_id, product_key, payment_id, price)
    context.user_data["payment_id"] = payment_id

    pay_message = (
        f"💳 Оплатите {price} руб. на кошелёк ЮMoney.\n\n"
        f"🔗 Ссылка для оплаты:\n{confirmation_url}\n\n"
        "После оплаты нажмите кнопку ниже, чтобы подтвердить."
    )
    keyboard = [[InlineKeyboardButton("✅ Проверить оплату", callback_data="check_payment")]]
    await query.edit_message_text(pay_message, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_PAYMENT

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = context.user_data.get("payment_id")
    if not payment_id:
        await query.edit_message_text("Не найден идентификатор платежа. Попробуйте заново /start")
        return ConversationHandler.END

    payment_info = get_payment(payment_id)
    if not payment_info:
        await query.edit_message_text("Платёж не найден.")
        return ConversationHandler.END

    if payment_info["status"] == "success":
        await query.edit_message_text("Этот платёж уже был успешно обработан.")
        return ConversationHandler.END

    success = await check_payment(payment_id)
    if success:
        update_payment_status(payment_id, "success")
        await deliver_product(update, context, payment_info["product"], payment_id)
        return ConversationHandler.END
    else:
        await query.edit_message_text(
            "Платёж пока не найден. Убедитесь, что вы оплатили, и попробуйте снова через минуту.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить снова", callback_data="check_payment")
            ]])
        )
        return WAITING_PAYMENT

async def deliver_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_key: str, payment_id: str):
    user = update.effective_user
    product = PRODUCTS.get(product_key)
    if not product:
        await update.callback_query.edit_message_text("Товар не найден, но оплата прошла. Обратитесь к администратору.")
        return

    success = False
    message = ""
    try:
        if product_key == "premium":
            success, message = await deliver_premium(user.id)
        elif product_key == "stars":
            success, message = await deliver_stars(user.id, product["price"])
        elif product_key == "nft":
            success, message = await deliver_nft(user.id)
        else:
            message = "Неизвестный тип товара."
    except Exception as e:
        logger.exception("Ошибка при выдаче товара")
        message = f"Произошла ошибка при выдаче товара. Свяжитесь с администратором."

    if success:
        mark_delivered(payment_id)
        await update.callback_query.edit_message_text(f"✅ {message}\nСпасибо за покупку!")
    else:
        await update.callback_query.edit_message_text(
            f"⚠️ {message}\nМы уведомили администратора. Ваш платёж зафиксирован, товар будет выдан вручную."
        )
        if context.bot:
            await context.bot.send_message(
                ADMIN_ID,
                f"❗️ Не удалось выдать товар автоматически.\n"
                f"Пользователь: {user.id}\nТовар: {product['name']}\nПлатёж: {payment_id}"
            )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено. Введите /start для выбора товара.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Справка*\n"
        "/start - начать покупку\n"
        "/history - история покупок\n"
        "/help - эта справка\n"
        "Если вы админ, используйте /admin для управления."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_user_payments
    user_id = update.effective_user.id
    payments = get_user_payments(user_id)
    if not payments:
        await update.message.reply_text("У вас пока нет покупок.")
        return
    text = "📜 *Ваши покупки:*\n"
    for p in payments:
        status_emoji = "✅" if p[3] == "success" else "⏳"
        text += f"{status_emoji} {p[1]} - {p[2]} руб. ({p[4]})\n"
    await update.message.reply_text(text, parse_mode="Markdown")
