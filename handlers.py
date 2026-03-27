from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from config import PRODUCTS, ADMIN_ID
from database import add_payment, update_payment_status, get_pending_payment, get_payment
from yoomoney import create_payment, check_payment

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_PRODUCT, CONFIRMING, WAITING_PAYMENT = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n"
        "Я бот для покупки Telegram Premium, звёзд и NFT.\n"
        "Выберите товар из меню ниже.",
        reply_markup=get_products_keyboard()
    )
    return SELECTING_PRODUCT

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

async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора товара"""
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
    """Подтверждение покупки и создание платежа"""
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

    # Проверяем, нет ли уже ожидающего платежа за этот товар
    existing = get_pending_payment(user_id, product_key)
    if existing:
        await query.edit_message_text(
            "У вас уже есть незавершённый платёж. Оплатите его или подождите.\n"
            "Если вы оплатили, нажмите /check."
        )
        return WAITING_PAYMENT

    # Создаём платёж
    payment_id, confirmation_url = await create_payment(price, product_name, user_id)
    if not confirmation_url:
        await query.edit_message_text(
            f"Не удалось создать платёж: {payment_id}\nПопробуйте позже или обратитесь к администратору."
        )
        return ConversationHandler.END

    # Сохраняем в БД
    add_payment(user_id, product_key, payment_id, price)

    # Сохраняем payment_id в контексте для проверки
    context.user_data["payment_id"] = payment_id

    # Отправляем ссылку на оплату
    pay_message = (
        f"💳 Оплатите {price} руб. на кошелёк ЮMoney.\n\n"
        f"🔗 Ссылка для оплаты:\n{confirmation_url}\n\n"
        "После оплаты нажмите кнопку ниже, чтобы подтвердить."
    )
    keyboard = [[InlineKeyboardButton("✅ Проверить оплату", callback_data="check_payment")]]
    await query.edit_message_text(pay_message, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_PAYMENT

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса платежа"""
    query = update.callback_query
    await query.answer()

    payment_id = context.user_data.get("payment_id")
    if not payment_id:
        await query.edit_message_text("Не найден идентификатор платежа. Попробуйте заново /start")
        return ConversationHandler.END

    # Получаем информацию о платеже из БД
    payment_info = get_payment(payment_id)
    if not payment_info:
        await query.edit_message_text("Платёж не найден.")
        return ConversationHandler.END

    if payment_info["status"] == "success":
        await query.edit_message_text("Этот платёж уже был успешно обработан.")
        return ConversationHandler.END

    # Проверяем через API ЮMoney
    success = await check_payment(payment_id)
    if success:
        # Обновляем статус
        update_payment_status(payment_id, "success")
        # Выдаём товар
        await deliver_product(update, context, payment_info["product"])
        return ConversationHandler.END
    else:
        await query.edit_message_text(
            "Платёж пока не найден. Убедитесь, что вы оплатили, и попробуйте снова через минуту.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Проверить снова", callback_data="check_payment")
            ]])
        )
        return WAITING_PAYMENT

async def deliver_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_key: str):
    """Выдача товара после успешной оплаты"""
    product = PRODUCTS.get(product_key)
    if not product:
        await update.callback_query.edit_message_text("Товар не найден, но оплата прошла. Обратитесь к администратору.")
        return

    user_id = update.effective_user.id
    # Здесь можно реализовать реальную активацию (например, через Telegram API)
    # Для демонстрации просто шлём сообщение с инструкцией
    if product_key == "premium":
        text = (
            "🎉 Поздравляем! Вы приобрели Telegram Premium на 1 месяц.\n"
            "Для активации перейдите по ссылке и следуйте инструкциям:\n"
            "https://t.me/premium?start=your_code_here\n\n"
            "Если возникли проблемы, свяжитесь с @support"
        )
    elif product_key == "stars":
        text = (
            "✨ Вы получили 100 Telegram Stars!\n"
            "Звёзды будут зачислены на ваш аккаунт в течение 5 минут.\n"
            "Спасибо за покупку!"
        )
    elif product_key == "nft":
        text = (
            "🎨 Ваше эксклюзивное NFT отправлено на ваш кошелёк!\n"
            "Адрес: 0x...\n"
            "Ссылка на просмотр: https://opensea.io/...\n"
            "Сохраните этот токен как подтверждение."
        )
    else:
        text = "Товар успешно оплачен. Спасибо за покупку!"

    await update.callback_query.edit_message_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text("Действие отменено. Введите /start для выбора товара.")
    return ConversationHandler.END
