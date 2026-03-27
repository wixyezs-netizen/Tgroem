#!/usr/bin/env python3
"""
http_wrapper.py — точка входа для BotHost.tech
Telegram Premium Shop Bot + Mini App
"""

import asyncio
import sqlite3
import uuid
import logging
import html
import json
import time
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from urllib.parse import urlencode, unquote

try:
    from aiohttp import web
    import aiohttp as aiohttp_client
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "aiohttp"])
    from aiohttp import web
    import aiohttp as aiohttp_client

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        ConversationHandler, ContextTypes, MessageHandler, filters
    )
    from telegram.constants import ParseMode
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "python-telegram-bot[all]"])
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        ConversationHandler, ContextTypes, MessageHandler, filters
    )
    from telegram.constants import ParseMode

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8633048902:AAF_ae0F_BR1KS-LkNzBE2GcOh1svZLV2L8")
ADMIN_IDS = [8681521200]

YOOMONEY_WALLET = "4100118889570559"
YOOMONEY_ACCESS_TOKEN = "4100118889570559.3288B2E716CEEB922A26BD6BEAC58648FBFB680CCF64E4E1447D714D6FB5EA5F01F1478FAC686BEF394C8A186C98982DE563C1ABCDF9F2F61D971B61DA3C7E486CA818F98B9E0069F1C0891E090DD56A11319D626A40F0AE8302A8339DED9EB7969617F191D93275F64C4127A3ECB7AED33FCDE91CA68690EB7534C67E6C219E"

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://telegram.premium.bothost.tech")
WEBAPP_PORT = int(os.getenv("PORT", "8080"))

CATEGORIES = {
    "premium": {
        "name": "Telegram Premium",
        "emoji": "⭐",
        "icon": "star",
        "products": {
            "premium_1m": {
                "name": "Premium 1 месяц",
                "price": 239,
                "description": "Telegram Premium подписка на 1 месяц",
                "features": [
                    "Уникальные стикеры и реакции",
                    "Без рекламы в каналах",
                    "Загрузка файлов до 4 ГБ",
                    "Быстрая скорость загрузки",
                    "Расшифровка голосовых сообщений",
                    "Управление диалогами"
                ],
                "badge": "",
                "delivery_type": "manual"
            },
            "premium_3m": {
                "name": "Premium 3 месяца",
                "price": 639,
                "description": "Telegram Premium подписка на 3 месяца",
                "features": [
                    "Все преимущества Premium",
                    "Экономия при покупке на 3 месяца",
                    "Приоритетная поддержка"
                ],
                "badge": "Выгодно",
                "delivery_type": "manual"
            },
            "premium_6m": {
                "name": "Premium 6 месяцев",
                "price": 1199,
                "description": "Telegram Premium подписка на 6 месяцев",
                "features": [
                    "Все преимущества Premium",
                    "Лучшее соотношение цена/качество",
                    "Приоритетная поддержка"
                ],
                "badge": "Популярный",
                "delivery_type": "manual"
            },
            "premium_12m": {
                "name": "Premium 12 месяцев",
                "price": 2159,
                "description": "Telegram Premium подписка на 12 месяцев",
                "features": [
                    "Все преимущества Premium",
                    "Самая низкая цена за месяц",
                    "VIP поддержка"
                ],
                "badge": "Лучшая цена",
                "delivery_type": "manual"
            },
        }
    },
    "stars": {
        "name": "Telegram Stars",
        "emoji": "🌟",
        "icon": "stars",
        "products": {
            "stars_50": {
                "name": "50 Stars",
                "price": 60,
                "description": "50 Telegram Stars на ваш аккаунт",
                "features": [
                    "Поддержка авторов контента",
                    "Покупки в ботах и мини-приложениях",
                    "Оплата цифровых товаров"
                ],
                "badge": "",
                "delivery_type": "manual"
            },
            "stars_100": {
                "name": "100 Stars",
                "price": 112,
                "description": "100 Telegram Stars на ваш аккаунт",
                "features": [
                    "Поддержка авторов контента",
                    "Покупки в ботах",
                    "Выгоднее чем 50 штук"
                ],
                "badge": "",
                "delivery_type": "manual"
            },
            "stars_250": {
                "name": "250 Stars",
                "price": 264,
                "description": "250 Telegram Stars на ваш аккаунт",
                "features": [
                    "Поддержка авторов контента",
                    "Покупки в ботах",
                    "Хорошая скидка"
                ],
                "badge": "Выгодно",
                "delivery_type": "manual"
            },
            "stars_500": {
                "name": "500 Stars",
                "price": 496,
                "description": "500 Telegram Stars на ваш аккаунт",
                "features": [
                    "Поддержка авторов контента",
                    "Покупки в ботах",
                    "Максимальная выгода"
                ],
                "badge": "Хит продаж",
                "delivery_type": "manual"
            },
        }
    },
    "nft": {
        "name": "NFT Коллекция",
        "emoji": "🎨",
        "icon": "nft",
        "products": {
            "nft_basic": {
                "name": "NFT Basic",
                "price": 159,
                "description": "Базовый NFT из нашей коллекции",
                "features": [
                    "Уникальный дизайн",
                    "Подтверждение в блокчейне TON",
                    "Можно перепродать"
                ],
                "badge": "",
                "delivery_type": "manual"
            },
            "nft_rare": {
                "name": "NFT Rare",
                "price": 399,
                "description": "Редкий NFT лимитированной серии",
                "features": [
                    "Лимитированная серия",
                    "Редкий уникальный дизайн",
                    "Высокая коллекционная ценность"
                ],
                "badge": "Редкий",
                "delivery_type": "manual"
            },
            "nft_legendary": {
                "name": "NFT Legendary",
                "price": 799,
                "description": "Легендарный NFT — всего 100 штук в мире",
                "features": [
                    "Всего 100 штук в мире",
                    "Легендарный статус владельца",
                    "Максимальная коллекционная ценность"
                ],
                "badge": "Легендарный",
                "delivery_type": "manual"
            },
        }
    }
}

CHECK_INTERVAL = 30
PAYMENT_TIMEOUT_HOURS = 24
DB_NAME = os.getenv("DB_PATH", "/app/data/bot_shop.db")

(MAIN_MENU, SELECTING_CATEGORY, SELECTING_PRODUCT, PRODUCT_DETAIL,
 ENTERING_PROMO, CONFIRMING, WAITING_PAYMENT, ADMIN_MENU,
 ADMIN_MANUAL_ID, ADMIN_ADD_PROMO, ADMIN_BROADCAST) = range(11)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ShopBot")


