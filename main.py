#!/usr/bin/env python3
"""
Telegram Premium Shop Bot + Mini App
ИСПРАВЛЕННАЯ ВЕРСИЯ
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
from urllib.parse import urlencode, parse_qs, unquote

from aiohttp import web
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8633048902:AAEBTjJtA-SBUSZI8WrKhcFajMA49XpOEVk")
ADMIN_IDS = [8681521200]

YOOMONEY_WALLET = "4100118889570559"
YOOMONEY_ACCESS_TOKEN = os.getenv("YOOMONEY_TOKEN", "4100118889570559.3288B2E716CEEB922A26BD6BEAC58648FBFB680CCF64E4E1447D714D6FB5EA5F01F1478FAC686BEF394C8A186C98982DE563C1ABCDF9F2F61D971B61DA3C7E486CA818F98B9E0069F1C0891E090DD56A11319D626A40F0AE8302A8339DED9EB7969617F191D93275F64C4127A3ECB7AED33FCDE91CA68690EB7534C67E6C219E")

# ВАЖНО: Укажите правильный URL вашего Mini App
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))
WEBAPP_DOMAIN = os.getenv("WEBAPP_DOMAIN", "telegram-premium.bothost.tech")
WEBAPP_URL = f"https://{WEBAPP_DOMAIN}"

# Товары
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
                "features": ["Без рекламы", "Файлы до 4 ГБ", "Уникальные стикеры", "Быстрая загрузка"],
                "badge": ""
            },
            "premium_3m": {
                "name": "Premium 3 месяца",
                "price": 639,
                "description": "Telegram Premium на 3 месяца",
                "features": ["Все преимущества Premium", "Скидка 10%"],
                "badge": "Выгодно"
            },
            "premium_6m": {
                "name": "Premium 6 месяцев",
                "price": 1199,
                "description": "Telegram Premium на 6 месяцев",
                "features": ["Все преимущества Premium", "Скидка 15%"],
                "badge": "Популярный"
            },
            "premium_12m": {
                "name": "Premium 12 месяцев",
                "price": 2159,
                "description": "Telegram Premium на 12 месяцев",
                "features": ["Все преимущества Premium", "Максимальная скидка"],
                "badge": "Лучшая цена"
            }
        }
    },
    "stars": {
        "name": "Telegram Stars",
        "emoji": "🌟",
        "icon": "stars",
        "products": {
            "stars_50": {"name": "50 Stars", "price": 60, "description": "50 Telegram Stars", "features": ["Поддержка авторов", "Покупки в ботах"], "badge": ""},
            "stars_100": {"name": "100 Stars", "price": 112, "description": "100 Telegram Stars", "features": ["Поддержка авторов", "Выгоднее"], "badge": ""},
            "stars_250": {"name": "250 Stars", "price": 264, "description": "250 Telegram Stars", "features": ["Отличная скидка"], "badge": "Выгодно"},
            "stars_500": {"name": "500 Stars", "price": 496, "description": "500 Telegram Stars", "features": ["Максимум звёзд"], "badge": "Хит"}
        }
    },
    "nft": {
        "name": "NFT Коллекция",
        "emoji": "🎨",
        "icon": "nft",
        "products": {
            "nft_basic": {"name": "NFT Basic", "price": 159, "description": "Базовый NFT", "features": ["Уникальный дизайн"], "badge": ""},
            "nft_rare": {"name": "NFT Rare", "price": 399, "description": "Редкий NFT", "features": ["Лимитированная серия"], "badge": "Редкий"},
            "nft_legendary": {"name": "NFT Legendary", "price": 799, "description": "Легендарный NFT", "features": ["Всего 100 штук"], "badge": "Легенда"}
        }
    }
}

CHECK_INTERVAL = 30
PAYMENT_TIMEOUT_HOURS = 24
DB_NAME = "shop.db"

MAIN_MENU, ADMIN_MENU, ADMIN_INPUT = range(3)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("Shop")


# ==================== MINI APP HTML ====================
def get_webapp_html():
    """Генерация HTML для Mini App"""
    categories_json = json.dumps(CATEGORIES, ensure_ascii=False)
    
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Premium Shop</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        
        :root {{
            --bg: #1a1a1a;
            --bg2: #2a2a2a;
            --card: #333;
            --text: #fff;
            --text2: #aaa;
            --accent: #3390ec;
            --success: #4caf50;
            --error: #f44336;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding-bottom: 80px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 24px 16px;
            text-align: center;
        }}
        .header h1 {{ font-size: 22px; margin-bottom: 4px; }}
        .header p {{ font-size: 14px; opacity: 0.9; }}
        
        .tabs {{
            display: flex;
            gap: 8px;
            padding: 16px;
            overflow-x: auto;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        
        .tab {{
            flex-shrink: 0;
            padding: 10px 20px;
            background: var(--card);
            border: none;
            border-radius: 20px;
            color: var(--text2);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab.active {{
            background: var(--accent);
            color: white;
        }}
        
        .products {{
            padding: 0 16px;
        }}
        
        .product {{
            background: var(--card);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: transform 0.2s;
            position: relative;
        }}
        .product:active {{ transform: scale(0.98); }}
        
        .product-top {{
            display: flex;
            gap: 14px;
            margin-bottom: 12px;
        }}
        
        .product-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            background: linear-gradient(135deg, #FFD700, #FFA500);
        }}
        .product-icon.stars {{ background: linear-gradient(135deg, #9C27B0, #E040FB); }}
        .product-icon.nft {{ background: linear-gradient(135deg, #00BCD4, #2196F3); }}
        
        .product-info {{ flex: 1; }}
        .product-name {{ font-size: 16px; font-weight: 600; margin-bottom: 4px; }}
        .product-desc {{ font-size: 13px; color: var(--text2); }}
        
        .product-bottom {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .product-price {{ font-size: 18px; font-weight: 700; }}
        .product-price span {{ font-size: 14px; color: var(--text2); }}
        
        .buy-btn {{
            padding: 10px 24px;
            background: var(--accent);
            border: none;
            border-radius: 20px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }}
        
        .badge {{
            position: absolute;
            top: 12px;
            right: 12px;
            padding: 4px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            color: white;
            background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        }}
        
        /* Modal */
        .modal {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            display: none;
            align-items: flex-end;
        }}
        .modal.show {{ display: flex; }}
        
        .modal-content {{
            background: var(--bg2);
            border-radius: 20px 20px 0 0;
            width: 100%;
            max-height: 85vh;
            overflow-y: auto;
            padding: 20px;
            padding-bottom: 40px;
            animation: slideUp 0.3s ease;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(100%); }}
            to {{ transform: translateY(0); }}
        }}
        
        .modal-header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .modal-icon {{
            width: 72px;
            height: 72px;
            border-radius: 18px;
            margin: 0 auto 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            background: linear-gradient(135deg, #FFD700, #FFA500);
        }}
        .modal-title {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; }}
        .modal-price {{ font-size: 28px; font-weight: 800; color: var(--accent); }}
        
        .features {{
            margin-bottom: 20px;
        }}
        .feature {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #444;
        }}
        .feature:last-child {{ border-bottom: none; }}
        .feature-icon {{
            width: 32px;
            height: 32px;
            background: rgba(76, 175, 80, 0.2);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--success);
        }}
        
        .promo-section {{
            margin-bottom: 20px;
        }}
        .promo-row {{
            display: flex;
            gap: 8px;
        }}
        .promo-input {{
            flex: 1;
            padding: 14px;
            background: var(--card);
            border: 1px solid #444;
            border-radius: 12px;
            color: var(--text);
            font-size: 15px;
            outline: none;
        }}
        .promo-input:focus {{ border-color: var(--accent); }}
        .promo-btn {{
            padding: 14px 20px;
            background: var(--accent);
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 600;
            cursor: pointer;
        }}
        .promo-result {{
            margin-top: 10px;
            padding: 10px;
            border-radius: 8px;
            font-size: 13px;
            display: none;
        }}
        .promo-result.success {{
            display: block;
            background: rgba(76, 175, 80, 0.2);
            color: var(--success);
        }}
        .promo-result.error {{
            display: block;
            background: rgba(244, 67, 54, 0.2);
            color: var(--error);
        }}
        
        .modal-btn {{
            width: 100%;
            padding: 18px;
            background: var(--accent);
            border: none;
            border-radius: 14px;
            color: white;
            font-size: 17px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }}
        .modal-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        .modal-btn.secondary {{
            background: transparent;
            border: 2px solid var(--accent);
            color: var(--accent);
        }}
        .modal-btn.danger {{
            background: transparent;
            border: 2px solid var(--error);
            color: var(--error);
        }}
        
        /* Payment Screen */
        .payment-view {{
            display: none;
            text-align: center;
            padding: 30px 0;
        }}
        .payment-view.show {{ display: block; }}
        
        .loader {{
            width: 48px;
            height: 48px;
            border: 4px solid #444;
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        
        .payment-title {{ font-size: 20px; font-weight: 700; margin-bottom: 10px; }}
        .payment-desc {{ color: var(--text2); margin-bottom: 20px; line-height: 1.5; }}
        
        .pay-link {{
            display: inline-block;
            padding: 16px 40px;
            background: var(--success);
            border-radius: 14px;
            color: white;
            text-decoration: none;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 16px;
        }}
        
        /* Success Screen */
        .success-view {{
            display: none;
            text-align: center;
            padding: 40px 0;
        }}
        .success-view.show {{ display: block; }}
        
        .success-icon {{
            width: 80px;
            height: 80px;
            background: var(--success);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            margin: 0 auto 20px;
            animation: pop 0.5s ease;
        }}
        @keyframes pop {{
            0% {{ transform: scale(0); }}
            60% {{ transform: scale(1.2); }}
            100% {{ transform: scale(1); }}
        }}
        
        /* Toast */
        .toast {{
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: var(--card);
            padding: 14px 28px;
            border-radius: 12px;
            font-size: 14px;
            z-index: 2000;
            opacity: 0;
            transition: all 0.3s;
        }}
        .toast.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}
        
        /* Debug */
        .debug {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            color: #0f0;
            padding: 8px;
            font-size: 10px;
            font-family: monospace;
            max-width: 90%;
            max-height: 100px;
            overflow: auto;
            z-index: 9999;
            display: none;
        }}
    </style>
</head>
<body>
    <div class="debug" id="debug"></div>
    <div class="toast" id="toast"></div>

    <div id="mainView">
        <div class="header">
            <h1>💎 Premium Shop</h1>
            <p>Telegram Premium, Stars, NFT</p>
        </div>

        <div class="tabs" id="tabs"></div>
        <div class="products" id="products"></div>
    </div>

    <div class="modal" id="modal" onclick="if(event.target===this)closeModal()">
        <div class="modal-content">
            <div id="productView">
                <div class="modal-header">
                    <div class="modal-icon" id="mIcon">⭐</div>
                    <div class="modal-title" id="mTitle">Товар</div>
                    <div class="modal-price" id="mPrice">0 ₽</div>
                </div>
                <div class="features" id="mFeatures"></div>
                <div class="promo-section">
                    <div class="promo-row">
                        <input type="text" class="promo-input" id="promoInput" placeholder="Промокод">
                        <button class="promo-btn" onclick="applyPromo()">OK</button>
                    </div>
                    <div class="promo-result" id="promoResult"></div>
                </div>
                <button class="modal-btn" id="buyBtn" onclick="createPayment()">
                    Купить за <span id="buyPrice">0</span> ₽
                </button>
            </div>

            <div class="payment-view" id="paymentView">
                <div class="loader"></div>
                <div class="payment-title">Ожидание оплаты</div>
                <div class="payment-desc" id="paymentDesc"></div>
                <a class="pay-link" id="payLink" href="#" target="_blank">💳 Оплатить</a>
                <button class="modal-btn secondary" onclick="checkPayment()">✅ Проверить оплату</button>
                <button class="modal-btn danger" onclick="cancelPayment()">❌ Отменить</button>
            </div>

            <div class="success-view" id="successView">
                <div class="success-icon">✓</div>
                <div class="payment-title" style="color:var(--success)">Оплата успешна!</div>
                <div class="payment-desc">Товар будет выдан в ближайшее время</div>
                <button class="modal-btn" onclick="closeModal()">Отлично!</button>
            </div>
        </div>
    </div>

    <script>
        // ===== INIT =====
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();

        const CATEGORIES = {categories_json};
        
        let currentCat = 'all';
        let selectedProduct = null;
        let selectedCatKey = '';
        let selectedProdKey = '';
        let currentPaymentId = null;
        let appliedDiscount = 0;
        let appliedPromo = '';
        let checkTimer = null;

        function debug(msg) {{
            console.log(msg);
            const d = document.getElementById('debug');
            d.textContent = msg;
            // d.style.display = 'block'; // Раскомментируйте для отладки
        }}

        function getUserId() {{
            try {{
                if (tg.initDataUnsafe && tg.initDataUnsafe.user) {{
                    return tg.initDataUnsafe.user.id;
                }}
            }} catch(e) {{}}
            return null;
        }}

        // ===== RENDER =====
        function init() {{
            debug('Init started, userId: ' + getUserId());
            renderTabs();
            renderProducts('all');
        }}

        function renderTabs() {{
            const c = document.getElementById('tabs');
            let h = '<button class="tab active" onclick="filterCat(\\'all\\', this)">Все</button>';
            for (const [k, v] of Object.entries(CATEGORIES)) {{
                h += '<button class="tab" onclick="filterCat(\\'' + k + '\\', this)">' + v.emoji + ' ' + v.name + '</button>';
            }}
            c.innerHTML = h;
        }}

        function renderProducts(cat) {{
            const c = document.getElementById('products');
            let h = '';
            for (const [catKey, catData] of Object.entries(CATEGORIES)) {{
                if (cat !== 'all' && cat !== catKey) continue;
                for (const [prodKey, prod] of Object.entries(catData.products)) {{
                    const badge = prod.badge ? '<div class="badge">' + prod.badge + '</div>' : '';
                    h += `
                        <div class="product" onclick="openProduct('${{catKey}}', '${{prodKey}}')">
                            ${{badge}}
                            <div class="product-top">
                                <div class="product-icon ${{catData.icon}}">${{catData.emoji}}</div>
                                <div class="product-info">
                                    <div class="product-name">${{prod.name}}</div>
                                    <div class="product-desc">${{prod.description}}</div>
                                </div>
                            </div>
                            <div class="product-bottom">
                                <div class="product-price">${{prod.price}} <span>₽</span></div>
                                <button class="buy-btn" onclick="event.stopPropagation(); openProduct('${{catKey}}', '${{prodKey}}')">Купить</button>
                            </div>
                        </div>
                    `;
                }}
            }}
            c.innerHTML = h;
        }}

        function filterCat(cat, btn) {{
            currentCat = cat;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            renderProducts(cat);
            if (tg.HapticFeedback) tg.HapticFeedback.selectionChanged();
        }}

        // ===== MODAL =====
        function openProduct(catKey, prodKey) {{
            const cat = CATEGORIES[catKey];
            const prod = cat.products[prodKey];
            if (!prod) return;

            selectedCatKey = catKey;
            selectedProdKey = prodKey;
            selectedProduct = prod;
            appliedDiscount = 0;
            appliedPromo = '';

            document.getElementById('mIcon').textContent = cat.emoji;
            document.getElementById('mIcon').className = 'modal-icon ' + cat.icon;
            document.getElementById('mTitle').textContent = prod.name;
            document.getElementById('mPrice').textContent = prod.price + ' ₽';
            document.getElementById('buyPrice').textContent = prod.price;

            let fh = '';
            (prod.features || []).forEach(f => {{
                fh += '<div class="feature"><div class="feature-icon">✓</div><div>' + f + '</div></div>';
            }});
            document.getElementById('mFeatures').innerHTML = fh;

            document.getElementById('promoInput').value = '';
            document.getElementById('promoResult').className = 'promo-result';
            document.getElementById('buyBtn').disabled = false;

            showView('product');
            document.getElementById('modal').classList.add('show');
            if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('medium');
        }}

        function closeModal() {{
            document.getElementById('modal').classList.remove('show');
            if (checkTimer) {{ clearInterval(checkTimer); checkTimer = null; }}
            currentPaymentId = null;
        }}

        function showView(view) {{
            document.getElementById('productView').style.display = view === 'product' ? 'block' : 'none';
            document.getElementById('paymentView').className = view === 'payment' ? 'payment-view show' : 'payment-view';
            document.getElementById('successView').className = view === 'success' ? 'success-view show' : 'success-view';
        }}

        // ===== PROMO =====
        async function applyPromo() {{
            const code = document.getElementById('promoInput').value.trim().toUpperCase();
            if (!code) return;

            const res = document.getElementById('promoResult');
            try {{
                const r = await fetch('/api/promo/check', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ code: code, amount: selectedProduct.price }})
                }});
                const data = await r.json();
                debug('Promo response: ' + JSON.stringify(data));

                if (data.valid) {{
                    appliedDiscount = data.discount;
                    appliedPromo = code;
                    const newPrice = Math.max(1, Math.round(selectedProduct.price * (100 - data.discount) / 100));
                    res.className = 'promo-result success';
                    res.textContent = '✓ Скидка ' + data.discount + '%! Цена: ' + newPrice + ' ₽';
                    document.getElementById('mPrice').innerHTML = '<s style="opacity:0.5">' + selectedProduct.price + ' ₽</s> ' + newPrice + ' ₽';
                    document.getElementById('buyPrice').textContent = newPrice;
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                }} else {{
                    res.className = 'promo-result error';
                    res.textContent = data.message || 'Неверный промокод';
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
                }}
            }} catch(e) {{
                debug('Promo error: ' + e);
                res.className = 'promo-result error';
                res.textContent = 'Ошибка проверки';
            }}
        }}

        // ===== PAYMENT =====
        async function createPayment() {{
            if (!selectedProduct) return;
            
            const userId = getUserId();
            debug('Creating payment, userId: ' + userId);
            
            const btn = document.getElementById('buyBtn');
            btn.disabled = true;
            btn.textContent = 'Создание...';

            let price = selectedProduct.price;
            if (appliedDiscount > 0) {{
                price = Math.max(1, Math.round(price * (100 - appliedDiscount) / 100));
            }}

            try {{
                const body = {{
                    category: selectedCatKey,
                    product: selectedProdKey,
                    promo_code: appliedPromo || null,
                    discount: appliedDiscount,
                    user_id: userId,
                    init_data: tg.initData || ''
                }};
                debug('Payment request: ' + JSON.stringify(body));

                const r = await fetch('/api/payment/create', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(body)
                }});
                const data = await r.json();
                debug('Payment response: ' + JSON.stringify(data));

                if (data.success) {{
                    currentPaymentId = data.payment_id;
                    document.getElementById('paymentDesc').innerHTML = 
                        '📦 ' + selectedProduct.name + '<br>💰 ' + data.amount + ' ₽<br><br>Оплатите и нажмите "Проверить"';
                    document.getElementById('payLink').href = data.payment_url;
                    showView('payment');
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                    
                    // Автопроверка
                    checkTimer = setInterval(autoCheck, 15000);
                }} else {{
                    toast(data.message || 'Ошибка');
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
                }}
            }} catch(e) {{
                debug('Payment error: ' + e);
                toast('Ошибка сети');
            }}

            btn.disabled = false;
            btn.innerHTML = 'Купить за <span id="buyPrice">' + price + '</span> ₽';
        }}

        async function checkPayment() {{
            if (!currentPaymentId) return;
            toast('Проверяю...');

            try {{
                const r = await fetch('/api/payment/check', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ payment_id: currentPaymentId }})
                }});
                const data = await r.json();
                debug('Check response: ' + JSON.stringify(data));

                if (data.paid) {{
                    if (checkTimer) {{ clearInterval(checkTimer); checkTimer = null; }}
                    showView('success');
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                }} else {{
                    toast('⏳ Оплата не найдена');
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('warning');
                }}
            }} catch(e) {{
                debug('Check error: ' + e);
                toast('Ошибка проверки');
            }}
        }}

        async function autoCheck() {{
            if (!currentPaymentId) return;
            try {{
                const r = await fetch('/api/payment/check', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ payment_id: currentPaymentId }})
                }});
                const data = await r.json();
                if (data.paid) {{
                    if (checkTimer) {{ clearInterval(checkTimer); checkTimer = null; }}
                    showView('success');
                    if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                }}
            }} catch(e) {{}}
        }}

        async function cancelPayment() {{
            if (currentPaymentId) {{
                try {{
                    await fetch('/api/payment/cancel', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ payment_id: currentPaymentId }})
                    }});
                }} catch(e) {{}}
            }}
            if (checkTimer) {{ clearInterval(checkTimer); checkTimer = null; }}
            closeModal();
            toast('Отменено');
        }}

        function toast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2500);
        }}

        // Start
        init();
    </script>
</body>
</html>'''


# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.db_name = DB_NAME

    def get_conn(self):
        conn = sqlite3.connect(self.db_name, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_conn()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                total_spent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_key TEXT,
                category TEXT,
                payment_id TEXT UNIQUE,
                payment_label TEXT,
                amount INTEGER,
                original_amount INTEGER,
                promo_code TEXT,
                discount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'not_delivered',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount_percent INTEGER,
                max_uses INTEGER DEFAULT -1,
                current_uses INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
            CREATE INDEX IF NOT EXISTS idx_payments_label ON payments(payment_label);
        ''')
        conn.commit()
        conn.close()
        logger.info("DB initialized")

    def get_or_create_user(self, user_id, username=None, first_name=None):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id, username, first_name) VALUES (?,?,?)",
                        (user_id, username, first_name))
            conn.commit()
        conn.close()

    def add_payment(self, user_id, product_key, category, payment_id, payment_label,
                    amount, original_amount=None, promo_code=None, discount=0):
        conn = self.get_conn()
        cur = conn.cursor()
        expires = (datetime.now() + timedelta(hours=PAYMENT_TIMEOUT_HOURS)).isoformat()
        cur.execute(
            """INSERT INTO payments (user_id, product_key, category, payment_id, payment_label,
               amount, original_amount, promo_code, discount, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, product_key, category, payment_id, payment_label,
             amount, original_amount or amount, promo_code, discount, expires))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id

    def get_payment(self, payment_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE payment_id=?", (payment_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_payment_by_row_id(self, row_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE id=?", (row_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_payment_status(self, payment_id, status):
        conn = self.get_conn()
        cur = conn.cursor()
        paid_at = datetime.now().isoformat() if status == "success" else None
        cur.execute("UPDATE payments SET status=?, paid_at=? WHERE payment_id=?",
                    (status, paid_at, payment_id))
        conn.commit()
        conn.close()

    def mark_delivered(self, payment_id):
        conn = self.get_conn()
        conn.execute("UPDATE payments SET delivery_status='delivered' WHERE payment_id=?", (payment_id,))
        conn.commit()
        conn.close()

    def get_pending_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE status='pending' AND expires_at > datetime('now')")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def expire_payments(self):
        conn = self.get_conn()
        conn.execute("UPDATE payments SET status='expired' WHERE status='pending' AND expires_at <= datetime('now')")
        conn.commit()
        conn.close()

    def get_user_payments(self, user_id, limit=20):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_active_payment(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE user_id=? AND status='pending' AND expires_at > datetime('now') LIMIT 1", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_payments(self, limit=50):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_undelivered_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE status='success' AND delivery_status='not_delivered'")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_user_spent(self, user_id, amount):
        conn = self.get_conn()
        conn.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()

    def add_promo(self, code, discount, max_uses=-1):
        conn = self.get_conn()
        try:
            conn.execute("INSERT INTO promo_codes (code, discount_percent, max_uses) VALUES (?,?,?)",
                         (code.upper(), discount, max_uses))
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
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def use_promo(self, code):
        conn = self.get_conn()
        conn.execute("UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code=?", (code.upper(),))
        conn.commit()
        conn.close()

    def validate_promo(self, code, amount=0):
        p = self.get_promo(code)
        if not p:
            return False, "Промокод не найден", 0
        if p["max_uses"] != -1 and p["current_uses"] >= p["max_uses"]:
            return False, "Промокод исчерпан", 0
        return True, "OK", p["discount_percent"]

    def get_stats(self):
        conn = self.get_conn()
        cur = conn.cursor()
        stats = {}
        cur.execute("SELECT COUNT(*) FROM users"); stats["users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='success'"); stats["success"] = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='success'"); stats["revenue"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='success' AND delivery_status='not_delivered'"); stats["undelivered"] = cur.fetchone()[0]
        conn.close()
        return stats


db = Database()


# ==================== YOOMONEY ====================
class YooMoney:
    @staticmethod
    def generate_url(amount, label, comment=""):
        params = {
            "receiver": YOOMONEY_WALLET,
            "quickpay-form": "button",
            "paymentType": "AC",
            "sum": str(amount),
            "label": label,
            "comment": comment or "Оплата",
            "successURL": WEBAPP_URL
        }
        return f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(params)}"

    @staticmethod
    async def check_payment(label, expected_amount):
        if not YOOMONEY_ACCESS_TOKEN:
            return False, "No token"
        url = "https://yoomoney.ru/api/operation-history"
        headers = {"Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
                   "Content-Type": "application/x-www-form-urlencoded"}
        data = {"type": "deposition", "label": label, "records": 10}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, data=data, timeout=15) as resp:
                    if resp.status != 200:
                        return False, f"HTTP {resp.status}"
                    result = await resp.json()
                    for op in result.get("operations", []):
                        if op.get("label") == label and op.get("status") == "success":
                            if float(op.get("amount", 0)) >= expected_amount:
                                return True, "OK"
                    return False, "Not found"
            except Exception as e:
                return False, str(e)


