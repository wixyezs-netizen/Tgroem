from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PREMIUM_PRICES, STARS_PRICES, SUPPORT_USERNAME


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="👑 Telegram Premium", callback_data="category_premium"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⭐ Telegram Stars", callback_data="category_stars"
        )
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"),
        InlineKeyboardButton(
            text="💬 Поддержка",
            url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}",
        ),
    )
    return builder.as_markup()


def premium_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, data in PREMIUM_PRICES.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{data['label']} — {data['display']} (было {data['old_price']})",
                callback_data=f"buy_{key}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_main"))
    return builder.as_markup()


def stars_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, data in STARS_PRICES.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{data['label']} — {data['display']} (было {data['old_price']})",
                callback_data=f"buy_{key}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_main"))
    return builder.as_markup()


def payment_keyboard(payment_url: str, order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Оплатить", url=payment_url)
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Проверить оплату", callback_data=f"check_{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")
    )
    return builder.as_markup()


def after_payment_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💬 Поддержка",
            url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")
    )
    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_main"))
    return builder.as_markup()
