from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, ContentType
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from config import (
    PREMIUM_PRICES, STARS_PRICES,
    PAYMENT_PROVIDER_TOKEN, SUPPORT_USERNAME, ADMIN_ID
)
from keyboards import (
    main_menu_keyboard, premium_keyboard, stars_keyboard,
    confirm_keyboard, after_payment_keyboard, back_keyboard
)
from database import add_user, create_order, complete_order, get_user_orders, get_stats

router = Router()

# ==================== ТЕКСТЫ ====================

WELCOME_TEXT = """
🌟 <b>Добро пожаловать в Premium Shop!</b> 🌟

Здесь вы можете приобрести:

👑 <b>Telegram Premium</b> — разблокируйте все возможности Telegram!
• Увеличенные лимиты
• Уникальные стикеры и эмодзи
• Быстрая загрузка файлов
• Отсутствие рекламы
• И многое другое!

⭐ <b>Telegram Stars</b> — внутренняя валюта Telegram!
• Поддерживайте авторов
• Покупайте цифровые товары
• Разблокируйте платный контент

✅ Моментальная доставка
🔒 Безопасная оплата
💬 Поддержка 24/7

<i>Выберите категорию:</i>
"""

PREMIUM_TEXT = """
👑 <b>Telegram Premium</b>

Выберите период подписки:

📌 <b>3 месяца</b> — {p3}
📌 <b>6 месяцев</b> — {p6} <i>(выгоднее!)</i>
📌 <b>12 месяцев</b> — {p12} <i>(максимальная выгода!)</i>

✅ Активация в течение нескольких минут после оплаты
⚡ Для активации потребуется ваш @username

<i>Выберите тариф:</i>
""".format(
    p3=PREMIUM_PRICES["premium_3"]["display"],
    p6=PREMIUM_PRICES["premium_6"]["display"],
    p12=PREMIUM_PRICES["premium_12"]["display"]
)

STARS_TEXT = """
⭐ <b>Telegram Stars</b>

Выберите количество звёзд:

💫 <b>50 Stars</b> — {s50}
💫 <b>100 Stars</b> — {s100}
💫 <b>250 Stars</b> — {s250}
💫 <b>500 Stars</b> — {s500}
💫 <b>1000 Stars</b> — {s1000}

✅ Начисление в течение нескольких минут после оплаты
⚡ Stars начисляются на ваш аккаунт Telegram

<i>Выберите количество:</i>
""".format(
    s50=STARS_PRICES["stars_50"]["display"],
    s100=STARS_PRICES["stars_100"]["display"],
    s250=STARS_PRICES["stars_250"]["display"],
    s500=STARS_PRICES["stars_500"]["display"],
    s1000=STARS_PRICES["stars_1000"]["display"]
)

INFO_TEXT = f"""
ℹ️ <b>Информация о сервисе</b>

🏪 <b>Premium Shop</b> — надёжный магазин Telegram Premium и Stars

📌 <b>Как это работает:</b>
1️⃣ Выберите товар
2️⃣ Оплатите удобным способом
3️⃣ Получите в течение нескольких минут!

🔒 <b>Гарантии:</b>
• Безопасная оплата через платёжную систему
• Если товар не доставлен — полный возврат
• Поддержка 24/7

💬 <b>Поддержка:</b> {SUPPORT_USERNAME}

⚠️ <b>Важно:</b> Убедитесь, что у вас установлен @username в настройках Telegram перед покупкой Premium.
"""


def get_product_info(product_key: str) -> dict | None:
    if product_key in PREMIUM_PRICES:
        return {**PREMIUM_PRICES[product_key], "type": "premium"}
    elif product_key in STARS_PRICES:
        return {**STARS_PRICES[product_key], "type": "stars"}
    return None


def get_confirm_text(product_key: str) -> str:
    product = get_product_info(product_key)
    if not product:
        return "Товар не найден"

    if product["type"] == "premium":
        return f"""
🛒 <b>Подтверждение заказа</b>

📦 <b>Товар:</b> {product['label']}
⏱ <b>Период:</b> {product['months']} мес.
💰 <b>Стоимость:</b> {product['display']}

👤 <b>Аккаунт:</b> Ваш текущий Telegram аккаунт

⚠️ <b>После оплаты Premium будет активирован в течение нескольких минут.</b>

Нажмите «💳 Оплатить» для продолжения:
"""
    else:
        return f"""
🛒 <b>Подтверждение заказа</b>

📦 <b>Товар:</b> {product['label']}
🌟 <b>Количество:</b> {product['amount']} Stars
💰 <b>Стоимость:</b> {product['display']}

👤 <b>Аккаунт:</b> Ваш текущий Telegram аккаунт

⚠️ <b>После оплаты Stars будут начислены в течение нескольких минут.</b>

Нажмите «💳 Оплатить» для продолжения:
"""


# ==================== ХЭНДЛЕРЫ ====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "category_premium")
async def show_premium(callback: CallbackQuery):
    await callback.message.edit_text(
        PREMIUM_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=premium_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "category_stars")