# ==================== HELPERS ====================
def get_product(category, key):
    cat = CATEGORIES.get(category)
    return cat["products"].get(key) if cat else None

def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_price(p):
    return f"{p:,}".replace(",", " ") + " ₽"


# ==================== WEB API ====================
routes = web.RouteTableDef()

# CORS middleware
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@routes.get('/')
async def index(request):
    html = get_webapp_html()
    return web.Response(text=html, content_type='text/html', charset='utf-8')


@routes.get('/health')
async def health(request):
    return web.json_response({"status": "ok", "time": datetime.now().isoformat()})


@routes.post('/api/promo/check')
async def api_promo_check(request):
    try:
        data = await request.json()
        code = data.get("code", "").strip().upper()
        amount = data.get("amount", 0)
        
        if not code:
            return web.json_response({"valid": False, "message": "Введите промокод"})
        
        valid, msg, discount = db.validate_promo(code, amount)
        logger.info(f"Promo check: {code} -> valid={valid}, discount={discount}")
        return web.json_response({"valid": valid, "message": msg, "discount": discount})
    except Exception as e:
        logger.error(f"Promo check error: {e}")
        return web.json_response({"valid": False, "message": "Ошибка"})


@routes.post('/api/payment/create')
async def api_create_payment(request):
    try:
        data = await request.json()
        logger.info(f"Payment create request: {data}")
        
        # Получаем user_id из разных источников
        user_id = data.get("user_id")
        if not user_id:
            # Попробуем из initData
            init_data = data.get("init_data", "")
            if init_data:
                try:
                    parsed = dict(x.split('=', 1) for x in init_data.split('&') if '=' in x)
                    user_json = unquote(parsed.get('user', '{}'))
                    user_data = json.loads(user_json)
                    user_id = user_data.get('id')
                except:
                    pass
        
        if not user_id:
            user_id = int(time.time())  # Fallback для тестов
            logger.warning(f"No user_id, using fallback: {user_id}")

        category = data.get("category")
        product_key = data.get("product")
        promo_code = data.get("promo_code")
        discount = data.get("discount", 0)

        product = get_product(category, product_key)
        if not product:
            return web.json_response({"success": False, "message": "Товар не найден"})

        # Проверяем активный платёж
        active = db.get_user_active_payment(user_id)
        if active:
            return web.json_response({"success": False, "message": "У вас есть активный платёж"})

        price = product["price"]
        original = price

        if promo_code and discount > 0:
            valid, _, real_discount = db.validate_promo(promo_code, price)
            if valid:
                discount = real_discount
                price = max(1, round(price * (100 - discount) / 100))
            else:
                discount = 0
                promo_code = None

        payment_id = str(uuid.uuid4())
        label = f"p_{user_id}_{int(time.time())}_{payment_id[:8]}"
        payment_url = YooMoney.generate_url(price, label, f"Покупка: {product['name']}")

        row_id = db.add_payment(
            user_id=user_id, product_key=product_key, category=category,
            payment_id=payment_id, payment_label=label, amount=price,
            original_amount=original, promo_code=promo_code, discount=discount
        )

        if promo_code:
            db.use_promo(promo_code)

        db.get_or_create_user(user_id)
        logger.info(f"Payment created: #{row_id}, user={user_id}, amount={price}")

        # Уведомляем админов
        if bot_app:
            for aid in ADMIN_IDS:
                try:
                    await bot_app.bot.send_message(
                        aid,
                        f"🆕 <b>Платёж #{row_id}</b>\n"
                        f"👤 {user_id}\n📦 {product['name']}\n💰 {format_price(price)}",
                        parse_mode=ParseMode.HTML)
                except:
                    pass

        return web.json_response({
            "success": True,
            "payment_id": payment_id,
            "amount": price,
            "payment_url": payment_url,
            "order_id": row_id
        })

    except Exception as e:
        logger.exception(f"Payment create error: {e}")
        return web.json_response({"success": False, "message": f"Ошибка: {e}"})


