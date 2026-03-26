import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOMONEY_ACCESS_TOKEN = os.getenv("YOOMONEY_ACCESS_TOKEN")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@Premium_star_support")

# =============================================
# ЦЕНЫ со скидкой 35% (округлены)
# =============================================
# Оригинал Premium: 449 / 799 / 1399
# -35%:  292 / 519 / 909
#
# Оригинал Stars: 75 / 140 / 330 / 620 / 1150
# -35%:  49 / 91 / 215 / 403 / 748

PREMIUM_PRICES = {
    "premium_3": {
        "label": "👑 Premium 3 мес.",
        "months": 3,
        "price": 292,
        "display": "292 ₽",
        "old_price": "449 ₽",
    },
    "premium_6": {
        "label": "👑 Premium 6 мес.",
        "months": 6,
        "price": 519,
        "display": "519 ₽",
        "old_price": "799 ₽",
    },
    "premium_12": {
        "label": "👑 Premium 12 мес.",
        "months": 12,
        "price": 909,
        "display": "909 ₽",
        "old_price": "1 399 ₽",
    },
}

STARS_PRICES = {
    "stars_50": {
        "label": "⭐ 50 Stars",
        "amount": 50,
        "price": 49,
        "display": "49 ₽",
        "old_price": "75 ₽",
    },
    "stars_100": {
        "label": "⭐ 100 Stars",
        "amount": 100,
        "price": 91,
        "display": "91 ₽",
        "old_price": "140 ₽",
    },
    "stars_250": {
        "label": "⭐ 250 Stars",
        "amount": 250,
        "price": 215,
        "display": "215 ₽",
        "old_price": "330 ₽",
    },
    "stars_500": {
        "label": "⭐ 500 Stars",
        "amount": 500,
        "price": 403,
        "display": "403 ₽",
        "old_price": "620 ₽",
    },
    "stars_1000": {
        "label": "⭐ 1000 Stars",
        "amount": 1000,
        "price": 748,
        "display": "748 ₽",
        "old_price": "1 150 ₽",
    },
}