async def show_stars(callback: CallbackQuery):
    await callback.message.edit_text(
        STARS_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=stars_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    await callback.message.edit_text(
        INFO_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def show_orders(callback: CallbackQuery):
    orders = await get_user_orders(callback.from_user.id)

    if not orders:
        text = "📋 <b>Мои заказы</b>\n\n🤷 У вас пока нет заказов."
    else:
        text = "📋 <b>Мои заказы</b>\n\n"
        for order in orders:
            status_emoji = "✅" if order["status"] == "paid" else "⏳"
            product = get_product_info(order["product_key"])
            product_name = product["label"] if product else order["product_key"]
            text += (
                f"{status_emoji} <b>#{order['order_id']}</b> — {product_name}\n"
                f"   💰 {order['amount_rub'] / 100:.0f} ₽ | "
                f"{'Оплачен' if order['status'] == 'paid' else 'Ожидает оплаты'}\n"
                f"   📅 {order['created_at'][:16]}\n\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard()
    )
    await callback.answer()


# ==================== ПОКУПКА ====================

@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    product_key = callback.data.replace("buy_", "")
    product = get_product_info(product_key)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await callback.message.edit_text(
        get_confirm_text(product_key),
        parse_mode=ParseMode.HTML,
        reply_markup=confirm_keyboard(product_key)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, bot: Bot):
    product_key = callback.data.replace("pay_", "")
    product = get_product_info(product_key)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Создаём заказ в БД
    order_id = await create_order(
        callback.from_user.id,
        product["type"],
        product_key,
        product["price"]
    )

    # Формируем инвойс
    title = product["label"]
    description = (
        f"Заказ #{order_id}\n"
        f"{'Подписка Telegram Premium на ' + str(product.get('months', '')) + ' мес.' if product['type'] == 'premium' else str(product.get('amount', '')) + ' Telegram Stars'}"
    )

    prices = [
        LabeledPrice(label=product["label"], amount=product["price"])
    ]

    await callback.message.delete()

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=f"order_{order_id}_{product_key}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter=f"buy_{product_key}",
        photo_url="https://i.imgur.com/TqFbMCY.png",
        photo_width=800,
        photo_height=450,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        is_flexible=False,
        protect_content=True
    )
    await callback.answer()


# ==================== ОБРАБОТКА ОПЛАТЫ ====================

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Подтверждаем готовность принять оплату"""
    await pre_checkout_query.answer(ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message: Message, bot: Bot):
    """Обработка успешной оплаты"""
    payment = message.successful_payment
    payload = payment.invoice_payload

    # Парсим payload
    parts = payload.split("_", 2)
    if len(parts) >= 2:
        order_id = int(parts[1])
        product_key = "_".join(parts[2:]) if len(parts) > 2 else ""
    else:
        order_id = 0
        product_key = ""

    # Обновляем заказ в БД
    await complete_order(
        order_id,
        payment.telegram_payment_charge_id,
        payment.provider_payment_charge_id
    )

    product = get_product_info(product_key)
    product_name = product["label"] if product else "Товар"
    product_type = product["type"] if product else "unknown"

    if product_type == "premium":
        delivery_text = "👑 <b>Telegram Premium</b> будет активирован на вашем аккаунте"
    else:
        delivery_text = "⭐ <b>Telegram Stars</b> будут начислены на ваш аккаунт"

    success_text = f"""
✅ <b>Оплата прошла успешно!</b>

🧾 <b>Заказ:</b> #{order_id}
📦 <b>Товар:</b> {product_name}
💰 <b>Сумма:</b> {payment.total_amount / 100:.0f} {payment.currency}

{delivery_text} <b>в течение нескольких минут.</b>

⏳ Пожалуйста, подождите. Обычно это занимает от 1 до 15 минут.

⚠️ <b>Если в течение 30 минут вы не получили товар,
пожалуйста, напишите в поддержку:</b> {SUPPORT_USERNAME}

<i>Укажите номер заказа #{order_id}</i>

Спасибо за покупку! 💜
"""

    await message.answer(
        success_text,
        parse_mode=ParseMode.HTML,
        reply_markup=after_payment_keyboard()
    )

    # Уведомляем админа
    if ADMIN_ID:
        admin_text = f"""
🔔 <b>Новый заказ оплачен!</b>

🧾 <b>Заказ:</b> #{order_id}
👤 <b>Покупатель:</b> {message.from_user.full_name} (@{message.from_user.username or 'нет username'})
🆔 <b>ID:</b> <code>{message.from_user.id}</code>
📦 <b>Товар:</b> {product_name}
💰 <b>Сумма:</b> {payment.total_amount / 100:.0f} {payment.currency}

📎 <b>Telegram charge:</b> <code>{payment.telegram_payment_charge_id}</code>
📎 <b>Provider charge:</b> <code>{payment.provider_payment_charge_id}</code>
"""
        try:
            await bot.send_message(
                ADMIN_ID,
                admin_text,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass


# ==================== АДМИН КОМАНДЫ ====================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users_count, paid_orders, total_revenue = await get_stats()

    await message.answer(
        f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователей:</b> {users_count}
🧾 <b>Оплаченных заказов:</b> {paid_orders}
💰 <b>Общая выручка:</b> {total_revenue / 100:.0f} ₽
""",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "📢 Отправьте сообщение для рассылки (в ответ на это сообщение):",
        parse_mode=ParseMode.HTML
    )