@routes.post('/api/payment/check')
async def api_check_payment(request):
    try:
        data = await request.json()
        payment_id = data.get("payment_id")
        
        if not payment_id:
            return web.json_response({"paid": False, "message": "No payment_id"})

        payment = db.get_payment(payment_id)
        if not payment:
            return web.json_response({"paid": False, "message": "Not found"})

        if payment["status"] == "success":
            return web.json_response({"paid": True})

        if payment["status"] in ("cancelled", "expired"):
            return web.json_response({"paid": False, "message": "Cancelled/Expired"})

        # Проверяем через YooMoney
        ok, msg = await YooMoney.check_payment(payment["payment_label"], payment["amount"])
        logger.info(f"YooMoney check: {payment_id} -> {ok}, {msg}")

        if ok:
            db.update_payment_status(payment_id, "success")
            db.update_user_spent(payment["user_id"], payment["amount"])

            # Уведомляем
            if bot_app:
                product = get_product(payment["category"], payment["product_key"])
                for aid in ADMIN_IDS:
                    try:
                        await bot_app.bot.send_message(
                            aid,
                            f"💰 <b>Оплата #{payment['id']}</b>\n"
                            f"👤 {payment['user_id']}\n"
                            f"📦 {product['name'] if product else payment['product_key']}\n"
                            f"💵 {format_price(payment['amount'])}\n📦 Выдайте!",
                            parse_mode=ParseMode.HTML)
                    except:
                        pass

                try:
                    await bot_app.bot.send_message(
                        payment["user_id"],
                        f"✅ <b>Оплата подтверждена!</b>\n"
                        f"📦 {product['name'] if product else payment['product_key']}\n"
                        f"⏳ Товар будет выдан!",
                        parse_mode=ParseMode.HTML)
                except:
                    pass

            return web.json_response({"paid": True})

        return web.json_response({"paid": False, "message": msg})

    except Exception as e:
        logger.error(f"Check payment error: {e}")
        return web.json_response({"paid": False, "message": str(e)})


