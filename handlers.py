import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from config import (
    PREMIUM_PRICES, STARS_PRICES, SUPPORT_USERNAME,
    ADMIN_ID, YOOMONEY_WALLET,
)
from keyboards import (
    main_menu_keyboard, premium_keyboard, stars_keyboard,
    payment_keyboard, after_payment_keyboard, back_keyboard,
)
from database import (
    add_user, create_order, complete_order,
    get_user_orders, get_stats,
)
from yoomoney_payment import (
    generate_payment_label, check_recent_deposits, get_balance,
)

router = Router()

# ==================== ТЕКСТЫ ====================

WELCOME_TEXT = """
🌟 <b>Добро пожаловать в Premium Shop!</b> 🌟

Здесь вы можете приобрести:

👑 <b>Telegram Premium</b> — все возможности Telegram!
⭐ <b>Telegram Stars</b> — внутренняя валюта Telegram!

🔥 <b>СКИДКА 35% на всё!</b> 🔥

✅ Активация за несколько минут
🔒 Безопасная оплата через ЮMoney
💬 Поддержка 24/7

<i>Выберите категорию:</i>
"""

PREMIUM_TEXT = """
👑 <b>Telegram Premium</b>

🔥 <b>Скидка 35%!</b>

📌 <b>3 месяца</b> — <s>{old3}</s> → <b>{p3}</b>
📌 <b>6 месяцев</b> — <s>{old6}</s> → <b>{p6}</b>
📌 <b>12 месяцев</b> — <s>{old12}</s> → <b>{p12}</b>

✅ Активация за несколько минут
⚡ Потребуется ваш @username
""".format(
    old3=PREMIUM_PRICES["premium_3"]["old_price"],
    p3=PREMIUM_PRICES["premium_3"]["display"],
    old6=PREMIUM_PRICES["premium_6"]["old_price"],
    p6=PREMIUM_PRICES["premium_6"]["display"],
    old12=PREMIUM_PRICES["premium_12"]["old_price"],
    p12=PREMIUM_PRICES["premium_12"]["display"],
)

STARS_TEXT = """
⭐ <b>Telegram Stars</b>

🔥 <b>Скидка 35%!</b>

💫 <b>50 Stars</b> — <s>{old50}</s> → <b>{s50}</b>
💫 <b>100 Stars</b> — <s>{old100}</s> → <b>{s100}</b>
💫 <b>250 Stars</b> — <s>{old250}</s> → <b>{s250}</b>
💫 <b>500 Stars</b> — <s>{old500}</s> → <b>{s500}</b>
💫 <b>1000 Stars</b> — <s>{old1000}</s> → <b>{s1000}</b>

✅ Начисление за несколько минут
""".format(
    old50=STARS_PRICES["stars_50"]["old_price"],
    s50=STARS_PRICES["stars_50"]["display"],
    old100=STARS_PRICES["stars_100"]["old_price"],
    s100=STARS_PRICES["stars_100"]["display"],
    old250=STARS_PRICES["stars_250"]["old_price"],
    s250=STARS_PRICES["stars_250"]["display"],
    old500=STARS_PRICES["stars_500"]["old_price"],
    s500=STARS_PRICES["stars_500"]["display"],
    old1000=STARS_PRICES["stars_1000"]["old_price"],
    s1000=STARS_PRICES["stars_1000"]["display"],
)

INFO_TEXT = f"""
ℹ️ <b>Информация о сервисе</b>

🏪 <b>Premium Shop</b> — магазин Telegram Premium и Stars

📌 <b>Как это работает:</b>
1️⃣ Выберите товар
2️⃣ Переведите точную сумму на ЮMoney кошелёк
3️⃣ <b>Обязательно укажите комментарий</b> (код заказа)
4️⃣ Нажмите «🔄 Проверить оплату»
5️⃣ Получите товар за несколько минут!

🔒 <b>Гарантии:</b>
• Безопасная оплата через ЮMoney
• Поддержка 24/7

💬 <b>Поддержка:</b> {SUPPORT_USERNAME}
"""


