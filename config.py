import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@Premium_star_support")

# Цены в копейках (для ЮKassa / Stripe и тд)
PREMIUM_PRICES = {
    "premium_3": {"label": "⭐ Premium 3 мес.", "months": 3, "price": 44900, "display": "449 ₽"},
    "premium_6": {"label": "⭐ Premium 6 мес.", "months": 6, "price": 79900, "display": "799 ₽"},
    "premium_12": {"label": "⭐ Premium 12 мес.", "months": 12, "price": 139900, "display": "1399 ₽"},
}

STARS_PRICES = {
    "stars_50": {"label": "💫 50 Stars", "amount": 50, "price": 7500, "display": "75 ₽"},
    "stars_100": {"label": "💫 100 Stars", "amount": 100, "price": 14000, "display": "140 ₽"},
    "stars_250": {"label": "💫 250 Stars", "amount": 250, "price": 33000, "display": "330 ₽"},
    "stars_500": {"label": "💫 500 Stars", "amount": 500, "price": 62000, "display": "620 ₽"},
    "stars_1000": {"label": "💫 1000 Stars", "amount": 1000, "price": 115000, "display": "1150 ₽"},
}