@routes.post('/api/payment/cancel')
async def api_cancel_payment(request):
    try:
        data = await request.json()
        payment_id = data.get("payment_id")
        if payment_id:
            payment = db.get_payment(payment_id)
            if payment and payment["status"] == "pending":
                db.update_payment_status(payment_id, "cancelled")
        return web.json_response({"ok": True})
    except:
        return web.json_response({"ok": False})


@routes.get('/api/orders')
async def api_orders(request):
    try:
        init_data = request.query.get("initData", "")
        user_id = None
        if init_data:
            try:
                parsed = dict(x.split('=', 1) for x in init_data.split('&') if '=' in x)
                user_json = unquote(parsed.get('user', '{}'))
                user_data = json.loads(user_json)
                user_id = user_data.get('id')
            except:
                pass

        if not user_id:
            return web.json_response({"orders": []})

        payments = db.get_user_payments(user_id, 20)
        orders = []
        for p in payments:
            product = get_product(p["category"], p["product_key"])
            orders.append({
                "id": p["id"],
                "product_name": product["name"] if product else p["product_key"],
                "amount": p["amount"],
                "status": p["status"],
                "created_at": p["created_at"][:16] if p["created_at"] else ""
            })
        return web.json_response({"orders": orders})
    except Exception as e:
        return web.json_response({"orders": [], "error": str(e)})