# ==================== УТИЛИТЫ ====================

def get_product_info(product_key: str) -> dict | None:
    if product_key in PREMIUM_PRICES:
        return {**PREMIUM_PRICES[product_key], "type": "premium"}
    elif product_key in STARS_PRICES:
        return {**STARS_PRICES[product_key], "type": "stars"}
    return None


# Хранилище заказов в памяти
pending_payments: dict[int, dict] = {}
# order_id -> {"label": str, "product_key": str, "user_id": int, "unique_amount": float}

# Множество уже использованных уникальных сумм (чтобы не совпадали)
used_amounts: set[float] = set()


def make_unique_amount(base_price: int) -> float:
    """
    Генерируем уникальную сумму: базовая цена + случайные копейки.
    Это позволяет отличить один платёж от другого.
    """
    for _ in range(100):
        kopecks = random.randint(1, 99)
        unique = base_price + kopecks / 100.0
        unique = round(unique, 2)
        if unique not in used_amounts:
            used_amounts.add(unique)
            return unique
    # Фоллбэк
    return float(base_price)


# ==================== ХЭНДЛЕРЫ ====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )
    await message.answer(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "category_premium")
async def show_premium(callback: CallbackQuery):
    await callback.message.edit_text(
        PREMIUM_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=premium_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "category_stars")
async def show_stars(callback: CallbackQuery):
    await callback.message.edit_text(
        STARS_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=stars_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    await callback.message.edit_text(
        INFO_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard(),
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
                f"   💰 {order['amount_rub']} ₽ | "
                f"{'Оплачен' if order['status'] == 'paid' else 'Ожидает'}\n"
                f"   📅 {order['created_at'][:16]}\n\n"
            )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_keyboard(),
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

    # Генерируем уникальную сумму
    unique_amount = make_unique_amount(product["price"])

    # Генерируем метку
    label = generate_payment_label()

    # Создаём заказ
    order_id = await create_order(
        user_id=callback.from_user.id,
        product_type=product["type"],
        product_key=product_key,
        amount_rub=product["price"],
        payment_label=label,
    )

    # Сохраняем в память
    pending_payments[order_id] = {
        "label": label,
        "product_key": product_key,
        "user_id": callback.from_user.id,
        "unique_amount": unique_amount,
    }

    # Ссылка на перевод
    payment_url = f"https://yoomoney.ru/to/{YOOMONEY_WALLET}/{unique_amount}"

    if product["type"] == "premium":
        desc = f"👑 {product['label']}\n⏱ Период: {product['months']} мес."
    else:
        desc = f"⭐ {product['label']}\n🌟 Количество: {product['amount']} Stars"

    old_p = product['old_price'].replace(' ', '').replace('₽', '').replace(',', '')
    try:
        saving = int(old_p) - product['price']
    except ValueError:
        saving = 0

    text = f"""
🛒 <b>Заказ #{order_id}</b>

{desc}

💰 <b>К оплате: {unique_amount} ₽</b>
<s>Старая цена: {product['old_price']}</s>
🔥 <b>Вы экономите ~{saving} ₽!</b>

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>Инструкция по оплате:</b>

1️⃣ Нажмите «💳 Оплатить»
2️⃣ Переведите <b>ровно {unique_amount} ₽</b>
   на кошелёк ЮMoney
3️⃣ Вернитесь сюда
4️⃣ Нажмите «🔄 Проверить оплату»

━━━━━━━━━━━━━━━━━━━━━━

💳 <b>Кошелёк:</b> <code>{YOOMONEY_WALLET}</code>
💵 <b>Сумма:</b> <code>{unique_amount}</code> ₽

⚠️ <b>ВАЖНО:</b> переводите <b>точную сумму</b>
{unique_amount} ₽ — иначе платёж не будет найден!

⏳ Заказ действителен 30 минут.
"""

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=payment_keyboard(payment_url, order_id),
    )
    await callback.answer()