# ==================== MINI APP HTML ====================
MINI_APP_HTML = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>Telegram Premium Shop</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root{
--bg:#fff;--text:#000;--hint:#999;--link:#2481cc;
--btn:#3390ec;--btn-text:#fff;--sec-bg:#f0f0f0;
--section-bg:#fff;--sep:#e0e0e0;--accent:#3390ec;
--destructive:#e53935;--subtitle:#999
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:var(--sec-bg);color:var(--text);
min-height:100vh;overflow-x:hidden;padding-bottom:100px
}
.header{
background:linear-gradient(135deg,#2481cc 0%,#3390ec 50%,#50a0f0 100%);
padding:20px 16px 24px;text-align:center;position:relative;overflow:hidden
}
.header::before{
content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
background:radial-gradient(circle,rgba(255,255,255,.1) 0%,transparent 60%);
animation:hs 8s ease-in-out infinite
}
@keyframes hs{0%,100%{transform:rotate(0)}50%{transform:rotate(180deg)}}
.header-logo{
width:64px;height:64px;margin:0 auto 12px;
background:rgba(255,255,255,.2);border-radius:50%;
display:flex;align-items:center;justify-content:center;
font-size:32px;backdrop-filter:blur(10px);position:relative;z-index:1
}
.header h1{color:#fff;font-size:22px;font-weight:700;margin-bottom:4px;position:relative;z-index:1}
.header p{color:rgba(255,255,255,.85);font-size:14px;position:relative;z-index:1}
.promo-banner{
margin:12px 16px;
background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
border-radius:14px;padding:16px;color:#fff;
position:relative;overflow:hidden;cursor:pointer;transition:transform .2s
}
.promo-banner:active{transform:scale(.98)}
.promo-banner::after{
content:'🎁';position:absolute;right:16px;top:50%;
transform:translateY(-50%);font-size:32px;opacity:.8
}
.promo-banner h3{font-size:16px;font-weight:600;margin-bottom:4px}
.promo-banner p{font-size:13px;opacity:.9}
.tabs{
display:flex;gap:8px;padding:12px 16px;overflow-x:auto;
scrollbar-width:none;-ms-overflow-style:none
}
.tabs::-webkit-scrollbar{display:none}
.tab{
flex-shrink:0;padding:10px 20px;border-radius:20px;border:none;
font-size:14px;font-weight:600;cursor:pointer;transition:all .3s;
background:var(--section-bg);color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.08)
}
.tab.active{
background:var(--btn);color:var(--btn-text);
box-shadow:0 2px 8px rgba(51,144,236,.3)
}
.tab:active{transform:scale(.95)}
.products{padding:0 16px}
.stitle{
font-size:13px;font-weight:600;color:var(--hint);
text-transform:uppercase;letter-spacing:.5px;margin:16px 0 10px 4px
}
.plist{display:flex;flex-direction:column;gap:8px}
.pcard{
background:var(--section-bg);border-radius:14px;padding:16px;
cursor:pointer;transition:all .2s;position:relative;overflow:hidden
}
.pcard:active{transform:scale(.98);background:var(--sec-bg)}
.pcard-top{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.picon{
width:48px;height:48px;border-radius:12px;
display:flex;align-items:center;justify-content:center;
font-size:24px;flex-shrink:0
}
.picon.star{background:linear-gradient(135deg,#FFD700,#FFA500)}
.picon.stars{background:linear-gradient(135deg,#9C27B0,#E040FB)}
.picon.nft{background:linear-gradient(135deg,#00BCD4,#2196F3)}
.pinfo{flex:1;min-width:0}
.pname{font-size:16px;font-weight:600;margin-bottom:2px}
.pdesc{font-size:13px;color:var(--hint);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pprice-row{display:flex;align-items:center;justify-content:space-between}
.pprice{font-size:18px;font-weight:700}
.pprice .cur{font-size:14px;font-weight:500;color:var(--hint)}
.bbtn{
padding:8px 20px;border-radius:20px;border:none;
background:var(--btn);color:var(--btn-text);
font-size:14px;font-weight:600;cursor:pointer;transition:all .2s
}
.bbtn:active{transform:scale(.95);opacity:.9}
.badge{
position:absolute;top:12px;right:12px;padding:4px 10px;
border-radius:10px;font-size:11px;font-weight:700;color:#fff;
background:linear-gradient(135deg,#FF6B6B,#FF8E53)
}
.badge.popular{background:linear-gradient(135deg,#3390ec,#50a0f0)}
.badge.best{background:linear-gradient(135deg,#00C853,#64DD17)}
.badge.rare{background:linear-gradient(135deg,#9C27B0,#E040FB)}
.badge.legendary{background:linear-gradient(135deg,#FF6D00,#FFD600)}
.modal-ov{
position:fixed;top:0;left:0;right:0;bottom:0;
background:rgba(0,0,0,.5);z-index:1000;
display:none;align-items:flex-end;justify-content:center
}
.modal-ov.active{display:flex}
.modal-c{
background:var(--bg);border-radius:20px 20px 0 0;
width:100%;max-height:85vh;overflow-y:auto;
animation:su .3s ease;padding-bottom:env(safe-area-inset-bottom,20px)
}
@keyframes su{from{transform:translateY(100%)}to{transform:translateY(0)}}
.modal-handle{
width:36px;height:4px;background:var(--hint);opacity:.3;
border-radius:2px;margin:10px auto 0
}
.modal-hdr{padding:20px 20px 0;text-align:center}
.modal-icon{
width:72px;height:72px;border-radius:18px;margin:0 auto 14px;
display:flex;align-items:center;justify-content:center;font-size:36px
}
.modal-title{font-size:22px;font-weight:700;margin-bottom:6px}
.modal-mprice{font-size:28px;font-weight:800;color:var(--btn);margin-bottom:4px}
.modal-desc{font-size:14px;color:var(--hint);margin-bottom:20px;line-height:1.4}
.flist{padding:0 20px;margin-bottom:20px}
.fitem{
display:flex;align-items:center;gap:12px;padding:12px 0;
border-bottom:.5px solid var(--sep)
}
.fitem:last-child{border-bottom:none}
.ficon{
width:32px;height:32px;border-radius:8px;background:var(--sec-bg);
display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0
}
.ftext{font-size:15px}
.promo-sec{padding:0 20px;margin-bottom:16px}
.promo-wrap{display:flex;gap:8px}
.promo-in{
flex:1;padding:12px 16px;border-radius:12px;
border:1.5px solid var(--sep);background:var(--sec-bg);
color:var(--text);font-size:15px;outline:none;transition:border-color .2s
}
.promo-in:focus{border-color:var(--btn)}
.promo-btn{
padding:12px 20px;border-radius:12px;border:none;
background:var(--btn);color:var(--btn-text);
font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap
}
.promo-res{
margin-top:8px;font-size:13px;padding:8px 12px;border-radius:8px;display:none
}
.promo-res.ok{display:block;background:rgba(76,175,80,.1);color:#4CAF50}
.promo-res.err{display:block;background:rgba(244,67,54,.1);color:#F44336}
.modal-ft{
padding:16px 20px;position:sticky;bottom:0;
background:var(--bg);border-top:.5px solid var(--sep)
}
.modal-bbtn{
width:100%;padding:16px;border-radius:14px;border:none;
background:var(--btn);color:var(--btn-text);
font-size:17px;font-weight:700;cursor:pointer;
display:flex;align-items:center;justify-content:center;gap:8px;transition:all .2s
}
.modal-bbtn:active{transform:scale(.98);opacity:.9}
.modal-bbtn:disabled{opacity:.5;cursor:not-allowed}
.pay-screen{display:none;text-align:center;padding:30px 20px}
.pay-screen.active{display:block}
.pay-loader{
width:48px;height:48px;border:3px solid var(--sep);
border-top-color:var(--btn);border-radius:50%;
animation:spin .8s linear infinite;margin:0 auto 20px
}
@keyframes spin{to{transform:rotate(360deg)}}
.pay-status{font-size:18px;font-weight:600;margin-bottom:10px}
.pay-info{font-size:14px;color:var(--hint);line-height:1.5;margin-bottom:20px}
.pay-link{
display:inline-block;padding:14px 32px;border-radius:14px;
background:var(--btn);color:var(--btn-text);text-decoration:none;
font-size:16px;font-weight:600;margin-bottom:12px;transition:all .2s
}
.pay-link:active{transform:scale(.98)}
.check-btn{
display:block;width:100%;padding:14px;border-radius:14px;
border:2px solid var(--btn);background:transparent;
color:var(--btn);font-size:16px;font-weight:600;cursor:pointer;
margin-top:12px;transition:all .2s
}
.check-btn:active{background:var(--btn);color:var(--btn-text)}
.suc-screen{display:none;text-align:center;padding:40px 20px}
.suc-screen.active{display:block}
.suc-icon{
width:80px;height:80px;border-radius:50%;
background:linear-gradient(135deg,#4CAF50,#66BB6A);
display:flex;align-items:center;justify-content:center;
margin:0 auto 20px;font-size:40px;animation:sp .5s ease
}
@keyframes sp{0%{transform:scale(0)}60%{transform:scale(1.2)}100%{transform:scale(1)}}
.orders-page{display:none}
.orders-page.active{display:block}
.ocard{background:var(--section-bg);border-radius:14px;padding:16px;margin:8px 16px}
.ohdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.oid{font-size:13px;color:var(--hint)}
.ost{font-size:12px;font-weight:600;padding:4px 10px;border-radius:8px}
.ost.success{background:rgba(76,175,80,.1);color:#4CAF50}
.ost.pending{background:rgba(255,152,0,.1);color:#FF9800}
.ost.expired{background:rgba(244,67,54,.1);color:#F44336}
.ost.cancelled{background:rgba(158,158,158,.1);color:#9E9E9E}
.oprod{font-size:16px;font-weight:600;margin-bottom:4px}
.oamt{font-size:15px;font-weight:700;color:var(--btn)}
.odate{font-size:12px;color:var(--hint);margin-top:6px}
.bnav{
position:fixed;bottom:0;left:0;right:0;background:var(--bg);
border-top:.5px solid var(--sep);display:flex;padding:8px 0;
padding-bottom:max(8px,env(safe-area-inset-bottom));z-index:900
}
.bnav-item{
flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;
padding:6px 0;cursor:pointer;border:none;background:none;
color:var(--hint);font-size:11px;font-weight:500;transition:all .2s
}
.bnav-item.active{color:var(--btn)}
.bnav-item svg{width:24px;height:24px}
.bnav-item:active{transform:scale(.9)}
.toast{
position:fixed;top:20px;left:50%;
transform:translateX(-50%) translateY(-100px);
padding:12px 24px;border-radius:12px;
background:var(--text);color:var(--bg);
font-size:14px;font-weight:500;z-index:2000;
transition:transform .3s ease;white-space:nowrap
}
.toast.show{transform:translateX(-50%) translateY(0)}
.empty-state{text-align:center;padding:60px 20px;color:var(--hint)}
.empty-state .em{font-size:48px;margin-bottom:16px}
.empty-state p{font-size:15px;line-height:1.5}
::-webkit-scrollbar{width:0}
</style>
</head>
<body>
<div class="toast" id="toast"></div>

<div id="mainPage">
<div class="header">
<div class="header-logo">💎</div>
<h1>Premium Shop</h1>
<p>Официальные продукты Telegram</p>
</div>
<div class="promo-banner" onclick="showPromoModal()">
<h3>Есть промокод?</h3>
<p>Примените и получите скидку</p>
</div>
<div class="tabs" id="tabs"></div>
<div class="products">
<div class="stitle" id="stitle">Все товары</div>
<div class="plist" id="plist"></div>
</div>
</div>

<div class="orders-page" id="ordersPage">
<div class="header" style="padding:16px">
<h1 style="font-size:20px">Мои покупки</h1>
</div>
<div id="ordersList"></div>
</div>

<div class="modal-ov" id="productModal" onclick="closeModalOut(event)">
<div class="modal-c" id="modalC">
<div class="modal-handle"></div>
<div id="mProductView">
<div class="modal-hdr">
<div class="modal-icon" id="mIcon">⭐</div>
<div class="modal-title" id="mTitle"></div>
<div class="modal-mprice" id="mPrice"></div>
<div class="modal-desc" id="mDesc"></div>
</div>
<div class="flist" id="flist"></div>
<div class="promo-sec">
<div class="promo-wrap">
<input type="text" class="promo-in" id="promoIn" placeholder="Промокод" autocapitalize="characters">
<button class="promo-btn" onclick="applyPromo()">ОК</button>
</div>
<div class="promo-res" id="promoRes"></div>
</div>
<div class="modal-ft">
<button class="modal-bbtn" id="buyBtn" onclick="createPayment()">
<span>Купить</span><span id="buyPrice"></span>
</button>
</div>
</div>
<div class="pay-screen" id="payScreen">
<div class="pay-loader"></div>
<div class="pay-status">Ожидание оплаты</div>
<div class="pay-info" id="payInfo"></div>
<a class="pay-link" id="payLink" href="#" target="_blank">💳 Оплатить</a>
<button class="check-btn" onclick="checkPay()">✅ Проверить оплату</button>
<button class="check-btn" onclick="cancelPay()" style="border-color:var(--destructive);color:var(--destructive);margin-top:8px">❌ Отменить</button>
</div>
<div class="suc-screen" id="sucScreen">
<div class="suc-icon">✓</div>
<div class="pay-status" style="color:#4CAF50">Оплата подтверждена!</div>
<div class="pay-info">Товар будет выдан в ближайшее время.<br>Вы получите уведомление в боте.</div>
<button class="modal-bbtn" onclick="closeModal()" style="margin-top:20px">Отлично!</button>
</div>
</div>
</div>

<div class="modal-ov" id="promoModal" onclick="closePromoM(event)">
<div class="modal-c" style="max-height:40vh">
<div class="modal-handle"></div>
<div style="padding:20px">
<div class="modal-title" style="margin-bottom:16px">🎁 Промокод</div>
<div class="promo-wrap">
<input type="text" class="promo-in" id="gPromoIn" placeholder="Введите промокод" autocapitalize="characters">
<button class="promo-btn" onclick="checkGlobalPromo()">Проверить</button>
</div>
<div class="promo-res" id="gPromoRes"></div>
</div>
</div>
</div>

<div class="bnav">
<button class="bnav-item active" onclick="showPage('main')" id="navMain">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
<span>Магазин</span>
</button>
<button class="bnav-item" onclick="showPage('orders')" id="navOrders">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
<span>Покупки</span>
</button>
<button class="bnav-item" onclick="showPage('profile')" id="navProfile">
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
<span>Профиль</span>
</button>
</div>

<script>
const tg=window.Telegram.WebApp;
tg.ready();tg.expand();
try{tg.enableClosingConfirmation()}catch(e){}

const API='';
let curCat='all',selProd=null,selCatKey='',selProdKey='';
let curPayId=null,curPayLabel=null,disc=0,promoCode='',chkInt=null;
const CATS=''' + json.dumps(CATEGORIES, ensure_ascii=False) + ''';

function init(){renderTabs();renderProds('all');applyTheme()}

function applyTheme(){
const r=document.documentElement,t=tg.themeParams;if(!t)return;
const m={bg_color:'--bg',text_color:'--text',hint_color:'--hint',link_color:'--link',
button_color:'--btn',button_text_color:'--btn-text',secondary_bg_color:'--sec-bg',
section_bg_color:'--section-bg',section_separator_color:'--sep',
subtitle_text_color:'--subtitle',destructive_text_color:'--destructive',
accent_text_color:'--accent'};
for(const[k,v]of Object.entries(m))if(t[k])r.style.setProperty(v,t[k]);
}

function renderTabs(){
const c=document.getElementById('tabs');
let h='<button class="tab active" onclick="filterCat(\'all\',this)">Все</button>';
for(const[k,v]of Object.entries(CATS))
h+=`<button class="tab" onclick="filterCat('${k}',this)">${v.emoji} ${v.name}</button>`;
c.innerHTML=h
}

function renderProds(cat){
const c=document.getElementById('plist'),t=document.getElementById('stitle');
let h='';
for(const[ck,cv]of Object.entries(CATS)){
if(cat!=='all'&&cat!==ck)continue;
for(const[pk,p]of Object.entries(cv.products)){
const b=p.badge?`<div class="badge ${badgeCls(p.badge)}">${p.badge}</div>`:'';
h+=`<div class="pcard" onclick="openProd('${ck}','${pk}')">
${b}<div class="pcard-top">
<div class="picon ${cv.icon}">${cv.emoji}</div>
<div class="pinfo"><div class="pname">${p.name}</div>
<div class="pdesc">${p.description}</div></div></div>
<div class="pprice-row"><div class="pprice">${p.price} <span class="cur">₽</span></div>
<button class="bbtn" onclick="event.stopPropagation();openProd('${ck}','${pk}')">Купить</button>
</div></div>`;
}}
c.innerHTML=h||'<div class="empty-state"><div class="em">📭</div><p>Товары не найдены</p></div>';
t.textContent=cat==='all'?'Все товары':(CATS[cat]?.name||'Товары')
}

function badgeCls(b){
return{Популярный:'popular','Лучшая цена':'best',Выгодно:'popular',
'Хит продаж':'popular',Редкий:'rare',Легендарный:'legendary'}[b]||''
}

function filterCat(c,btn){
curCat=c;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
btn.classList.add('active');renderProds(c);
try{tg.HapticFeedback.selectionChanged()}catch(e){}
}

function showPage(p){
document.getElementById('mainPage').style.display=p==='main'?'block':'none';
document.getElementById('ordersPage').className=p==='orders'?'orders-page active':'orders-page';
document.querySelectorAll('.bnav-item').forEach(n=>n.classList.remove('active'));
if(p==='main')document.getElementById('navMain').classList.add('active');
else if(p==='orders'){document.getElementById('navOrders').classList.add('active');loadOrders()}
else if(p==='profile'){
document.getElementById('navProfile').classList.add('active');
tg.showAlert('👤 Профиль доступен в боте\\n\\nИспользуйте /start');
setTimeout(()=>{document.getElementById('navMain').classList.add('active');
document.getElementById('navProfile').classList.remove('active')},100)
}
try{tg.HapticFeedback.selectionChanged()}catch(e){}
}

async function loadOrders(){
const c=document.getElementById('ordersList');
c.innerHTML='<div class="empty-state"><div class="pay-loader"></div><p>Загрузка...</p></div>';
try{
const r=await fetch(`${API}/api/orders?initData=${encodeURIComponent(tg.initData||'')}`);
const d=await r.json();
if(!d.orders||!d.orders.length){
c.innerHTML='<div class="empty-state"><div class="em">📭</div><p>Покупок пока нет</p></div>';return}
let h='';
for(const o of d.orders){
const sc=o.status==='success'?'success':o.status==='pending'?'pending':
o.status==='cancelled'?'cancelled':'expired';
const st=o.status==='success'?'Оплачен':o.status==='pending'?'Ожидает':
o.status==='cancelled'?'Отменён':'Истёк';
h+=`<div class="ocard"><div class="ohdr"><span class="oid">#${o.id}</span>
<span class="ost ${sc}">${st}</span></div>
<div class="oprod">${o.product_name}</div>
<div class="oamt">${o.amount} ₽</div>
<div class="odate">${o.created_at||''}</div></div>`
}
c.innerHTML=h
}catch(e){c.innerHTML='<div class="empty-state"><p>Ошибка загрузки</p></div>'}
}

function openProd(ck,pk){
const cat=CATS[ck],p=cat.products[pk];if(!p)return;
selCatKey=ck;selProdKey=pk;selProd=p;disc=0;promoCode='';
document.getElementById('mIcon').className=`modal-icon picon ${cat.icon}`;
document.getElementById('mIcon').textContent=cat.emoji;
document.getElementById('mTitle').textContent=p.name;
document.getElementById('mPrice').textContent=p.price+' ₽';
document.getElementById('mDesc').textContent=p.description;
document.getElementById('flist').innerHTML=(p.features||[]).map(f=>
`<div class="fitem"><div class="ficon">✓</div><div class="ftext">${f}</div></div>`).join('');
document.getElementById('buyPrice').textContent=`за ${p.price} ₽`;
document.getElementById('promoIn').value='';
const pr=document.getElementById('promoRes');pr.className='promo-res';pr.style.display='none';
document.getElementById('buyBtn').disabled=false;
showMView('product');
document.getElementById('productModal').classList.add('active');
try{tg.HapticFeedback.impactOccurred('medium')}catch(e){}
}

function showMView(v){
document.getElementById('mProductView').style.display=v==='product'?'block':'none';
document.getElementById('payScreen').className=v==='payment'?'pay-screen active':'pay-screen';
document.getElementById('sucScreen').className=v==='success'?'suc-screen active':'suc-screen';
}

function closeModal(){
document.getElementById('productModal').classList.remove('active');
if(chkInt){clearInterval(chkInt);chkInt=null}
selProd=null;curPayId=null;curPayLabel=null
}

function closeModalOut(e){if(e.target===document.getElementById('productModal'))closeModal()}

async function applyPromo(){
const code=document.getElementById('promoIn').value.trim().toUpperCase();
if(!code)return;
const res=document.getElementById('promoRes');
try{
const r=await fetch(`${API}/api/promo/check`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({code,amount:selProd.price,initData:tg.initData||''})});
const d=await r.json();
if(d.valid){
disc=d.discount;promoCode=code;
const np=Math.max(1,Math.round(selProd.price*(100-d.discount)/100));
res.className='promo-res ok';res.textContent=`✅ Скидка ${d.discount}%! Цена: ${np} ₽`;res.style.display='block';
document.getElementById('mPrice').innerHTML=
`<s style="color:var(--hint);font-size:18px">${selProd.price} ₽</s> ${np} ₽`;
document.getElementById('buyPrice').textContent=`за ${np} ₽`;
try{tg.HapticFeedback.notificationOccurred('success')}catch(e){}
}else{
res.className='promo-res err';res.textContent=d.message||'❌ Недействителен';res.style.display='block';
try{tg.HapticFeedback.notificationOccurred('error')}catch(e){}
}
}catch(e){res.className='promo-res err';res.textContent='❌ Ошибка';res.style.display='block'}
}

function showPromoModal(){
document.getElementById('promoModal').classList.add('active');
document.getElementById('gPromoIn').value='';
document.getElementById('gPromoRes').style.display='none';
try{tg.HapticFeedback.impactOccurred('light')}catch(e){}
}

function closePromoM(e){if(e.target===document.getElementById('promoModal'))
document.getElementById('promoModal').classList.remove('active')}

async function checkGlobalPromo(){
const code=document.getElementById('gPromoIn').value.trim().toUpperCase();
if(!code)return;const res=document.getElementById('gPromoRes');
try{
const r=await fetch(`${API}/api/promo/check`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({code,amount:0,initData:tg.initData||''})});
const d=await r.json();
if(d.valid){res.className='promo-res ok';
res.textContent=`✅ Действителен! Скидка ${d.discount}%`;res.style.display='block';
try{tg.HapticFeedback.notificationOccurred('success')}catch(e){}
}else{res.className='promo-res err';
res.textContent=d.message||'❌ Недействителен';res.style.display='block';
try{tg.HapticFeedback.notificationOccurred('error')}catch(e){}
}
}catch(e){res.className='promo-res err';res.textContent='❌ Ошибка';res.style.display='block'}
}

async function createPayment(){
if(!selProd)return;
const btn=document.getElementById('buyBtn');
btn.disabled=true;btn.innerHTML='<span>Создание...</span>';
let price=selProd.price;
if(disc>0)price=Math.max(1,Math.round(price*(100-disc)/100));
try{
const r=await fetch(`${API}/api/payment/create`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({category:selCatKey,product:selProdKey,
promo_code:promoCode||null,discount:disc,initData:tg.initData||''})});
const d=await r.json();
if(d.success){
curPayId=d.payment_id;curPayLabel=d.label;
document.getElementById('payInfo').innerHTML=
`📦 ${selProd.name}<br>💰 ${d.amount} ₽<br><br>Оплатите и нажмите "Проверить"`;
document.getElementById('payLink').href=d.payment_url;
showMView('payment');
try{tg.HapticFeedback.notificationOccurred('success')}catch(e){}
chkInt=setInterval(autoCheck,15000)
}else{
showToast(d.message||'Ошибка');btn.disabled=false;
btn.innerHTML=`<span>Купить</span><span id="buyPrice">за ${price} ₽</span>`
}
}catch(e){
showToast('Ошибка сети');btn.disabled=false;
btn.innerHTML=`<span>Купить</span><span id="buyPrice">за ${price} ₽</span>`
}
}

async function checkPay(){
if(!curPayId)return;showToast('Проверяю...');
try{
const r=await fetch(`${API}/api/payment/check`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({payment_id:curPayId,initData:tg.initData||''})});
const d=await r.json();
if(d.paid){
if(chkInt){clearInterval(chkInt);chkInt=null}
showMView('success');
try{tg.HapticFeedback.notificationOccurred('success')}catch(e){}
}else{showToast('⏳ Не найден');
try{tg.HapticFeedback.notificationOccurred('warning')}catch(e){}
}
}catch(e){showToast('Ошибка')}
}

async function autoCheck(){
if(!curPayId)return;
try{
const r=await fetch(`${API}/api/payment/check`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({payment_id:curPayId,initData:tg.initData||''})});
const d=await r.json();
if(d.paid){
if(chkInt){clearInterval(chkInt);chkInt=null}
showMView('success');
try{tg.HapticFeedback.notificationOccurred('success')}catch(e){}
}
}catch(e){}
}

async function cancelPay(){
if(!curPayId)return;
tg.showConfirm('Отменить платёж?',async(ok)=>{
if(!ok)return;
try{await fetch(`${API}/api/payment/cancel`,{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({payment_id:curPayId,initData:tg.initData||''})})}catch(e){}
if(chkInt){clearInterval(chkInt);chkInt=null}
closeModal();showToast('Отменён')
})
}

function showToast(m){
const t=document.getElementById('toast');t.textContent=m;
t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500)
}

init();
</script>
</body>
</html>'''


# ==================== DATABASE ====================
class Database:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        os.makedirs(os.path.dirname(db_name) if os.path.dirname(db_name) else '.', exist_ok=True)

    def get_conn(self):
        conn = sqlite3.connect(self.db_name, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except:
            pass
        return conn

    def init_db(self):
        conn = self.get_conn()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,
                last_name TEXT,language_code TEXT,referrer_id INTEGER,
                total_spent INTEGER DEFAULT 0,is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,product_key TEXT NOT NULL,
                category TEXT NOT NULL,payment_id TEXT NOT NULL UNIQUE,
                payment_label TEXT,amount INTEGER NOT NULL,
                original_amount INTEGER,promo_code TEXT,
                discount INTEGER DEFAULT 0,status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'not_delivered',
                delivery_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,delivered_at TIMESTAMP,expires_at TIMESTAMP);
            CREATE TABLE IF NOT EXISTS promo_codes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,discount_percent INTEGER NOT NULL,
                max_uses INTEGER DEFAULT -1,current_uses INTEGER DEFAULT 0,
                min_amount INTEGER DEFAULT 0,created_by INTEGER,
                expires_at TIMESTAMP,is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS referrals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,referred_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS admin_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,action TEXT NOT NULL,
                details TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS idx_ps ON payments(status);
            CREATE INDEX IF NOT EXISTS idx_pu ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_pl ON payments(payment_label);
        ''')
        conn.commit()
        conn.close()
        logger.info("DB initialized")

    def get_or_create_user(self, user_id, username=None, first_name=None,
                           last_name=None, language_code=None, referrer_id=None):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        u = cur.fetchone()
        if not u:
            cur.execute("INSERT INTO users(user_id,username,first_name,last_name,language_code,referrer_id)VALUES(?,?,?,?,?,?)",
                        (user_id, username, first_name, last_name, language_code, referrer_id))
            conn.commit()
            if referrer_id and referrer_id != user_id:
                cur.execute("INSERT OR IGNORE INTO referrals(referrer_id,referred_id)VALUES(?,?)",
                            (referrer_id, user_id))
                conn.commit()
        else:
            cur.execute("UPDATE users SET username=?,first_name=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                        (username, first_name, user_id))
            conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        u = cur.fetchone()
        r = dict(u) if u else {}
        conn.close()
        return r

    def get_user(self, uid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
        r = cur.fetchone()
        conn.close()
        return dict(r) if r else None

    def get_all_users(self):
        conn = self.get_conn()
        r = [dict(x) for x in conn.execute("SELECT * FROM users").fetchall()]
        conn.close()
        return r

    def add_payment(self, user_id, product_key, category, payment_id, payment_label,
                    amount, original_amount=None, promo_code=None, discount=0):
        conn = self.get_conn()
        exp = (datetime.now() + timedelta(hours=PAYMENT_TIMEOUT_HOURS)).isoformat()
        cur = conn.cursor()
        cur.execute("INSERT INTO payments(user_id,product_key,category,payment_id,payment_label,amount,original_amount,promo_code,discount,expires_at)VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (user_id, product_key, category, payment_id, payment_label, amount, original_amount or amount, promo_code, discount, exp))
        conn.commit()
        rid = cur.lastrowid
        conn.close()
        return rid

    def get_payment(self, pid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE payment_id=?", (pid,))
        r = cur.fetchone()
        conn.close()
        return dict(r) if r else None

    def get_payment_by_row_id(self, rid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE id=?", (rid,))
        r = cur.fetchone()
        conn.close()
        return dict(r) if r else None

    def update_payment_status(self, pid, status):
        conn = self.get_conn()
        pa = datetime.now().isoformat() if status == "success" else None
        conn.execute("UPDATE payments SET status=?,paid_at=? WHERE payment_id=?", (status, pa, pid))
        conn.commit()
        conn.close()

    def mark_delivered(self, pid, info=""):
        conn = self.get_conn()
        conn.execute("UPDATE payments SET delivery_status='delivered',delivery_info=?,delivered_at=CURRENT_TIMESTAMP WHERE payment_id=?", (info, pid))
        conn.commit()
        conn.close()

    def get_pending_payments(self):
        conn = self.get_conn()
        r = [dict(x) for x in conn.execute("SELECT * FROM payments WHERE status='pending' AND expires_at>datetime('now')").fetchall()]
        conn.close()
        return r

    def expire_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE payments SET status='expired' WHERE status='pending' AND expires_at<=datetime('now')")
        conn.commit()
        c = cur.rowcount
        conn.close()
        return c

    def get_user_payments(self, uid, limit=20):
        conn = self.get_conn()
        r = [dict(x) for x in conn.execute("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()]
        conn.close()
        return r

    def get_user_active_payment(self, uid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE user_id=? AND status='pending' AND expires_at>datetime('now') ORDER BY created_at DESC LIMIT 1", (uid,))
        r = cur.fetchone()
        conn.close()
        return dict(r) if r else None

    def get_all_payments(self, limit=50, status=None):
        conn = self.get_conn()
        if status:
            r = [dict(x) for x in conn.execute("SELECT * FROM payments WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()]
        else:
            r = [dict(x) for x in conn.execute("SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
        conn.close()
        return r

    def get_undelivered_payments(self):
        conn = self.get_conn()
        r = [dict(x) for x in conn.execute("SELECT * FROM payments WHERE status='success' AND delivery_status='not_delivered'").fetchall()]
        conn.close()
        return r

    def update_user_spent(self, uid, amount):
        conn = self.get_conn()
        conn.execute("UPDATE users SET total_spent=total_spent+? WHERE user_id=?", (amount, uid))
        conn.commit()
        conn.close()

    def add_promo(self, code, discount_percent, max_uses=-1, created_by=None):
        conn = self.get_conn()
        try:
            conn.execute("INSERT INTO promo_codes(code,discount_percent,max_uses,created_by)VALUES(?,?,?,?)",
                         (code.upper(), discount_percent, max_uses, created_by))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    def get_promo(self, code):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code.upper(),))
        r = cur.fetchone()
        conn.close()
        return dict(r) if r else None

    def use_promo(self, code):
        conn = self.get_conn()
        conn.execute("UPDATE promo_codes SET current_uses=current_uses+1 WHERE code=?", (code.upper(),))
        conn.commit()
        conn.close()

    def validate_promo(self, code, amount=0):
        p = self.get_promo(code)
        if not p:
            return False, "Промокод не найден", 0
        if p["max_uses"] != -1 and p["current_uses"] >= p["max_uses"]:
            return False, "Промокод исчерпан", 0
        if p.get("expires_at") and datetime.fromisoformat(p["expires_at"]) < datetime.now():
            return False, "Промокод истёк", 0
        return True, "OK", p["discount_percent"]

    def get_all_promos(self):
        conn = self.get_conn()
        r = [dict(x) for x in conn.execute("SELECT * FROM promo_codes ORDER BY created_at DESC").fetchall()]
        conn.close()
        return r

    def get_stats(self):
        conn = self.get_conn()
        cur = conn.cursor()
        s = {}
        cur.execute("SELECT COUNT(*)FROM users"); s["total_users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM payments"); s["total_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM payments WHERE status='success'"); s["success_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM payments WHERE status='pending'"); s["pending_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0)FROM payments WHERE status='success'"); s["total_revenue"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM payments WHERE status='success' AND date(paid_at)=date('now')"); s["today_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0)FROM payments WHERE status='success' AND date(paid_at)=date('now')"); s["today_revenue"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM users WHERE date(created_at)=date('now')"); s["today_users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*)FROM payments WHERE status='success' AND delivery_status='not_delivered'"); s["undelivered"] = cur.fetchone()[0]
        conn.close()
        return s

    def admin_log(self, aid, action, details=""):
        conn = self.get_conn()
        conn.execute("INSERT INTO admin_log(admin_id,action,details)VALUES(?,?,?)", (aid, action, details))
        conn.commit()
        conn.close()

    def get_referral_count(self, uid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*)FROM referrals WHERE referrer_id=?", (uid,))
        c = cur.fetchone()[0]
        conn.close()
        return c


db = Database()


# ==================== YOOMONEY ====================
class YooPay:
    @staticmethod
    def make_url(amount, label, comment=""):
        p = {"receiver": YOOMONEY_WALLET, "quickpay-form": "button",
             "paymentType": "AC", "sum": str(amount), "label": label,
             "comment": comment or "Оплата", "successURL": WEBAPP_URL,
             "targets": comment or "Оплата"}
        return f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(p)}"

    @staticmethod
    async def check_label(label, expected):
        if not YOOMONEY_ACCESS_TOKEN:
            return False, "No token"
        url = "https://yoomoney.ru/api/operation-history"
        h = {"Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
             "Content-Type": "application/x-www-form-urlencoded"}
        d = {"type": "deposition", "label": label, "records": 10}
        async with aiohttp_client.ClientSession() as s:
            try:
                async with s.post(url, headers=h, data=d, timeout=15) as r:
                    if r.status != 200:
                        return False, f"HTTP {r.status}"
                    res = await r.json()
                    for op in res.get("operations", []):
                        if op.get("label") == label and op.get("status") == "success":
                            if float(op.get("amount", 0)) >= expected:
                                return True, "OK"
                    return False, "Не найден"
            except Exception as e:
                return False, str(e)

    @staticmethod
    async def get_balance():
        if not YOOMONEY_ACCESS_TOKEN:
            return None
        async with aiohttp_client.ClientSession() as s:
            try:
                async with s.post("https://yoomoney.ru/api/account-info",
                                  headers={"Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}"},
                                  timeout=10) as r:
                    if r.status == 200:
                        return (await r.json()).get("balance")
            except:
                pass
        return None


# ==================== HELPERS ====================
def get_product_info(cat_key, prod_key):
    c = CATEGORIES.get(cat_key)
    return c["products"].get(prod_key) if c else None

def is_admin(uid):
    return uid in ADMIN_IDS

def format_price(p):
    return f"{p:,}".replace(",", " ") + " ₽"

def extract_user_id(init_data_str):
    if not init_data_str:
        return None
    try:
        parsed = dict(x.split('=', 1) for x in init_data_str.split('&') if '=' in x)
        user_data = json.loads(unquote(parsed.get('user', '{}')))
        return user_data.get('id')
    except:
        return None


# ==================== WEB API ====================
routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.Response(text=MINI_APP_HTML, content_type='text/html', charset='utf-8')

@routes.get('/health')
async def health(request):
    return web.json_response({"status": "ok", "time": datetime.now().isoformat()})

@routes.get('/api/products')
async def api_products(request):
    return web.json_response({"categories": CATEGORIES})

@routes.get('/api/orders')
async def api_orders(request):
    uid = extract_user_id(request.query.get('initData', ''))
    if not uid:
        return web.json_response({"orders": []})
    pays = db.get_user_payments(uid, 20)
    orders = []
    for p in pays:
        prod = get_product_info(p["category"], p["product_key"])
        orders.append({
            "id": p["id"],
            "product_name": prod["name"] if prod else p["product_key"],
            "amount": p["amount"],
            "status": p["status"],
            "delivery_status": p["delivery_status"],
            "created_at": (p["created_at"] or "")[:16]
        })
    return web.json_response({"orders": orders})

@routes.post('/api/promo/check')
async def api_promo(request):
    d = await request.json()
    code = d.get("code", "").strip().upper()
    if not code:
        return web.json_response({"valid": False, "message": "Введите промокод"})
    v, m, disc = db.validate_promo(code, d.get("amount", 0))
    return web.json_response({"valid": v, "message": m, "discount": disc})

@routes.post('/api/payment/create')
async def api_create(request):
    d = await request.json()
    uid = extract_user_id(d.get("initData", ""))
    if not uid:
        return web.json_response({"success": False, "message": "Авторизация не удалась. Откройте через бота."})
    cat = d.get("category")
    pk = d.get("product")
    prod = get_product_info(cat, pk)
    if not prod:
        return web.json_response({"success": False, "message": "Товар не найден"})
    active = db.get_user_active_payment(uid)
    if active:
        return web.json_response({"success": False, "message": "У вас есть незавершённый платёж. Отмените его."})
    price = prod["price"]
    orig = price
    pc = d.get("promo_code")
    disc = d.get("discount", 0)
    if pc and disc > 0:
        v, _, rd = db.validate_promo(pc, price)
        if v:
            disc = rd
            price = max(1, round(price * (100 - disc) / 100))
        else:
            disc = 0
            pc = None
    pid = str(uuid.uuid4())
    label = f"p_{uid}_{int(time.time())}_{pid[:8]}"
    comment = f"Покупка: {prod['name']}"
    purl = YooPay.make_url(price, label, comment)
    rid = db.add_payment(uid, pk, cat, pid, label, price, orig, pc, disc)
    if pc:
        db.use_promo(pc)
    db.get_or_create_user(uid)
    logger.info(f"Payment #{rid}: user={uid} product={pk} amount={price}")

    global bot_app
    if bot_app:
        for aid in ADMIN_IDS:
            try:
                await bot_app.bot.send_message(aid,
                    f"🆕 <b>Платёж #{rid}</b>\n👤 {uid}\n📦 {prod['name']}\n💰 {format_price(price)}\n🏷 <code>{label}</code>",
                    parse_mode=ParseMode.HTML)
            except:
                pass

    return web.json_response({"success": True, "payment_id": pid, "label": label,
                              "amount": price, "payment_url": purl, "order_id": rid})

@routes.post('/api/payment/check')
async def api_check(request):
    d = await request.json()
    pid = d.get("payment_id")
    if not pid:
        return web.json_response({"paid": False})
    p = db.get_payment(pid)
    if not p:
        return web.json_response({"paid": False, "message": "Не найден"})
    if p["status"] == "success":
        return web.json_response({"paid": True})
    if p["status"] in ("cancelled", "expired"):
        return web.json_response({"paid": False, "message": "Отменён/истёк"})
    ok, msg = await YooPay.check_label(p["payment_label"], p["amount"])
    if ok:
        db.update_payment_status(pid, "success")
        db.update_user_spent(p["user_id"], p["amount"])
        logger.info(f"Payment {pid} confirmed!")
        global bot_app
        if bot_app:
            prod = get_product_info(p["category"], p["product_key"])
            for aid in ADMIN_IDS:
                try:
                    await bot_app.bot.send_message(aid,
                        f"💰 <b>Оплата!</b> #{p['id']}\n👤 {p['user_id']}\n📦 {prod['name'] if prod else p['product_key']}\n💰 {format_price(p['amount'])}\n📦 Выдайте товар!",
                        parse_mode=ParseMode.HTML)
                except:
                    pass
            try:
                await bot_app.bot.send_message(p["user_id"],
                    f"✅ <b>Оплата подтверждена!</b>\n📦 {prod['name'] if prod else p['product_key']}\n💰 {format_price(p['amount'])}\n⏳ Товар будет выдан!",
                    parse_mode=ParseMode.HTML)
            except:
                pass
        return web.json_response({"paid": True})
    return web.json_response({"paid": False, "message": msg})

@routes.post('/api/payment/cancel')
async def api_cancel(request):
    d = await request.json()
    pid = d.get("payment_id")
    if pid:
        p = db.get_payment(pid)
        if p and p["status"] == "pending":
            db.update_payment_status(pid, "cancelled")
    return web.json_response({"ok": True})


# ==================== BOT HANDLERS ====================
def get_main_kb(uid=None):
    kb = [
        [InlineKeyboardButton("🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📜 Покупки", callback_data="my_orders"),
         InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("👥 Рефералка", callback_data="referral"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="help_info")],
    ]
    if uid and is_admin(uid):
        kb.append([InlineKeyboardButton("👑 Админ", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def get_admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton("📋 Платежи", callback_data="adm_payments")],
        [InlineKeyboardButton("📦 Невыданные", callback_data="adm_undelivered")],
        [InlineKeyboardButton("✅ Подтвердить", callback_data="adm_confirm")],
        [InlineKeyboardButton("📦 Выдать", callback_data="adm_deliver")],
        [InlineKeyboardButton("🎟 Промокоды", callback_data="adm_promos")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton("💰 Баланс", callback_data="adm_balance")],
        [InlineKeyboardButton("🔙 Меню", callback_data="back_main")],
    ])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref = None
    if context.args and context.args[0].startswith("ref"):
        try:
            ref = int(context.args[0][3:])
            if ref == u.id: ref = None
        except: pass
    db.get_or_create_user(u.id, u.username, u.first_name, u.last_name, u.language_code, ref)
    t = (f"👋 Привет, <b>{html.escape(u.first_name)}</b>!\n\n"
         f"💎 <b>Telegram Premium Shop</b>\n\n"
         f"⭐ Premium · 🌟 Stars · 🎨 NFT\n"
         f"💳 Оплата через ЮMoney\n\n"
         f"Нажмите <b>«Открыть магазин»</b>:")
    if ref: t += "\n\n🎁 Вы по реферальной ссылке!"
    await update.message.reply_text(t, reply_markup=get_main_kb(u.id), parse_mode=ParseMode.HTML)
    return MAIN_MENU

async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = update.effective_user.id

    if d == "back_main":
        await q.edit_message_text("🏠 <b>Меню</b>", reply_markup=get_main_kb(uid), parse_mode=ParseMode.HTML)
        return MAIN_MENU
    elif d == "my_orders":
        pays = db.get_user_payments(uid, 10)
        if not pays:
            t = "📭 Покупок нет."
        else:
            t = "📜 <b>Покупки:</b>\n\n"
            for p in pays:
                st = {"success":"✅","pending":"⏳","expired":"❌","cancelled":"🚫"}.get(p["status"],"❓")
                pr = get_product_info(p["category"], p["product_key"])
                t += f"{st} #{p['id']} {pr['name'] if pr else p['product_key']} — {format_price(p['amount'])}\n"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="back_main")]]), parse_mode=ParseMode.HTML)
    elif d == "profile":
        u = db.get_user(uid)
        refs = db.get_referral_count(uid)
        ps = db.get_user_payments(uid, 1000)
        ok = sum(1 for p in ps if p["status"] == "success")
        t = (f"👤 <b>Профиль</b>\n\n🆔 <code>{uid}</code>\n"
             f"🛍 Покупок: {ok}\n💰 Потрачено: {format_price(u.get('total_spent',0) if u else 0)}\n"
             f"👥 Рефералов: {refs}")
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="back_main")]]), parse_mode=ParseMode.HTML)
    elif d == "referral":
        bi = await context.bot.get_me()
        lnk = f"https://t.me/{bi.username}?start=ref{uid}"
        t = f"👥 <b>Реферальная программа</b>\n\n🔗 <code>{lnk}</code>\n\n👥 Приглашено: {db.get_referral_count(uid)}"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="back_main")]]), parse_mode=ParseMode.HTML)
    elif d == "help_info":
        t = "ℹ️ <b>Помощь</b>\n\n/start — меню\n/check — проверить платёж\n/history — покупки\n\nОткройте магазин кнопкой!"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="back_main")]]), parse_mode=ParseMode.HTML)
    elif d == "admin_panel":
        if not is_admin(uid): return
        await q.edit_message_text("👑 <b>Админ</b>", reply_markup=get_admin_kb(), parse_mode=ParseMode.HTML)
        return ADMIN_MENU
    elif d == "adm_stats":
        if not is_admin(uid): return
        s = db.get_stats()
        bal = await YooPay.get_balance()
        t = (f"📊 <b>Статистика</b>\n\n👥 {s['total_users']} (+{s['today_users']})\n"
             f"💳 {s['total_payments']} (✅{s['success_payments']} ⏳{s['pending_payments']})\n"
             f"📦 Невыдано: {s['undelivered']}\n"
             f"💰 Всего: {format_price(s['total_revenue'])}\n"
             f"💰 Сегодня: {format_price(s['today_revenue'])}\n"
             f"💼 Баланс: {f'{bal:.2f}₽' if bal else 'Н/Д'}")
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)
    elif d == "adm_payments":
        if not is_admin(uid): return
        ps = db.get_all_payments(15)
        t = "📋 <b>Платежи:</b>\n\n" if ps else "📭 Нет"
        for p in ps:
            st = {"success":"✅","pending":"⏳","expired":"❌","cancelled":"🚫"}.get(p["status"],"❓")
            t += f"{st}#{p['id']}|{p['user_id']}|{p['product_key']}|{format_price(p['amount'])}\n"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)
    elif d == "adm_undelivered":
        if not is_admin(uid): return
        ps = db.get_undelivered_payments()
        t = "✅ Всё выдано!" if not ps else "📦 <b>Невыданные:</b>\n\n"
        for p in ps:
            pr = get_product_info(p["category"], p["product_key"])
            t += f"#{p['id']}|{p['user_id']}|{pr['name'] if pr else p['product_key']}|{format_price(p['amount'])}\n"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)
    elif d == "adm_confirm":
        if not is_admin(uid): return
        context.user_data["aw"] = "confirm"
        await q.edit_message_text("Введите ID платежа (#):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]))
        return ADMIN_MANUAL_ID
    elif d == "adm_deliver":
        if not is_admin(uid): return
        context.user_data["aw"] = "deliver"
        await q.edit_message_text("Введите ID платежа (#) для выдачи:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]))
        return ADMIN_MANUAL_ID
    elif d == "adm_promos":
        if not is_admin(uid): return
        ps = db.get_all_promos()
        t = "🎟 <b>Промокоды:</b>\n\n"
        for p in ps:
            a = "✅" if p["is_active"] else "❌"
            u = f"{p['current_uses']}/{p['max_uses']}" if p["max_uses"] != -1 else f"{p['current_uses']}/∞"
            t += f"{a} <code>{p['code']}</code> {p['discount_percent']}% ({u})\n"
        if not ps: t += "Нет\n"
        t += "\nСоздать: <code>КОД СКИДКА МАКС</code>"
        context.user_data["aw"] = "promo"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]), parse_mode=ParseMode.HTML)
        return ADMIN_ADD_PROMO
    elif d == "adm_broadcast":
        if not is_admin(uid): return
        context.user_data["aw"] = "broadcast"
        await q.edit_message_text("📢 Введите текст рассылки (HTML):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]))
        return ADMIN_BROADCAST
    elif d == "adm_balance":
        if not is_admin(uid): return
        bal = await YooPay.get_balance()
        await q.edit_message_text(f"💰 {f'{bal:.2f} ₽' if bal else 'Н/Д'}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙",callback_data="admin_panel")]]))
    return MAIN_MENU

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    aw = context.user_data.get("aw")
    uid = update.effective_user.id
    bk = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ", callback_data="admin_panel")]])

    if aw == "confirm":
        try: rid = int(update.message.text.strip().replace("#",""))
        except: await update.message.reply_text("❌ Число!"); return ADMIN_MANUAL_ID
        p = db.get_payment_by_row_id(rid)
        if not p: await update.message.reply_text("❌ Не найден"); return ADMIN_MANUAL_ID
        if p["status"] == "success": await update.message.reply_text("✅ Уже"); return ADMIN_MANUAL_ID
        db.update_payment_status(p["payment_id"], "success")
        db.update_user_spent(p["user_id"], p["amount"])
        db.admin_log(uid, "confirm", f"#{rid}")
        try:
            pr = get_product_info(p["category"], p["product_key"])
            await context.bot.send_message(p["user_id"],
                f"✅ <b>Платёж #{rid} подтверждён!</b>\n📦 {pr['name'] if pr else p['product_key']}\n⏳ Товар скоро!", parse_mode=ParseMode.HTML)
        except: pass
        await update.message.reply_text(f"✅ #{rid} подтверждён", reply_markup=bk)
        context.user_data["aw"] = None; return ADMIN_MENU

    elif aw == "deliver":
        try: rid = int(update.message.text.strip().replace("#",""))
        except: await update.message.reply_text("❌ Число!"); return ADMIN_MANUAL_ID
        p = db.get_payment_by_row_id(rid)
        if not p: await update.message.reply_text("❌ Не найден"); return ADMIN_MANUAL_ID
        if p["status"] != "success": await update.message.reply_text("⚠️ Не оплачен"); return ADMIN_MANUAL_ID
        if p["delivery_status"] == "delivered": await update.message.reply_text("✅ Уже"); return ADMIN_MANUAL_ID
        db.mark_delivered(p["payment_id"], f"Admin {uid}")
        db.admin_log(uid, "deliver", f"#{rid}")
        try:
            pr = get_product_info(p["category"], p["product_key"])
            await context.bot.send_message(p["user_id"],
                f"🎉 <b>Товар выдан!</b>\n📦 {pr['name'] if pr else p['product_key']}\nСпасибо!", parse_mode=ParseMode.HTML)
        except: pass
        await update.message.reply_text(f"✅ #{rid} выдан", reply_markup=bk)
        context.user_data["aw"] = None; return ADMIN_MENU

    elif aw == "promo":
        parts = update.message.text.strip().split()
        if len(parts) < 2: await update.message.reply_text("Формат: КОД СКИДКА [МАКС]"); return ADMIN_ADD_PROMO
        code = parts[0].upper()
        try: disc = int(parts[1].replace("%",""))
        except: await update.message.reply_text("Скидка=число"); return ADMIN_ADD_PROMO
        mx = -1
        if len(parts) >= 3:
            try: mx = int(parts[2])
            except: pass
        if disc < 1 or disc > 99: await update.message.reply_text("1-99%"); return ADMIN_ADD_PROMO
        ok = db.add_promo(code, disc, mx, uid)
        if ok:
            db.admin_log(uid, "promo", f"{code} {disc}%")
            await update.message.reply_text(f"✅ <code>{code}</code> {disc}%", parse_mode=ParseMode.HTML, reply_markup=bk)
        else:
            await update.message.reply_text("❌ Существует")
        context.user_data["aw"] = None; return ADMIN_MENU

    elif aw == "broadcast":
        txt = update.message.text.strip()
        users = db.get_all_users()
        sent = fail = 0
        for u in users:
            try:
                await context.bot.send_message(u["user_id"], f"📢\n\n{txt}", parse_mode=ParseMode.HTML)
                sent += 1; await asyncio.sleep(0.05)
            except: fail += 1
        db.admin_log(uid, "broadcast", f"s:{sent} f:{fail}")
        await update.message.reply_text(f"📢 ✅{sent} ❌{fail}", reply_markup=bk)
        context.user_data["aw"] = None; return ADMIN_MENU

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    a = db.get_user_active_payment(uid)
    if not a: await update.message.reply_text("✅ Нет активных платежей."); return
    ok, msg = await YooPay.check_label(a["payment_label"], a["amount"])
    if ok:
        db.update_payment_status(a["payment_id"], "success")
        db.update_user_spent(uid, a["amount"])
        pr = get_product_info(a["category"], a["product_key"])
        await update.message.reply_text(f"✅ <b>Оплачено!</b>\n📦 {pr['name'] if pr else a['product_key']}\n⏳ Товар скоро!", parse_mode=ParseMode.HTML)
        for aid in ADMIN_IDS:
            try: await context.bot.send_message(aid, f"💰 #{a['id']} оплачен! {uid} {format_price(a['amount'])}", parse_mode=ParseMode.HTML)
            except: pass
    else:
        await update.message.reply_text(f"⏳ Не найден. {msg}")

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ps = db.get_user_payments(update.effective_user.id, 10)
    if not ps: await update.message.reply_text("📭 Нет покупок."); return
    t = "📜 <b>Покупки:</b>\n\n"
    for p in ps:
        st = {"success":"✅","pending":"⏳","expired":"❌","cancelled":"🚫"}.get(p["status"],"❓")
        pr = get_product_info(p["category"], p["product_key"])
        t += f"{st} #{p['id']} {pr['name'] if pr else p['product_key']} — {format_price(p['amount'])}\n"
    await update.message.reply_text(t, parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ /start — меню\n/check — проверить\n/history — покупки\n\nОткройте магазин кнопкой!")


# ==================== BACKGROUND ====================
async def bg_checker(app):
    logger.info("Background checker started")
    while True:
        try:
            db.expire_payments()
            for p in db.get_pending_payments():
                try:
                    ok, _ = await YooPay.check_label(p["payment_label"], p["amount"])
                    if ok:
                        db.update_payment_status(p["payment_id"], "success")
                        db.update_user_spent(p["user_id"], p["amount"])
                        logger.info(f"Auto-confirmed #{p['id']}")
                        pr = get_product_info(p["category"], p["product_key"])
                        try:
                            await app.bot.send_message(p["user_id"],
                                f"✅ <b>Платёж #{p['id']} подтверждён!</b>\n📦 {pr['name'] if pr else p['product_key']}\n⏳ Товар будет выдан!", parse_mode=ParseMode.HTML)
                        except: pass
                        for aid in ADMIN_IDS:
                            try:
                                await app.bot.send_message(aid,
                                    f"💰 Авто #{p['id']}|{p['user_id']}|{format_price(p['amount'])}\n📦 Выдайте!", parse_mode=ParseMode.HTML)
                            except: pass
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Check err {p['id']}: {e}")
        except Exception as e:
            logger.exception(f"BG err: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ==================== STARTUP ====================
bot_app = None

async def on_startup(webapp):
    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(btn_handler, pattern="^(back_main|my_orders|profile|referral|help_info|admin_panel|adm_stats|adm_payments|adm_undelivered|adm_confirm|adm_deliver|adm_promos|adm_broadcast|adm_balance)$")],
            ADMIN_MENU: [CallbackQueryHandler(btn_handler, pattern="^(back_main|admin_panel|adm_stats|adm_payments|adm_undelivered|adm_confirm|adm_deliver|adm_promos|adm_broadcast|adm_balance)$")],
            ADMIN_MANUAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text), CallbackQueryHandler(btn_handler, pattern="^admin_panel$")],
            ADMIN_ADD_PROMO: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text), CallbackQueryHandler(btn_handler, pattern="^admin_panel$")],
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text), CallbackQueryHandler(btn_handler, pattern="^admin_panel$")],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        per_user=True, per_chat=True,
    )

    bot_app.add_handler(conv)
    bot_app.add_handler(CommandHandler("check", cmd_check))
    bot_app.add_handler(CommandHandler("history", cmd_history))
    bot_app.add_handler(CommandHandler("help", cmd_help))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_my_commands([
        BotCommand("start", "Главное меню"),
        BotCommand("check", "Проверить оплату"),
        BotCommand("history", "Мои покупки"),
        BotCommand("help", "Помощь"),
    ])
    await bot_app.updater.start_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])
    asyncio.create_task(bg_checker(bot_app))

    logger.info("🚀 Bot + WebApp started!")
    for aid in ADMIN_IDS:
        try: await bot_app.bot.send_message(aid, "🟢 Бот + Mini App запущены!")
        except: pass

async def on_shutdown(webapp):
    global bot_app
    if bot_app:
        try: await bot_app.updater.stop()
        except: pass
        try: await bot_app.stop()
        except: pass
        try: await bot_app.shutdown()
        except: pass
    logger.info("Stopped")


# ==================== MAIN ====================
def create_app():
    """Создать aiohttp приложение (для разных способов запуска)"""
    db.init_db()
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_routes(routes)
    return app

# Для запуска напрямую
if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

# Для WSGI/import запуска (bothost.tech может использовать это)
app = create_app()