# ==================== TELEGRAM BOT ====================
bot_app = None


def get_main_kb(user_id=None):
    kb = [
        [InlineKeyboardButton("🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📜 Мои покупки", callback_data="orders")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    if user_id and is_admin(user_id):
        kb.append([InlineKeyboardButton("👑 Админ", callback_data="admin")])
    return InlineKeyboardMarkup(kb)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"👋 Привет, <b>{html.escape(user.first_name)}</b>!\n\n"
        f"💎 <b>Premium Shop</b>\n\n"
        f"⭐ Telegram Premium\n🌟 Stars\n🎨 NFT\n\n"
        f"Нажмите кнопку ниже:",
        reply_markup=get_main_kb(user.id),
        parse_mode=ParseMode.HTML
    )
    return MAIN_MENU


async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "orders":
        pays = db.get_user_payments(user_id, 10)
        if not pays:
            text = "📭 Покупок нет"
        else:
            text = "📜 <b>Покупки:</b>\n\n"
            for p in pays:
                st = {"success": "✅", "pending": "⏳", "expired": "❌", "cancelled": "🚫"}.get(p["status"], "❓")
                prod = get_product(p["category"], p["product_key"])
                text += f"{st} #{p['id']} {prod['name'] if prod else p['product_key']} — {format_price(p['amount'])}\n"
        kb = [[InlineKeyboardButton("🔙 Меню", callback_data="menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ <b>Помощь</b>\n\n1. Откройте магазин\n2. Выберите товар\n3. Оплатите\n4. Получите товар",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Меню", callback_data="menu")]]),
            parse_mode=ParseMode.HTML
        )

    elif data == "menu":
        await query.edit_message_text(
            "🏠 <b>Главное меню</b>",
            reply_markup=get_main_kb(user_id),
            parse_mode=ParseMode.HTML
        )

    elif data == "admin" and is_admin(user_id):
        stats = db.get_stats()
        kb = [
            [InlineKeyboardButton("📦 Невыданные", callback_data="adm_undelivered")],
            [InlineKeyboardButton("📋 Платежи", callback_data="adm_payments")],
            [InlineKeyboardButton("✅ Подтвердить", callback_data="adm_confirm")],
            [InlineKeyboardButton("📦 Выдать", callback_data="adm_deliver")],
            [InlineKeyboardButton("🎟 +Промокод", callback_data="adm_promo")],
            [InlineKeyboardButton("🔙 Меню", callback_data="menu")]
        ]
        await query.edit_message_text(
            f"👑 <b>Админ</b>\n\n👥 {stats['users']}\n✅ {stats['success']}\n💰 {format_price(stats['revenue'])}\n📦 Невыдано: {stats['undelivered']}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
        return ADMIN_MENU

    elif data == "adm_undelivered" and is_admin(user_id):
        pays = db.get_undelivered_payments()
        if not pays:
            text = "✅ Всё выдано!"
        else:
            text = "📦 <b>Невыданные:</b>\n\n"
            for p in pays:
                prod = get_product(p["category"], p["product_key"])
                text += f"#{p['id']} | {p['user_id']} | {prod['name'] if prod else p['product_key']}\n"
        kb = [[InlineKeyboardButton("🔙 Админ", callback_data="admin")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "adm_payments" and is_admin(user_id):
        pays = db.get_all_payments(15)
        text = "📋 <b>Платежи:</b>\n\n"
        for p in pays:
            st = {"success": "✅", "pending": "⏳", "expired": "❌", "cancelled": "🚫"}.get(p["status"], "❓")
            text += f"{st} #{p['id']} | {p['user_id']} | {format_price(p['amount'])}\n"
        kb = [[InlineKeyboardButton("🔙 Админ", callback_data="admin")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "adm_confirm" and is_admin(user_id):
        context.user_data["admin_action"] = "confirm"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin")]]
        await query.edit_message_text("Введите ID платежа для подтверждения:", reply_markup=InlineKeyboardMarkup(kb))
        return ADMIN_INPUT

    elif data == "adm_deliver" and is_admin(user_id):
        context.user_data["admin_action"] = "deliver"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin")]]
        await query.edit_message_text("Введите ID платежа для выдачи:", reply_markup=InlineKeyboardMarkup(kb))
        return ADMIN_INPUT

    elif data == "adm_promo" and is_admin(user_id):
        context.user_data["admin_action"] = "promo"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin")]]
        await query.edit_message_text("Введите: КОД СКИДКА% [МАКС]\nПример: SALE20 20 100", reply_markup=InlineKeyboardMarkup(kb))
        return ADMIN_INPUT

    return MAIN_MENU


async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return MAIN_MENU

    action = context.user_data.get("admin_action")
    text = update.message.text.strip()

    if action == "confirm":
        try:
            rid = int(text.replace("#", ""))
            p = db.get_payment_by_row_id(rid)
            if not p:
                await update.message.reply_text("❌ Не найден")
            elif p["status"] == "success":
                await update.message.reply_text("✅ Уже подтверждён")
            else:
                db.update_payment_status(p["payment_id"], "success")
                db.update_user_spent(p["user_id"], p["amount"])
                await update.message.reply_text(f"✅ #{rid} подтверждён")
                try:
                    prod = get_product(p["category"], p["product_key"])
                    await context.bot.send_message(p["user_id"],
                        f"✅ Платёж #{rid} подтверждён!\n📦 {prod['name'] if prod else p['product_key']}",
                        parse_mode=ParseMode.HTML)
                except:
                    pass
        except:
            await update.message.reply_text("❌ Введите число")

    elif action == "deliver":
        try:
            rid = int(text.replace("#", ""))
            p = db.get_payment_by_row_id(rid)
            if not p:
                await update.message.reply_text("❌ Не найден")
            elif p["status"] != "success":
                await update.message.reply_text("⚠️ Не оплачен")
            elif p["delivery_status"] == "delivered":
                await update.message.reply_text("✅ Уже выдан")
            else:
                db.mark_delivered(p["payment_id"])
                await update.message.reply_text(f"✅ #{rid} выдан")
                try:
                    prod = get_product(p["category"], p["product_key"])
                    await context.bot.send_message(p["user_id"],
                        f"🎉 Товар выдан!\n📦 {prod['name'] if prod else p['product_key']}",
                        parse_mode=ParseMode.HTML)
                except:
                    pass
        except:
            await update.message.reply_text("❌ Введите число")

    elif action == "promo":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("Формат: КОД СКИДКА% [МАКС]")
        else:
            code = parts[0].upper()
            try:
                disc = int(parts[1].replace("%", ""))
                mx = int(parts[2]) if len(parts) > 2 else -1
                if db.add_promo(code, disc, mx):
                    await update.message.reply_text(f"✅ Промокод {code} ({disc}%) создан")
                else:
                    await update.message.reply_text("❌ Уже существует")
            except:
                await update.message.reply_text("❌ Ошибка формата")

    context.user_data["admin_action"] = None
    return ADMIN_MENU


# ==================== BACKGROUND TASKS ====================
async def background_checker():
    while True:
        try:
            db.expire_payments()
            for p in db.get_pending_payments():
                ok, _ = await YooMoney.check_payment(p["payment_label"], p["amount"])
                if ok:
                    db.update_payment_status(p["payment_id"], "success")
                    db.update_user_spent(p["user_id"], p["amount"])
                    logger.info(f"Auto-confirmed: #{p['id']}")
                    if bot_app:
                        prod = get_product(p["category"], p["product_key"])
                        for aid in ADMIN_IDS:
                            try:
                                await bot_app.bot.send_message(aid,
                                    f"💰 Авто: #{p['id']} | {format_price(p['amount'])} | Выдайте!")
                            except:
                                pass
                        try:
                            await bot_app.bot.send_message(p["user_id"],
                                f"✅ Оплата #{p['id']} подтверждена!\n📦 {prod['name'] if prod else p['product_key']}")
                        except:
                            pass
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Background error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ==================== STARTUP ====================
async def on_startup(app):
    global bot_app
    
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(btn_handler)],
            ADMIN_MENU: [CallbackQueryHandler(btn_handler)],
            ADMIN_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_input),
                CallbackQueryHandler(btn_handler)
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
    )
    
    bot_app.add_handler(conv)
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_my_commands([BotCommand("start", "Главное меню")])
    await bot_app.updater.start_polling(drop_pending_updates=True)
    
    asyncio.create_task(background_checker())
    
    logger.info(f"🚀 Started! Web: {WEBAPP_URL}")
    for aid in ADMIN_IDS:
        try:
            await bot_app.bot.send_message(aid, f"🟢 Бот запущен!\n🌐 {WEBAPP_URL}")
        except:
            pass


async def on_shutdown(app):
    global bot_app
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


def main():
    db.init_db()
    
    app = web.Application(middlewares=[cors_middleware])
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_routes(routes)
    
    logger.info(f"Starting server on {WEBAPP_HOST}:{WEBAPP_PORT}")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT, print=None)


if __name__ == "__main__":
    main()