# ==================== ПРОВЕРКА ОПЛАТЫ ====================

@router.callback_query(F.data.startswith("check_"))
async def check_payment(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.replace("check_", ""))

    # Ищем заказ
    if order_id in pending_payments:
        data = pending_payments[order_id]
        label = data["label"]
        product_key = data["product_key"]
        unique_amount = data["unique_amount"]
    else:
        import aiosqlite
        async with aiosqlite.connect("bot_database.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM orders WHERE order_id = ?", (order_id,)
            )
            order = await cursor.fetchone()

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        if order["status"] == "paid":
            await callback.answer("✅ Этот заказ уже оплачен!", show_alert=True)
            return

        label = order["payment_label"]
        product_key = order["product_key"]
        unique_amount = float(order["amount_rub"])

    # Проверяем через API
    is_paid = await check_recent_deposits(
        expected_amount=unique_amount,
        comment=label,
    )

    if is_paid:
        await complete_order(order_id)
        pending_payments.pop(order_id, None)
        used_amounts.discard(unique_amount)

        product = get_product_info(product_key)
        product_name = product["label"] if product else "Товар"
        product_type = product["type"] if product else "unknown"

        if product_type == "premium":
            delivery_text = "👑 <b>Telegram Premium</b> будет активирован на вашем аккаунте"
        else:
            delivery_text = "⭐ <b>Telegram Stars</b> будут начислены на ваш аккаунт"

        success_text = f"""
✅ <b>Оплата подтверждена!</b>

🧾 <b>Заказ:</b> #{order_id}
📦 <b>Товар:</b> {product_name}
💰 <b>Сумма:</b> {unique_amount} ₽

━━━━━━━━━━━━━━━━━━━━━━

{delivery_text} <b>в течение нескольких минут.</b>

⏳ Обычно это занимает от 1 до 15 минут.

⚠️ <b>Если в течение 30 минут вы не получили товар,
напишите в поддержку:</b> {SUPPORT_USERNAME}

📎 <i>Укажите номер заказа #{order_id}</i>

━━━━━━━━━━━━━━━━━━━━━━

Спасибо за покупку! 💜
"""

        await callback.message.edit_text(
            success_text,
            parse_mode=ParseMode.HTML,
            reply_markup=after_payment_keyboard(),
        )
        await callback.answer("✅ Оплата получена!", show_alert=True)

        # Уведомляем админа
        if ADMIN_ID:
            admin_text = f"""
🔔 <b>Новая оплата!</b>

🧾 <b>Заказ:</b> #{order_id}
👤 <b>Покупатель:</b> {callback.from_user.full_name} (@{callback.from_user.username or 'нет'})
🆔 <b>ID:</b> <code>{callback.from_user.id}</code>
📦 <b>Товар:</b> {product_name}
💰 <b>Сумма:</b> {unique_amount} ₽
"""
            try:
                await bot.send_message(
                    ADMIN_ID, admin_text, parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
    else:
        await callback.answer(
            "⏳ Оплата пока не найдена.\n\n"
            "Если вы уже оплатили — подождите\n"
            "1-2 минуты и нажмите проверку снова.\n\n"
            f"Убедитесь что перевели ровно {unique_amount} ₽",
            show_alert=True,
        )


# ==================== АДМИН КОМАНДЫ ====================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    users_count, paid_orders, total_revenue = await get_stats()
    balance = await get_balance()

    await message.answer(
        f"""
📊 <b>Статистика бота</b>

👥 <b>Пользователей:</b> {users_count}
🧾 <b>Оплаченных заказов:</b> {paid_orders}
💰 <b>Общая выручка:</b> {total_revenue} ₽
💳 <b>Баланс ЮMoney:</b> {balance}
⏳ <b>Ожидающих оплаты:</b> {len(pending_payments)}
""",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        """
🔧 <b>Админ-панель</b>

/stats — Статистика и баланс
/admin — Это меню
""",
        parse_mode=ParseMode.HTML,
    )
