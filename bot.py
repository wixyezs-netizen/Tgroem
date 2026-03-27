#!/usr/bin/env python3
"""
Telegram Premium Shop Bot с встроенным Mini App интерфейсом
Единый файл: бот + веб-сервер Mini App
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
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode, quote, parse_qs, unquote
from aiohttp import web
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler,
    filters
)
from telegram.constants import ParseMode

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8633048902:AAF_ae0F_BR1KS-LkNzBE2GcOh1svZLV2L8"
ADMIN_IDS = [8681521200]

YOOMONEY_WALLET = "4100118889570559"
YOOMONEY_ACCESS_TOKEN = "4100118889570559.3288B2E716CEEB922A26BD6BEAC58648FBFB680CCF64E4E1447D714D6FB5EA5F01F1478FAC686BEF394C8A186C98982DE563C1ABCDF9F2F61D971B61DA3C7E486CA818F98B9E0069F1C0891E090DD56A11319D626A40F0AE8302A8339DED9EB7969617F191D93275F64C4127A3ECB7AED33FCDE91CA68690EB7534C67E6C219E"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8080
WEBAPP_URL = "https://telegram.premium.bothost.tech"

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
                "features": ["Уникальные стикеры и реакции", "Без рекламы", "Файлы до 4 ГБ", "Быстрая загрузка", "Расшифровка голосовых"],
                "badge": "",
                "delivery_type": "manual"
            },
            "premium_3m": {
                "name": "Premium 3 месяца",
                "price": 639,
                "description": "Telegram Premium подписка на 3 месяца",
                "features": ["Все преимущества Premium", "Скидка при покупке на 3 месяца"],
                "badge": "Выгодно",
                "delivery_type": "manual"
            },
            "premium_6m": {
                "name": "Premium 6 месяцев",
                "price": 1199,
                "description": "Telegram Premium подписка на 6 месяцев",
                "features": ["Все преимущества Premium", "Максимальная выгода"],
                "badge": "Популярный",
                "delivery_type": "manual"
            },
            "premium_12m": {
                "name": "Premium 12 месяцев",
                "price": 2159,
                "description": "Telegram Premium подписка на 12 месяцев",
                "features": ["Все преимущества Premium", "Лучшая цена за месяц"],
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
                "description": "50 Telegram Stars",
                "features": ["Поддержка авторов", "Покупки в ботах", "Оплата сервисов"],
                "badge": "",
                "delivery_type": "manual"
            },
            "stars_100": {
                "name": "100 Stars",
                "price": 112,
                "description": "100 Telegram Stars",
                "features": ["Поддержка авторов", "Покупки в ботах", "Выгоднее чем 50"],
                "badge": "",
                "delivery_type": "manual"
            },
            "stars_250": {
                "name": "250 Stars",
                "price": 264,
                "description": "250 Telegram Stars",
                "features": ["Поддержка авторов", "Покупки в ботах", "Отличная скидка"],
                "badge": "Выгодно",
                "delivery_type": "manual"
            },
            "stars_500": {
                "name": "500 Stars",
                "price": 496,
                "description": "500 Telegram Stars",
                "features": ["Поддержка авторов", "Покупки в ботах", "Максимум звёзд"],
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
                "description": "Базовый NFT из коллекции",
                "features": ["Уникальный дизайн", "Подтверждение в блокчейне", "Можно перепродать"],
                "badge": "",
                "delivery_type": "manual"
            },
            "nft_rare": {
                "name": "NFT Rare",
                "price": 399,
                "description": "Редкий NFT лимитированной серии",
                "features": ["Лимитированная серия", "Редкий дизайн", "Высокая ценность"],
                "badge": "Редкий",
                "delivery_type": "manual"
            },
            "nft_legendary": {
                "name": "NFT Legendary",
                "price": 799,
                "description": "Легендарный NFT — всего 100 в мире",
                "features": ["Всего 100 штук", "Легендарный статус", "Коллекционная ценность"],
                "badge": "Легендарный",
                "delivery_type": "manual"
            },
        }
    }
}

CHECK_INTERVAL = 30
PAYMENT_TIMEOUT_HOURS = 24
DB_NAME = "bot_shop.db"

(
    MAIN_MENU, SELECTING_CATEGORY, SELECTING_PRODUCT, PRODUCT_DETAIL,
    ENTERING_PROMO, CONFIRMING, WAITING_PAYMENT, ADMIN_MENU,
    ADMIN_MANUAL_ID, ADMIN_ADD_PROMO, ADMIN_BROADCAST
) = range(11)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ShopBot")


# ==================== MINI APP HTML ====================
def get_mini_app_html() -> str:
    """Полный HTML Mini App в стиле официального Telegram магазина"""
    return '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Telegram Premium Shop</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
:root {
    --tg-theme-bg-color: #ffffff;
    --tg-theme-text-color: #000000;
    --tg-theme-hint-color: #999999;
    --tg-theme-link-color: #2481cc;
    --tg-theme-button-color: #3390ec;
    --tg-theme-button-text-color: #ffffff;
    --tg-theme-secondary-bg-color: #f0f0f0;
    --tg-theme-header-bg-color: #ffffff;
    --tg-theme-section-bg-color: #ffffff;
    --tg-theme-accent-text-color: #3390ec;
    --tg-theme-destructive-text-color: #e53935;
    --tg-theme-subtitle-text-color: #999999;
    --tg-theme-section-separator-color: #e0e0e0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background-color: var(--tg-theme-secondary-bg-color);
    color: var(--tg-theme-text-color);
    min-height: 100vh;
    overflow-x: hidden;
    padding-bottom: 100px;
}

/* ===== HEADER ===== */
.header {
    background: linear-gradient(135deg, #2481cc 0%, #3390ec 50%, #50a0f0 100%);
    padding: 20px 16px 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
    animation: headerShine 8s ease-in-out infinite;
}

@keyframes headerShine {
    0%, 100% { transform: rotate(0deg); }
    50% { transform: rotate(180deg); }
}

.header-logo {
    width: 64px;
    height: 64px;
    margin: 0 auto 12px;
    background: rgba(255,255,255,0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    backdrop-filter: blur(10px);
    position: relative;
    z-index: 1;
}

.header h1 {
    color: white;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
    position: relative;
    z-index: 1;
}

.header p {
    color: rgba(255,255,255,0.85);
    font-size: 14px;
    position: relative;
    z-index: 1;
}

/* ===== PROMO BANNER ===== */
.promo-banner {
    margin: 12px 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 14px;
    padding: 16px;
    color: white;
    position: relative;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.2s;
}

.promo-banner:active {
    transform: scale(0.98);
}

.promo-banner::after {
    content: '🎁';
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 32px;
    opacity: 0.8;
}

.promo-banner h3 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
}

.promo-banner p {
    font-size: 13px;
    opacity: 0.9;
}

/* ===== CATEGORIES TABS ===== */
.categories-tabs {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
}

.categories-tabs::-webkit-scrollbar {
    display: none;
}

.tab-btn {
    flex-shrink: 0;
    padding: 10px 20px;
    border-radius: 20px;
    border: none;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    background: var(--tg-theme-section-bg-color);
    color: var(--tg-theme-text-color);
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.tab-btn.active {
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
    box-shadow: 0 2px 8px rgba(51,144,236,0.3);
}

.tab-btn:active {
    transform: scale(0.95);
}

/* ===== PRODUCTS GRID ===== */
.products-section {
    padding: 0 16px;
}

.section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--tg-theme-hint-color);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 16px 0 10px 4px;
}

.products-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

/* ===== PRODUCT CARD ===== */
.product-card {
    background: var(--tg-theme-section-bg-color);
    border-radius: 14px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.product-card:active {
    transform: scale(0.98);
    background: var(--tg-theme-secondary-bg-color);
}

.product-card-top {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
}

.product-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
}

.product-icon.star { background: linear-gradient(135deg, #FFD700, #FFA500); }
.product-icon.stars { background: linear-gradient(135deg, #9C27B0, #E040FB); }
.product-icon.nft { background: linear-gradient(135deg, #00BCD4, #2196F3); }

.product-info {
    flex: 1;
    min-width: 0;
}

.product-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--tg-theme-text-color);
    margin-bottom: 2px;
}

.product-desc {
    font-size: 13px;
    color: var(--tg-theme-hint-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.product-price-section {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.product-price {
    font-size: 18px;
    font-weight: 700;
    color: var(--tg-theme-text-color);
}

.product-price .currency {
    font-size: 14px;
    font-weight: 500;
    color: var(--tg-theme-hint-color);
}

.buy-btn {
    padding: 8px 20px;
    border-radius: 20px;
    border: none;
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}

.buy-btn:active {
    transform: scale(0.95);
    opacity: 0.9;
}

.product-badge {
    position: absolute;
    top: 12px;
    right: 12px;
    padding: 4px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
    color: white;
    background: linear-gradient(135deg, #FF6B6B, #FF8E53);
}

.product-badge.popular { background: linear-gradient(135deg, #3390ec, #50a0f0); }
.product-badge.best { background: linear-gradient(135deg, #00C853, #64DD17); }
.product-badge.rare { background: linear-gradient(135deg, #9C27B0, #E040FB); }
.product-badge.legendary { background: linear-gradient(135deg, #FF6D00, #FFD600); }

/* ===== PRODUCT DETAIL MODAL ===== */
.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    display: none;
    align-items: flex-end;
    justify-content: center;
    animation: fadeIn 0.2s ease;
}

.modal-overlay.active {
    display: flex;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.modal-content {
    background: var(--tg-theme-bg-color);
    border-radius: 20px 20px 0 0;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    animation: slideUp 0.3s ease;
    padding-bottom: env(safe-area-inset-bottom, 20px);
}

@keyframes slideUp {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
}

.modal-handle {
    width: 36px;
    height: 4px;
    background: var(--tg-theme-hint-color);
    opacity: 0.3;
    border-radius: 2px;
    margin: 10px auto 0;
}

.modal-header {
    padding: 20px 20px 0;
    text-align: center;
}

.modal-icon {
    width: 72px;
    height: 72px;
    border-radius: 18px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
}

.modal-title {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 6px;
}

.modal-price-display {
    font-size: 28px;
    font-weight: 800;
    color: var(--tg-theme-button-color);
    margin-bottom: 4px;
}

.modal-description {
    font-size: 14px;
    color: var(--tg-theme-hint-color);
    margin-bottom: 20px;
    line-height: 1.4;
}

.features-list {
    padding: 0 20px;
    margin-bottom: 20px;
}

.feature-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 0.5px solid var(--tg-theme-section-separator-color);
}

.feature-item:last-child {
    border-bottom: none;
}

.feature-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--tg-theme-secondary-bg-color);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}

.feature-text {
    font-size: 15px;
    color: var(--tg-theme-text-color);
}

/* ===== PROMO INPUT ===== */
.promo-section {
    padding: 0 20px;
    margin-bottom: 16px;
}

.promo-input-wrap {
    display: flex;
    gap: 8px;
}

.promo-input {
    flex: 1;
    padding: 12px 16px;
    border-radius: 12px;
    border: 1.5px solid var(--tg-theme-section-separator-color);
    background: var(--tg-theme-secondary-bg-color);
    color: var(--tg-theme-text-color);
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
}

.promo-input:focus {
    border-color: var(--tg-theme-button-color);
}

.promo-apply-btn {
    padding: 12px 20px;
    border-radius: 12px;
    border: none;
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
}

.promo-result {
    margin-top: 8px;
    font-size: 13px;
    padding: 8px 12px;
    border-radius: 8px;
    display: none;
}

.promo-result.success {
    display: block;
    background: rgba(76, 175, 80, 0.1);
    color: #4CAF50;
}

.promo-result.error {
    display: block;
    background: rgba(244, 67, 54, 0.1);
    color: #F44336;
}

/* ===== MODAL FOOTER ===== */
.modal-footer {
    padding: 16px 20px;
    position: sticky;
    bottom: 0;
    background: var(--tg-theme-bg-color);
    border-top: 0.5px solid var(--tg-theme-section-separator-color);
}

.modal-buy-btn {
    width: 100%;
    padding: 16px;
    border-radius: 14px;
    border: none;
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
    font-size: 17px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

.modal-buy-btn:active {
    transform: scale(0.98);
    opacity: 0.9;
}

.modal-buy-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* ===== PAYMENT SCREEN ===== */
.payment-screen {
    display: none;
    text-align: center;
    padding: 30px 20px;
}

.payment-screen.active {
    display: block;
}

.payment-loader {
    width: 48px;
    height: 48px;
    border: 3px solid var(--tg-theme-section-separator-color);
    border-top-color: var(--tg-theme-button-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 20px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.payment-status {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 10px;
}

.payment-info {
    font-size: 14px;
    color: var(--tg-theme-hint-color);
    line-height: 1.5;
    margin-bottom: 20px;
}

.payment-link-btn {
    display: inline-block;
    padding: 14px 32px;
    border-radius: 14px;
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
    text-decoration: none;
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    transition: all 0.2s;
}

.payment-link-btn:active {
    transform: scale(0.98);
}

.check-btn {
    display: block;
    width: 100%;
    padding: 14px;
    border-radius: 14px;
    border: 2px solid var(--tg-theme-button-color);
    background: transparent;
    color: var(--tg-theme-button-color);
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 12px;
    transition: all 0.2s;
}

.check-btn:active {
    background: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
}

/* ===== SUCCESS SCREEN ===== */
.success-screen {
    display: none;
    text-align: center;
    padding: 40px 20px;
}

.success-screen.active {
    display: block;
}

.success-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, #4CAF50, #66BB6A);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    font-size: 40px;
    animation: successPop 0.5s ease;
}

@keyframes successPop {
    0% { transform: scale(0); }
    60% { transform: scale(1.2); }
    100% { transform: scale(1); }
}

/* ===== ORDERS PAGE ===== */
.orders-page {
    display: none;
}

.orders-page.active {
    display: block;
}

.order-card {
    background: var(--tg-theme-section-bg-color);
    border-radius: 14px;
    padding: 16px;
    margin: 8px 16px;
}

.order-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.order-id {
    font-size: 13px;
    color: var(--tg-theme-hint-color);
}

.order-status {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 8px;
}

.order-status.success { background: rgba(76,175,80,0.1); color: #4CAF50; }
.order-status.pending { background: rgba(255,152,0,0.1); color: #FF9800; }
.order-status.expired { background: rgba(244,67,54,0.1); color: #F44336; }

.order-product {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
}

.order-amount {
    font-size: 15px;
    font-weight: 700;
    color: var(--tg-theme-button-color);
}

.order-date {
    font-size: 12px;
    color: var(--tg-theme-hint-color);
    margin-top: 6px;
}

/* ===== BOTTOM NAV ===== */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--tg-theme-bg-color);
    border-top: 0.5px solid var(--tg-theme-section-separator-color);
    display: flex;
    padding: 8px 0;
    padding-bottom: max(8px, env(safe-area-inset-bottom));
    z-index: 900;
}

.nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 6px 0;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
    background: none;
    color: var(--tg-theme-hint-color);
    font-size: 11px;
    font-weight: 500;
}

.nav-item.active {
    color: var(--tg-theme-button-color);
}

.nav-item svg {
    width: 24px;
    height: 24px;
}

.nav-item:active {
    transform: scale(0.9);
}

/* ===== SKELETON ===== */
.skeleton {
    background: linear-gradient(90deg,
        var(--tg-theme-secondary-bg-color) 25%,
        var(--tg-theme-section-bg-color) 50%,
        var(--tg-theme-secondary-bg-color) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ===== TOAST ===== */
.toast {
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%) translateY(-100px);
    padding: 12px 24px;
    border-radius: 12px;
    background: var(--tg-theme-text-color);
    color: var(--tg-theme-bg-color);
    font-size: 14px;
    font-weight: 500;
    z-index: 2000;
    transition: transform 0.3s ease;
    white-space: nowrap;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
}

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar { width: 0; }
</style>
</head>
<body>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<!-- MAIN PAGE -->
<div id="mainPage">
    <div class="header">
        <div class="header-logo">💎</div>
        <h1>Telegram Premium Shop</h1>
        <p>Официальные продукты Telegram</p>
    </div>

    <div class="promo-banner" onclick="showPromoInput()">
        <h3>Есть промокод?</h3>
        <p>Примените и получите скидку</p>
    </div>

    <div class="categories-tabs" id="categoryTabs"></div>

    <div class="products-section">
        <div class="section-title" id="sectionTitle">Все товары</div>
        <div class="products-list" id="productsList"></div>
    </div>
</div>

<!-- ORDERS PAGE -->
<div class="orders-page" id="ordersPage">
    <div class="header" style="padding: 16px;">
        <h1 style="font-size: 20px;">Мои покупки</h1>
    </div>
    <div id="ordersList" style="padding-top: 8px;"></div>
</div>

<!-- PRODUCT MODAL -->
<div class="modal-overlay" id="productModal" onclick="closeModalOutside(event)">
    <div class="modal-content" id="modalContent">
        <div class="modal-handle"></div>

        <div id="modalProductView">
            <div class="modal-header">
                <div class="modal-icon" id="modalIcon">⭐</div>
                <div class="modal-title" id="modalTitle"></div>
                <div class="modal-price-display" id="modalPrice"></div>
                <div class="modal-description" id="modalDesc"></div>
            </div>

            <div class="features-list" id="featuresList"></div>

            <div class="promo-section">
                <div class="promo-input-wrap">
                    <input type="text" class="promo-input" id="promoInput"
                           placeholder="Промокод" autocapitalize="characters">
                    <button class="promo-apply-btn" onclick="applyPromo()">Применить</button>
                </div>
                <div class="promo-result" id="promoResult"></div>
            </div>

            <div class="modal-footer">
                <button class="modal-buy-btn" id="buyBtn" onclick="createPayment()">
                    <span>Купить</span>
                    <span id="buyBtnPrice"></span>
                </button>
            </div>
        </div>

        <div class="payment-screen" id="paymentScreen">
            <div class="payment-loader"></div>
            <div class="payment-status">Ожидание оплаты</div>
            <div class="payment-info" id="paymentInfo"></div>
            <a class="payment-link-btn" id="paymentLink" href="#" target="_blank">💳 Оплатить</a>
            <button class="check-btn" onclick="checkPayment()">✅ Проверить оплату</button>
            <button class="check-btn" onclick="cancelPayment()"
                    style="border-color: var(--tg-theme-destructive-text-color);
                           color: var(--tg-theme-destructive-text-color); margin-top: 8px;">
                ❌ Отменить
            </button>
        </div>

        <div class="success-screen" id="successScreen">
            <div class="success-icon">✓</div>
            <div class="payment-status" style="color: #4CAF50;">Оплата подтверждена!</div>
            <div class="payment-info">
                Товар будет выдан в ближайшее время.<br>
                Вы получите уведомление в боте.
            </div>
            <button class="modal-buy-btn" onclick="closeModal()" style="margin-top: 20px;">
                Отлично!
            </button>
        </div>
    </div>
</div>

<!-- PROMO MODAL -->
<div class="modal-overlay" id="promoModal" onclick="closePromoModal(event)">
    <div class="modal-content" style="max-height: 40vh;">
        <div class="modal-handle"></div>
        <div style="padding: 20px;">
            <div class="modal-title" style="margin-bottom: 16px;">🎁 Промокод</div>
            <div class="promo-input-wrap">
                <input type="text" class="promo-input" id="globalPromoInput"
                       placeholder="Введите промокод" autocapitalize="characters">
                <button class="promo-apply-btn" onclick="applyGlobalPromo()">Проверить</button>
            </div>
            <div class="promo-result" id="globalPromoResult"></div>
        </div>
    </div>
</div>

<!-- BOTTOM NAV -->
<div class="bottom-nav">
    <button class="nav-item active" onclick="showPage('main')" id="navMain">
        <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
        </svg>
        <span>Магазин</span>
    </button>
    <button class="nav-item" onclick="showPage('orders')" id="navOrders">
        <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
        </svg>
        <span>Покупки</span>
    </button>
    <button class="nav-item" onclick="showPage('profile')" id="navProfile">
        <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
        <span>Профиль</span>
    </button>
</div>

<script>
// ===== ИНИЦИАЛИЗАЦИЯ =====
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.enableClosingConfirmation();

const API_BASE = '';
let currentCategory = 'all';
let selectedProduct = null;
let selectedCategoryKey = '';
let selectedProductKey = '';
let currentPaymentId = null;
let currentPaymentLabel = null;
let appliedDiscount = 0;
let appliedPromoCode = '';
let checkInterval = null;

const CATEGORIES = ''' + json.dumps(CATEGORIES, ensure_ascii=False) + ''';

// ===== РЕНДЕРИНГ =====
function init() {
    renderTabs();
    renderProducts('all');
    applyTelegramTheme();
}

function applyTelegramTheme() {
    const root = document.documentElement;
    if (tg.themeParams) {
        const tp = tg.themeParams;
        if (tp.bg_color) root.style.setProperty('--tg-theme-bg-color', tp.bg_color);
        if (tp.text_color) root.style.setProperty('--tg-theme-text-color', tp.text_color);
        if (tp.hint_color) root.style.setProperty('--tg-theme-hint-color', tp.hint_color);
        if (tp.link_color) root.style.setProperty('--tg-theme-link-color', tp.link_color);
        if (tp.button_color) root.style.setProperty('--tg-theme-button-color', tp.button_color);
        if (tp.button_text_color) root.style.setProperty('--tg-theme-button-text-color', tp.button_text_color);
        if (tp.secondary_bg_color) root.style.setProperty('--tg-theme-secondary-bg-color', tp.secondary_bg_color);
        if (tp.section_bg_color) root.style.setProperty('--tg-theme-section-bg-color', tp.section_bg_color);
        if (tp.section_separator_color) root.style.setProperty('--tg-theme-section-separator-color', tp.section_separator_color);
        if (tp.subtitle_text_color) root.style.setProperty('--tg-theme-subtitle-text-color', tp.subtitle_text_color);
        if (tp.destructive_text_color) root.style.setProperty('--tg-theme-destructive-text-color', tp.destructive_text_color);
        if (tp.accent_text_color) root.style.setProperty('--tg-theme-accent-text-color', tp.accent_text_color);
        if (tp.header_bg_color) root.style.setProperty('--tg-theme-header-bg-color', tp.header_bg_color);
    }
}

function renderTabs() {
    const container = document.getElementById('categoryTabs');
    let html = '<button class="tab-btn active" onclick="filterCategory(\'all\', this)">Все</button>';
    for (const [key, cat] of Object.entries(CATEGORIES)) {
        html += `<button class="tab-btn" onclick="filterCategory('${key}', this)">${cat.emoji} ${cat.name}</button>`;
    }
    container.innerHTML = html;
}

function renderProducts(category) {
    const container = document.getElementById('productsList');
    const title = document.getElementById('sectionTitle');
    let html = '';

    for (const [catKey, cat] of Object.entries(CATEGORIES)) {
        if (category !== 'all' && category !== catKey) continue;

        for (const [prodKey, product] of Object.entries(cat.products)) {
            const badgeHtml = product.badge ?
                `<div class="product-badge ${getBadgeClass(product.badge)}">${product.badge}</div>` : '';

            html += `
                <div class="product-card" onclick="openProduct('${catKey}', '${prodKey}')">
                    ${badgeHtml}
                    <div class="product-card-top">
                        <div class="product-icon ${cat.icon}">${cat.emoji}</div>
                        <div class="product-info">
                            <div class="product-name">${product.name}</div>
                            <div class="product-desc">${product.description}</div>
                        </div>
                    </div>
                    <div class="product-price-section">
                        <div class="product-price">${product.price} <span class="currency">₽</span></div>
                        <button class="buy-btn" onclick="event.stopPropagation(); openProduct('${catKey}', '${prodKey}')">
                            Купить
                        </button>
                    </div>
                </div>
            `;
        }
    }

    container.innerHTML = html;

    if (category === 'all') {
        title.textContent = 'Все товары';
    } else {
        title.textContent = CATEGORIES[category]?.name || 'Товары';
    }
}

function getBadgeClass(badge) {
    const map = {
        'Популярный': 'popular',
        'Лучшая цена': 'best',
        'Выгодно': 'popular',
        'Хит продаж': 'popular',
        'Редкий': 'rare',
        'Легендарный': 'legendary'
    };
    return map[badge] || '';
}

function filterCategory(category, btn) {
    currentCategory = category;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderProducts(category);
    tg.HapticFeedback.selectionChanged();
}

// ===== СТРАНИЦЫ =====
function showPage(page) {
    document.getElementById('mainPage').style.display = page === 'main' ? 'block' : 'none';
    document.getElementById('ordersPage').className = page === 'orders' ? 'orders-page active' : 'orders-page';

    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    if (page === 'main') {
        document.getElementById('navMain').classList.add('active');
    } else if (page === 'orders') {
        document.getElementById('navOrders').classList.add('active');
        loadOrders();
    } else if (page === 'profile') {
        document.getElementById('navProfile').classList.add('active');
        tg.showAlert('👤 Профиль доступен в боте\\n\\nИспользуйте /start');
        document.getElementById('navMain').classList.add('active');
    }

    tg.HapticFeedback.selectionChanged();
}

async function loadOrders() {
    const container = document.getElementById('ordersList');
    try {
        const initData = tg.initData || '';
        const resp = await fetch(`${API_BASE}/api/orders?initData=${encodeURIComponent(initData)}`);
        const data = await resp.json();

        if (!data.orders || data.orders.length === 0) {
            container.innerHTML = '<div style="text-align:center; padding:40px; color:var(--tg-theme-hint-color);">📭 Покупок пока нет</div>';
            return;
        }

        let html = '';
        for (const order of data.orders) {
            const statusClass = order.status === 'success' ? 'success' :
                               order.status === 'pending' ? 'pending' : 'expired';
            const statusText = order.status === 'success' ? 'Оплачен' :
                              order.status === 'pending' ? 'Ожидает' : 'Истёк';

            html += `
                <div class="order-card">
                    <div class="order-header">
                        <span class="order-id">#${order.id}</span>
                        <span class="order-status ${statusClass}">${statusText}</span>
                    </div>
                    <div class="order-product">${order.product_name}</div>
                    <div class="order-amount">${order.amount} ₽</div>
                    <div class="order-date">${order.created_at}</div>
                </div>
            `;
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; padding:40px; color:var(--tg-theme-hint-color);">Ошибка загрузки</div>';
    }
}

// ===== PRODUCT MODAL =====
function openProduct(catKey, prodKey) {
    const cat = CATEGORIES[catKey];
    const product = cat.products[prodKey];
    if (!product) return;

    selectedCategoryKey = catKey;
    selectedProductKey = prodKey;
    selectedProduct = product;
    appliedDiscount = 0;
    appliedPromoCode = '';

    document.getElementById('modalIcon').className = `modal-icon product-icon ${cat.icon}`;
    document.getElementById('modalIcon').textContent = cat.emoji;
    document.getElementById('modalTitle').textContent = product.name;
    document.getElementById('modalPrice').textContent = product.price + ' ₽';
    document.getElementById('modalDesc').textContent = product.description;

    const featuresHtml = (product.features || []).map(f =>
        `<div class="feature-item">
            <div class="feature-icon">✓</div>
            <div class="feature-text">${f}</div>
        </div>`
    ).join('');
    document.getElementById('featuresList').innerHTML = featuresHtml;

    document.getElementById('buyBtnPrice').textContent = `за ${product.price} ₽`;
    document.getElementById('promoInput').value = '';
    document.getElementById('promoResult').className = 'promo-result';
    document.getElementById('promoResult').style.display = 'none';
    document.getElementById('buyBtn').disabled = false;

    showModalView('product');
    document.getElementById('productModal').classList.add('active');

    tg.HapticFeedback.impactOccurred('medium');
}

function showModalView(view) {
    document.getElementById('modalProductView').style.display = view === 'product' ? 'block' : 'none';
    document.getElementById('paymentScreen').className = view === 'payment' ? 'payment-screen active' : 'payment-screen';
    document.getElementById('successScreen').className = view === 'success' ? 'success-screen active' : 'success-screen';
}

function closeModal() {
    document.getElementById('productModal').classList.remove('active');
    if (checkInterval) {
        clearInterval(checkInterval);
        checkInterval = null;
    }
    selectedProduct = null;
    currentPaymentId = null;
    currentPaymentLabel = null;
}

function closeModalOutside(e) {
    if (e.target === document.getElementById('productModal')) {
        closeModal();
    }
}

// ===== ПРОМОКОД =====
async function applyPromo() {
    const code = document.getElementById('promoInput').value.trim().toUpperCase();
    if (!code) return;

    const result = document.getElementById('promoResult');
    try {
        const resp = await fetch(`${API_BASE}/api/promo/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code: code,
                amount: selectedProduct.price,
                initData: tg.initData || ''
            })
        });
        const data = await resp.json();

        if (data.valid) {
            appliedDiscount = data.discount;
            appliedPromoCode = code;
            const newPrice = Math.max(1, Math.round(selectedProduct.price * (100 - data.discount) / 100));

            result.className = 'promo-result success';
            result.textContent = `✅ Скидка ${data.discount}%! Новая цена: ${newPrice} ₽`;
            result.style.display = 'block';

            document.getElementById('modalPrice').innerHTML =
                `<s style="color:var(--tg-theme-hint-color);font-size:18px;">${selectedProduct.price} ₽</s> ${newPrice} ₽`;
            document.getElementById('buyBtnPrice').textContent = `за ${newPrice} ₽`;

            tg.HapticFeedback.notificationOccurred('success');
        } else {
            result.className = 'promo-result error';
            result.textContent = data.message || '❌ Промокод недействителен';
            result.style.display = 'block';
            tg.HapticFeedback.notificationOccurred('error');
        }
    } catch (e) {
        result.className = 'promo-result error';
        result.textContent = '❌ Ошибка проверки';
        result.style.display = 'block';
    }
}

function showPromoInput() {
    document.getElementById('promoModal').classList.add('active');
    document.getElementById('globalPromoInput').value = '';
    document.getElementById('globalPromoResult').style.display = 'none';
    tg.HapticFeedback.impactOccurred('light');
}

function closePromoModal(e) {
    if (e.target === document.getElementById('promoModal')) {
        document.getElementById('promoModal').classList.remove('active');
    }
}

async function applyGlobalPromo() {
    const code = document.getElementById('globalPromoInput').value.trim().toUpperCase();
    if (!code) return;

    const result = document.getElementById('globalPromoResult');
    try {
        const resp = await fetch(`${API_BASE}/api/promo/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, amount: 0, initData: tg.initData || '' })
        });
        const data = await resp.json();

        if (data.valid) {
            result.className = 'promo-result success';
            result.textContent = `✅ Промокод действителен! Скидка ${data.discount}%`;
            result.style.display = 'block';
            tg.HapticFeedback.notificationOccurred('success');
        } else {
            result.className = 'promo-result error';
            result.textContent = data.message || '❌ Недействителен';
            result.style.display = 'block';
            tg.HapticFeedback.notificationOccurred('error');
        }
    } catch (e) {
        result.className = 'promo-result error';
        result.textContent = '❌ Ошибка';
        result.style.display = 'block';
    }
}

// ===== ОПЛАТА =====
async function createPayment() {
    if (!selectedProduct) return;

    const btn = document.getElementById('buyBtn');
    btn.disabled = true;
    btn.innerHTML = '<span>Создание платежа...</span>';

    let price = selectedProduct.price;
    if (appliedDiscount > 0) {
        price = Math.max(1, Math.round(price * (100 - appliedDiscount) / 100));
    }

    try {
        const resp = await fetch(`${API_BASE}/api/payment/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: selectedCategoryKey,
                product: selectedProductKey,
                promo_code: appliedPromoCode || null,
                discount: appliedDiscount,
                initData: tg.initData || ''
            })
        });

        const data = await resp.json();

        if (data.success) {
            currentPaymentId = data.payment_id;
            currentPaymentLabel = data.label;

            document.getElementById('paymentInfo').innerHTML =
                `📦 ${selectedProduct.name}<br>💰 ${data.amount} ₽<br><br>Оплатите по ссылке и нажмите "Проверить"`;
            document.getElementById('paymentLink').href = data.payment_url;

            showModalView('payment');
            tg.HapticFeedback.notificationOccurred('success');

            // Автопроверка каждые 15 секунд
            checkInterval = setInterval(autoCheckPayment, 15000);
        } else {
            showToast(data.message || 'Ошибка создания платежа');
            btn.disabled = false;
            btn.innerHTML = `<span>Купить</span><span id="buyBtnPrice">за ${price} ₽</span>`;
            tg.HapticFeedback.notificationOccurred('error');
        }
    } catch (e) {
        showToast('Ошибка сети');
        btn.disabled = false;
        btn.innerHTML = `<span>Купить</span><span id="buyBtnPrice">за ${price} ₽</span>`;
    }
}

async function checkPayment() {
    if (!currentPaymentId) return;

    showToast('Проверяю оплату...');

    try {
        const resp = await fetch(`${API_BASE}/api/payment/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                payment_id: currentPaymentId,
                initData: tg.initData || ''
            })
        });

        const data = await resp.json();

        if (data.paid) {
            if (checkInterval) {
                clearInterval(checkInterval);
                checkInterval = null;
            }
            showModalView('success');
            tg.HapticFeedback.notificationOccurred('success');
        } else {
            showToast('⏳ Оплата пока не найдена');
            tg.HapticFeedback.notificationOccurred('warning');
        }
    } catch (e) {
        showToast('Ошибка проверки');
    }
}

async function autoCheckPayment() {
    if (!currentPaymentId) return;
    try {
        const resp = await fetch(`${API_BASE}/api/payment/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                payment_id: currentPaymentId,
                initData: tg.initData || ''
            })
        });
        const data = await resp.json();
        if (data.paid) {
            if (checkInterval) {
                clearInterval(checkInterval);
                checkInterval = null;
            }
            showModalView('success');
            tg.HapticFeedback.notificationOccurred('success');
        }
    } catch (e) {}
}

async function cancelPayment() {
    if (!currentPaymentId) return;

    tg.showConfirm('Отменить платёж?', async (confirmed) => {
        if (!confirmed) return;

        try {
            await fetch(`${API_BASE}/api/payment/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    payment_id: currentPaymentId,
                    initData: tg.initData || ''
                })
            });
        } catch (e) {}

        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
        closeModal();
        showToast('Платёж отменён');
    });
}

// ===== УТИЛИТЫ =====
function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

function formatPrice(price) {
    return price.toLocaleString('ru-RU') + ' ₽';
}

// Запуск
init();
</script>
</body>
</html>'''


# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name

    def get_conn(self):
        conn = sqlite3.connect(self.db_name, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self):
        conn = self.get_conn()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                referrer_id INTEGER,
                total_spent INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_key TEXT NOT NULL,
                category TEXT NOT NULL,
                payment_id TEXT NOT NULL UNIQUE,
                payment_label TEXT,
                amount INTEGER NOT NULL,
                original_amount INTEGER,
                promo_code TEXT,
                discount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'not_delivered',
                delivery_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                delivered_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                discount_percent INTEGER NOT NULL,
                max_uses INTEGER DEFAULT -1,
                current_uses INTEGER DEFAULT 0,
                min_amount INTEGER DEFAULT 0,
                created_by INTEGER,
                expires_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS admin_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
            CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_label ON payments(payment_label);
        ''')
        conn.commit()
        conn.close()
        logger.info("БД инициализирована")

    def get_or_create_user(self, user_id, username=None, first_name=None,
                           last_name=None, language_code=None, referrer_id=None):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()
        if not user:
            cur.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, language_code, referrer_id) VALUES (?,?,?,?,?,?)",
                (user_id, username, first_name, last_name, language_code, referrer_id))
            conn.commit()
            if referrer_id and referrer_id != user_id:
                cur.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)",
                            (referrer_id, user_id))
                conn.commit()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
        else:
            cur.execute("UPDATE users SET username=?, first_name=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                        (username, first_name, user_id))
            conn.commit()
        result = dict(user)
        conn.close()
        return result

    def get_user(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_payment(self, user_id, product_key, category, payment_id, payment_label,
                    amount, original_amount=None, promo_code=None, discount=0):
        conn = self.get_conn()
        cur = conn.cursor()
        expires_at = (datetime.now() + timedelta(hours=PAYMENT_TIMEOUT_HOURS)).isoformat()
        cur.execute(
            """INSERT INTO payments (user_id, product_key, category, payment_id, payment_label,
               amount, original_amount, promo_code, discount, expires_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_id, product_key, category, payment_id, payment_label,
             amount, original_amount or amount, promo_code, discount, expires_at))
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        return row_id

    def get_payment(self, payment_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_payment_by_row_id(self, row_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE id = ?", (row_id,))
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

    def mark_delivered(self, payment_id, info=""):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE payments SET delivery_status='delivered', delivery_info=?, delivered_at=CURRENT_TIMESTAMP WHERE payment_id=?",
                    (info, payment_id))
        conn.commit()
        conn.close()

    def get_pending_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE status='pending' AND expires_at > datetime('now') ORDER BY created_at")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def expire_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE payments SET status='expired' WHERE status='pending' AND expires_at <= datetime('now')")
        conn.commit()
        count = cur.rowcount
        conn.close()
        return count

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
        cur.execute("SELECT * FROM payments WHERE user_id=? AND status='pending' AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT 1",
                    (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_payments(self, limit=50, status=None):
        conn = self.get_conn()
        cur = conn.cursor()
        if status:
            cur.execute("SELECT * FROM payments WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit))
        else:
            cur.execute("SELECT * FROM payments ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_undelivered_payments(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM payments WHERE status='success' AND delivery_status='not_delivered' ORDER BY paid_at")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_user_spent(self, user_id, amount):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    def add_promo(self, code, discount_percent, max_uses=-1, min_amount=0, expires_at=None, created_by=None):
        conn = self.get_conn()
        try:
            conn.execute(
                "INSERT INTO promo_codes (code, discount_percent, max_uses, min_amount, expires_at, created_by) VALUES (?,?,?,?,?,?)",
                (code.upper(), discount_percent, max_uses, min_amount, expires_at, created_by))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
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
        promo = self.get_promo(code)
        if not promo:
            return False, "Промокод не найден", 0
        if promo["max_uses"] != -1 and promo["current_uses"] >= promo["max_uses"]:
            return False, "Промокод исчерпан", 0
        if promo["expires_at"] and datetime.fromisoformat(promo["expires_at"]) < datetime.now():
            return False, "Промокод истёк", 0
        if amount > 0 and amount < promo["min_amount"]:
            return False, f"Мин. сумма: {promo['min_amount']} ₽", 0
        return True, "OK", promo["discount_percent"]

    def get_all_promos(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self):
        conn = self.get_conn()
        cur = conn.cursor()
        stats = {}
        cur.execute("SELECT COUNT(*) FROM users"); stats["total_users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments"); stats["total_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='success'"); stats["success_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'"); stats["pending_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='success'"); stats["total_revenue"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='success' AND date(paid_at)=date('now')"); stats["today_payments"] = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='success' AND date(paid_at)=date('now')"); stats["today_revenue"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')"); stats["today_users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM payments WHERE status='success' AND delivery_status='not_delivered'"); stats["undelivered"] = cur.fetchone()[0]
        conn.close()
        return stats

    def admin_log(self, admin_id, action, details=""):
        conn = self.get_conn()
        conn.execute("INSERT INTO admin_log (admin_id, action, details) VALUES (?,?,?)",
                     (admin_id, action, details))
        conn.commit()
        conn.close()

    def get_referral_count(self, user_id):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
        c = cur.fetchone()[0]
        conn.close()
        return c


db = Database()


# ==================== YOOMONEY ====================
class YooMoneyPayment:
    @staticmethod
    def generate_payment_url(amount, label, comment=""):
        params = {
            "receiver": YOOMONEY_WALLET,
            "quickpay-form": "button",
            "paymentType": "AC",
            "sum": str(amount),
            "label": label,
            "comment": comment or "Оплата товара",
            "successURL": WEBAPP_URL,
            "targets": comment or "Оплата товара",
        }
        return f"https://yoomoney.ru/quickpay/confirm.xml?{urlencode(params)}"

    @staticmethod
    async def check_payment_by_label(label, expected_amount):
        if not YOOMONEY_ACCESS_TOKEN:
            return False, "Токен не настроен"
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
                                return True, "Оплачено"
                    return False, "Не найден"
            except Exception as e:
                return False, str(e)

    @staticmethod
    async def get_balance():
        if not YOOMONEY_ACCESS_TOKEN:
            return None
        url = "https://yoomoney.ru/api/account-info"
        headers = {"Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("balance")
            except:
                pass
        return None


# ==================== УТИЛИТЫ ====================
def get_product_info(category_key, product_key):
    cat = CATEGORIES.get(category_key)
    if not cat:
        return None
    return cat["products"].get(product_key)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_price(price):
    return f"{price:,}".replace(",", " ") + " ₽"

def validate_init_data(init_data_str):
    """Валидация Telegram WebApp initData"""
    if not init_data_str:
        return None
    try:
        parsed = dict(x.split('=', 1) for x in init_data_str.split('&'))
        check_hash = parsed.pop('hash', '')
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash == check_hash:
            user_data = json.loads(unquote(parsed.get('user', '{}')))
            return user_data
    except:
        pass
    return None

def extract_user_id(init_data_str):
    """Извлечь user_id из initData (с валидацией или без)"""
    user_data = validate_init_data(init_data_str)
    if user_data:
        return user_data.get('id')
    # Фоллбек для разработки
    try:
        parsed = dict(x.split('=', 1) for x in init_data_str.split('&'))
        user_data = json.loads(unquote(parsed.get('user', '{}')))
        return user_data.get('id')
    except:
        return None


# ==================== WEB API (aiohttp) ====================
routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.Response(text=get_mini_app_html(), content_type='text/html', charset='utf-8')

@routes.get('/api/products')
async def api_products(request):
    return web.json_response({"categories": CATEGORIES})

@routes.get('/api/orders')
async def api_orders(request):
    init_data = request.query.get('initData', '')
    user_id = extract_user_id(init_data)
    if not user_id:
        return web.json_response({"orders": [], "error": "auth"})
    payments = db.get_user_payments(user_id, limit=20)
    orders = []
    for p in payments:
        product = get_product_info(p["category"], p["product_key"])
        orders.append({
            "id": p["id"],
            "product_name": product["name"] if product else p["product_key"],
            "amount": p["amount"],
            "status": p["status"],
            "delivery_status": p["delivery_status"],
            "created_at": p["created_at"][:16] if p["created_at"] else ""
        })
    return web.json_response({"orders": orders})

@routes.post('/api/promo/check')
async def api_promo_check(request):
    data = await request.json()
    code = data.get("code", "").strip().upper()
    amount = data.get("amount", 0)
    if not code:
        return web.json_response({"valid": False, "message": "Введите промокод"})
    valid, msg, discount = db.validate_promo(code, amount)
    return web.json_response({"valid": valid, "message": msg, "discount": discount})

@routes.post('/api/payment/create')
async def api_create_payment(request):
    data = await request.json()
    init_data = data.get("initData", "")
    user_id = extract_user_id(init_data)
    if not user_id:
        return web.json_response({"success": False, "message": "Авторизация не удалась"})

    category = data.get("category")
    product_key = data.get("product")
    promo_code = data.get("promo_code")
    discount = data.get("discount", 0)

    product = get_product_info(category, product_key)
    if not product:
        return web.json_response({"success": False, "message": "Товар не найден"})

    # Проверяем активный платёж
    active = db.get_user_active_payment(user_id)
    if active:
        return web.json_response({"success": False, "message": "У вас есть незавершённый платёж"})

    price = product["price"]
    original_price = price

    # Применяем промокод
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
    comment = f"Покупка: {product['name']}"
    payment_url = YooMoneyPayment.generate_payment_url(price, label, comment)

    row_id = db.add_payment(
        user_id=user_id, product_key=product_key, category=category,
        payment_id=payment_id, payment_label=label, amount=price,
        original_amount=original_price, promo_code=promo_code, discount=discount
    )

    if promo_code:
        db.use_promo(promo_code)

    db.get_or_create_user(user_id)

    logger.info(f"Новый платёж #{row_id}: user={user_id}, product={product_key}, amount={price}")

    # Уведомляем админов через бот
    global bot_application
    if bot_application:
        for admin_id in ADMIN_IDS:
            try:
                await bot_application.bot.send_message(
                    admin_id,
                    f"🆕 <b>Новый платёж #{row_id}</b>\n"
                    f"👤 {user_id}\n📦 {product['name']}\n💰 {format_price(price)}\n"
                    f"🏷 <code>{label}</code>",
                    parse_mode=ParseMode.HTML)
            except:
                pass

    return web.json_response({
        "success": True,
        "payment_id": payment_id,
        "label": label,
        "amount": price,
        "payment_url": payment_url,
        "order_id": row_id
    })

@routes.post('/api/payment/check')
async def api_check_payment(request):
    data = await request.json()
    payment_id = data.get("payment_id")
    if not payment_id:
        return web.json_response({"paid": False, "message": "No payment_id"})

    payment = db.get_payment(payment_id)
    if not payment:
        return web.json_response({"paid": False, "message": "Платёж не найден"})

    if payment["status"] == "success":
        return web.json_response({"paid": True})

    if payment["status"] in ("cancelled", "expired"):
        return web.json_response({"paid": False, "message": "Платёж отменён/истёк"})

    success, msg = await YooMoneyPayment.check_payment_by_label(payment["payment_label"], payment["amount"])

    if success:
        db.update_payment_status(payment_id, "success")
        db.update_user_spent(payment["user_id"], payment["amount"])
        logger.info(f"Платёж {payment_id} оплачен!")

        global bot_application
        if bot_application:
            for admin_id in ADMIN_IDS:
                try:
                    product = get_product_info(payment["category"], payment["product_key"])
                    await bot_application.bot.send_message(
                        admin_id,
                        f"💰 <b>Оплата подтверждена!</b>\n#{payment['id']} | {payment['user_id']}\n"
                        f"📦 {product['name'] if product else payment['product_key']}\n"
                        f"💰 {format_price(payment['amount'])}\n📦 Требуется выдача!",
                        parse_mode=ParseMode.HTML)
                except:
                    pass

            try:
                product = get_product_info(payment["category"], payment["product_key"])
                await bot_application.bot.send_message(
                    payment["user_id"],
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"📦 {product['name'] if product else payment['product_key']}\n"
                    f"💰 {format_price(payment['amount'])}\n\n"
                    f"⏳ Товар будет выдан в ближайшее время!",
                    parse_mode=ParseMode.HTML)
            except:
                pass

        return web.json_response({"paid": True})

    return web.json_response({"paid": False, "message": msg})

@routes.post('/api/payment/cancel')
async def api_cancel_payment(request):
    data = await request.json()
    payment_id = data.get("payment_id")
    if payment_id:
        payment = db.get_payment(payment_id)
        if payment and payment["status"] == "pending":
            db.update_payment_status(payment_id, "cancelled")
    return web.json_response({"ok": True})


# ==================== TELEGRAM BOT HANDLERS ====================
def get_main_kb(user_id=None):
    keyboard = [
        [InlineKeyboardButton("🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📜 Мои покупки", callback_data="my_orders"),
         InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("👥 Рефералка", callback_data="referral"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="help_info")],
    ]
    if user_id and is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton("📋 Платежи", callback_data="adm_payments")],
        [InlineKeyboardButton("📦 Невыданные", callback_data="adm_undelivered")],
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data="adm_confirm")],
        [InlineKeyboardButton("📦 Выдать товар", callback_data="adm_deliver")],
        [InlineKeyboardButton("🎟 Промокоды", callback_data="adm_promos")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton("💰 Баланс", callback_data="adm_balance")],
        [InlineKeyboardButton("🔙 Меню", callback_data="back_main")],
    ])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer = None
    if context.args and context.args[0].startswith("ref"):
        try:
            referrer = int(context.args[0][3:])
            if referrer == user.id:
                referrer = None
        except ValueError:
            pass

    db.get_or_create_user(user.id, user.username, user.first_name, user.last_name,
                          user.language_code, referrer)

    text = (
        f"👋 Привет, <b>{html.escape(user.first_name)}</b>!\n\n"
        f"💎 <b>Telegram Premium Shop</b>\n\n"
        f"Здесь вы можете приобрести:\n"
        f"⭐ Telegram Premium\n🌟 Telegram Stars\n🎨 NFT Коллекцию\n\n"
        f"💳 Оплата через ЮMoney\n"
        f"🔐 Безопасные покупки\n\n"
        f"Нажмите <b>«Открыть магазин»</b> для покупки:"
    )

    if referrer:
        text += "\n\n🎁 Вы пришли по реферальной ссылке!"

    await update.message.reply_text(text, reply_markup=get_main_kb(user.id), parse_mode=ParseMode.HTML)
    return MAIN_MENU


async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    user = update.effective_user

    if data == "back_main":
        await query.edit_message_text(
            f"🏠 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_kb(user_id), parse_mode=ParseMode.HTML)
        return MAIN_MENU

    elif data == "my_orders":
        payments = db.get_user_payments(user_id, 10)
        if not payments:
            text = "📭 Покупок пока нет.\n\nОткройте магазин!"
        else:
            text = "📜 <b>Ваши покупки:</b>\n\n"
            for p in payments:
                st = {"success": "✅", "pending": "⏳", "expired": "❌", "cancelled": "🚫"}.get(p["status"], "❓")
                prod = get_product_info(p["category"], p["product_key"])
                name = prod["name"] if prod else p["product_key"]
                dlv = " 📦" if p["delivery_status"] == "delivered" else ""
                text += f"{st} #{p['id']} {name} — {format_price(p['amount'])}{dlv}\n"
        kb = [[InlineKeyboardButton("🔙 Меню", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "profile":
        u = db.get_user(user_id)
        refs = db.get_referral_count(user_id)
        pays = db.get_user_payments(user_id, 1000)
        ok_count = sum(1 for p in pays if p["status"] == "success")
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"🆔 <code>{user_id}</code>\n"
            f"👤 {html.escape(u.get('first_name',''))}\n"
            f"🛍 Покупок: {ok_count}\n"
            f"💰 Потрачено: {format_price(u.get('total_spent',0))}\n"
            f"👥 Рефералов: {refs}\n"
            f"📅 Регистрация: {u.get('created_at','')[:10]}")
        kb = [[InlineKeyboardButton("🔙 Меню", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "referral":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=ref{user_id}"
        refs = db.get_referral_count(user_id)
        text = (
            f"👥 <b>Реферальная программа</b>\n\n"
            f"🔗 Ваша ссылка:\n<code>{link}</code>\n\n"
            f"👥 Приглашено: {refs}\n\n"
            f"Отправьте ссылку друзьям!")
        kb = [[InlineKeyboardButton("🔙 Меню", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "help_info":
        text = (
            "ℹ️ <b>Помощь</b>\n\n"
            "1. Откройте магазин кнопкой\n"
            "2. Выберите товар\n"
            "3. Оплатите по ссылке\n"
            "4. Дождитесь выдачи\n\n"
            "/start — меню\n/check — проверить платёж\n/history — покупки")
        kb = [[InlineKeyboardButton("🔙 Меню", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "admin_panel":
        if not is_admin(user_id):
            return
        await query.edit_message_text("👑 <b>Админ-панель</b>", reply_markup=get_admin_kb(),
                                      parse_mode=ParseMode.HTML)
        return ADMIN_MENU

    # === АДМИН ===
    elif data == "adm_stats":
        if not is_admin(user_id): return
        s = db.get_stats()
        bal = await YooMoneyPayment.get_balance()
        text = (
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Пользователей: {s['total_users']} (+{s['today_users']} сегодня)\n\n"
            f"💳 Платежей: {s['total_payments']}\n"
            f"✅ Успешных: {s['success_payments']}\n"
            f"⏳ Ожидающих: {s['pending_payments']}\n"
            f"📦 Невыданных: {s['undelivered']}\n\n"
            f"💰 Всего: {format_price(s['total_revenue'])}\n"
            f"💰 Сегодня: {format_price(s['today_revenue'])}\n\n"
            f"💼 Баланс: {f'{bal:.2f} ₽' if bal else 'Н/Д'}")
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "adm_payments":
        if not is_admin(user_id): return
        pays = db.get_all_payments(15)
        if not pays:
            text = "📭 Платежей нет"
        else:
            text = "📋 <b>Платежи:</b>\n\n"
            for p in pays:
                st = {"success":"✅","pending":"⏳","expired":"❌","cancelled":"🚫"}.get(p["status"],"❓")
                text += f"{st} #{p['id']} | {p['user_id']} | {p['product_key']} | {format_price(p['amount'])}\n"
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "adm_undelivered":
        if not is_admin(user_id): return
        pays = db.get_undelivered_payments()
        if not pays:
            text = "✅ Все товары выданы!"
        else:
            text = "📦 <b>Невыданные:</b>\n\n"
            for p in pays:
                prod = get_product_info(p["category"], p["product_key"])
                text += f"#{p['id']} | {p['user_id']} | {prod['name'] if prod else p['product_key']} | {format_price(p['amount'])}\n"
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "adm_confirm":
        if not is_admin(user_id): return
        context.user_data["admin_awaiting"] = "confirm_id"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
        await query.edit_message_text("Введите ID платежа (#) для подтверждения оплаты:",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return ADMIN_MANUAL_ID

    elif data == "adm_deliver":
        if not is_admin(user_id): return
        context.user_data["admin_awaiting"] = "deliver_id"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
        await query.edit_message_text("Введите ID платежа (#) для выдачи товара:",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return ADMIN_MANUAL_ID

    elif data == "adm_promos":
        if not is_admin(user_id): return
        promos = db.get_all_promos()
        text = "🎟 <b>Промокоды:</b>\n\n"
        if promos:
            for p in promos:
                act = "✅" if p["is_active"] else "❌"
                uses = f"{p['current_uses']}/{p['max_uses']}" if p["max_uses"] != -1 else f"{p['current_uses']}/∞"
                text += f"{act} <code>{p['code']}</code> — {p['discount_percent']}% ({uses})\n"
        else:
            text += "Нет промокодов.\n"
        text += "\nДля создания введите: <code>КОД СКИДКА% МАКС</code>\nПример: <code>SALE20 20 100</code>"
        context.user_data["admin_awaiting"] = "add_promo"
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return ADMIN_ADD_PROMO

    elif data == "adm_broadcast":
        if not is_admin(user_id): return
        context.user_data["admin_awaiting"] = "broadcast"
        kb = [[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]]
        await query.edit_message_text("📢 Введите текст рассылки (HTML):",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return ADMIN_BROADCAST

    elif data == "adm_balance":
        if not is_admin(user_id): return
        bal = await YooMoneyPayment.get_balance()
        text = f"💰 Баланс: {f'{bal:.2f} ₽' if bal else 'Н/Д'}"
        kb = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    return MAIN_MENU


async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    awaiting = context.user_data.get("admin_awaiting")
    user_id = update.effective_user.id

    if awaiting == "confirm_id":
        try:
            rid = int(update.message.text.strip().replace("#", ""))
        except:
            await update.message.reply_text("❌ Введите число"); return ADMIN_MANUAL_ID
        p = db.get_payment_by_row_id(rid)
        if not p:
            await update.message.reply_text("❌ Не найден"); return ADMIN_MANUAL_ID
        if p["status"] == "success":
            await update.message.reply_text("✅ Уже подтверждён"); return ADMIN_MANUAL_ID
        db.update_payment_status(p["payment_id"], "success")
        db.update_user_spent(p["user_id"], p["amount"])
        db.admin_log(user_id, "confirm", f"#{rid}")
        try:
            prod = get_product_info(p["category"], p["product_key"])
            await context.bot.send_message(p["user_id"],
                f"✅ <b>Платёж #{rid} подтверждён!</b>\n📦 {prod['name'] if prod else p['product_key']}\n"
                f"💰 {format_price(p['amount'])}\n⏳ Товар скоро будет выдан!", parse_mode=ParseMode.HTML)
        except: pass
        await update.message.reply_text(f"✅ #{rid} подтверждён",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ", callback_data="admin_panel")]]))
        context.user_data["admin_awaiting"] = None
        return ADMIN_MENU

    elif awaiting == "deliver_id":
        try:
            rid = int(update.message.text.strip().replace("#", ""))
        except:
            await update.message.reply_text("❌ Введите число"); return ADMIN_MANUAL_ID
        p = db.get_payment_by_row_id(rid)
        if not p:
            await update.message.reply_text("❌ Не найден"); return ADMIN_MANUAL_ID
        if p["status"] != "success":
            await update.message.reply_text("⚠️ Не оплачен"); return ADMIN_MANUAL_ID
        if p["delivery_status"] == "delivered":
            await update.message.reply_text("✅ Уже выдан"); return ADMIN_MANUAL_ID
        db.mark_delivered(p["payment_id"], f"Admin {user_id}")
        db.admin_log(user_id, "deliver", f"#{rid}")
        try:
            prod = get_product_info(p["category"], p["product_key"])
            await context.bot.send_message(p["user_id"],
                f"🎉 <b>Товар выдан!</b>\n📦 {prod['name'] if prod else p['product_key']}\nСпасибо за покупку!",
                parse_mode=ParseMode.HTML)
        except: pass
        await update.message.reply_text(f"✅ #{rid} выдан",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ", callback_data="admin_panel")]]))
        context.user_data["admin_awaiting"] = None
        return ADMIN_MENU

    elif awaiting == "add_promo":
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("Формат: КОД СКИДКА% [МАКС]"); return ADMIN_ADD_PROMO
        code = parts[0].upper()
        try:
            disc = int(parts[1].replace("%",""))
        except:
            await update.message.reply_text("Скидка — число"); return ADMIN_ADD_PROMO
        mx = -1
        if len(parts) >= 3:
            try: mx = int(parts[2])
            except: pass
        if disc < 1 or disc > 99:
            await update.message.reply_text("Скидка 1-99%"); return ADMIN_ADD_PROMO
        ok = db.add_promo(code, disc, mx, created_by=user_id)
        if ok:
            db.admin_log(user_id, "add_promo", f"{code} {disc}% max:{mx}")
            await update.message.reply_text(f"✅ Промокод <code>{code}</code> создан ({disc}%)",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ", callback_data="admin_panel")]]))
        else:
            await update.message.reply_text("❌ Уже существует")
        context.user_data["admin_awaiting"] = None
        return ADMIN_MENU

    elif awaiting == "broadcast":
        text = update.message.text.strip()
        users = db.get_all_users()
        sent = failed = 0
        for u in users:
            try:
                await context.bot.send_message(u["user_id"], f"📢\n\n{text}", parse_mode=ParseMode.HTML)
                sent += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        db.admin_log(user_id, "broadcast", f"sent:{sent} fail:{failed}")
        await update.message.reply_text(f"📢 Отправлено: {sent}, ошибок: {failed}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Админ", callback_data="admin_panel")]]))
        context.user_data["admin_awaiting"] = None
        return ADMIN_MENU


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    active = db.get_user_active_payment(uid)
    if not active:
        await update.message.reply_text("✅ Нет активных платежей.")
        return
    ok, msg = await YooMoneyPayment.check_payment_by_label(active["payment_label"], active["amount"])
    if ok:
        db.update_payment_status(active["payment_id"], "success")
        db.update_user_spent(uid, active["amount"])
        prod = get_product_info(active["category"], active["product_key"])
        await update.message.reply_text(
            f"✅ <b>Оплата подтверждена!</b>\n📦 {prod['name'] if prod else active['product_key']}\n"
            f"💰 {format_price(active['amount'])}\n⏳ Товар скоро будет выдан!", parse_mode=ParseMode.HTML)
        for aid in ADMIN_IDS:
            try:
                await context.bot.send_message(aid,
                    f"💰 Оплата #{active['id']} подтверждена (/check)\n{uid} | {format_price(active['amount'])}",
                    parse_mode=ParseMode.HTML)
            except: pass
    else:
        await update.message.reply_text(f"⏳ Не оплачен. {msg}")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pays = db.get_user_payments(update.effective_user.id, 10)
    if not pays:
        await update.message.reply_text("📭 Покупок нет."); return
    text = "📜 <b>Покупки:</b>\n\n"
    for p in pays:
        st = {"success":"✅","pending":"⏳","expired":"❌","cancelled":"🚫"}.get(p["status"],"❓")
        prod = get_product_info(p["category"], p["product_key"])
        text += f"{st} #{p['id']} {prod['name'] if prod else p['product_key']} — {format_price(p['amount'])}\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>Помощь</b>\n\n/start — меню\n/check — проверить платёж\n/history — покупки\n\n"
        "Откройте магазин кнопкой в меню!", parse_mode=ParseMode.HTML)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа"); return
    await update.message.reply_text("👑 <b>Админ-панель</b>", reply_markup=get_admin_kb(),
                                    parse_mode=ParseMode.HTML)
    return ADMIN_MENU


# ==================== ФОНОВЫЕ ЗАДАЧИ ====================
async def background_checker(app):
    logger.info("Фоновая проверка запущена")
    while True:
        try:
            db.expire_payments()
            for p in db.get_pending_payments():
                try:
                    ok, msg = await YooMoneyPayment.check_payment_by_label(p["payment_label"], p["amount"])
                    if ok:
                        db.update_payment_status(p["payment_id"], "success")
                        db.update_user_spent(p["user_id"], p["amount"])
                        logger.info(f"Авто-подтверждение #{p['id']}")
                        prod = get_product_info(p["category"], p["product_key"])
                        try:
                            await app.bot.send_message(p["user_id"],
                                f"✅ <b>Платёж #{p['id']} подтверждён!</b>\n"
                                f"📦 {prod['name'] if prod else p['product_key']}\n"
                                f"⏳ Товар будет выдан!", parse_mode=ParseMode.HTML)
                        except: pass
                        for aid in ADMIN_IDS:
                            try:
                                await app.bot.send_message(aid,
                                    f"💰 Авто: #{p['id']} | {p['user_id']} | {format_price(p['amount'])}\n📦 Выдайте!",
                                    parse_mode=ParseMode.HTML)
                            except: pass
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка проверки {p['id']}: {e}")
        except Exception as e:
            logger.exception(f"Фоновая ошибка: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ==================== ЗАПУСК ====================
bot_application = None


async def on_startup(app_web):
    """Запуск бота и фоновых задач"""
    global bot_application

    bot_application = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(btn_handler,
                    pattern="^(back_main|my_orders|profile|referral|help_info|admin_panel|"
                            "adm_stats|adm_payments|adm_undelivered|adm_confirm|adm_deliver|"
                            "adm_promos|adm_broadcast|adm_balance)$"),
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(btn_handler,
                    pattern="^(back_main|admin_panel|adm_stats|adm_payments|adm_undelivered|"
                            "adm_confirm|adm_deliver|adm_promos|adm_broadcast|adm_balance)$"),
            ],
            ADMIN_MANUAL_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text),
                CallbackQueryHandler(btn_handler, pattern="^admin_panel$"),
            ],
            ADMIN_ADD_PROMO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text),
                CallbackQueryHandler(btn_handler, pattern="^admin_panel$"),
            ],
            ADMIN_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text),
                CallbackQueryHandler(btn_handler, pattern="^admin_panel$"),
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        per_user=True, per_chat=True,
    )

    bot_application.add_handler(conv)
    bot_application.add_handler(CommandHandler("check", cmd_check))
    bot_application.add_handler(CommandHandler("history", cmd_history))
    bot_application.add_handler(CommandHandler("help", cmd_help))
    bot_application.add_handler(CommandHandler("admin", cmd_admin))

    await bot_application.initialize()
    await bot_application.start()

    commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("check", "Проверить оплату"),
        BotCommand("history", "Мои покупки"),
        BotCommand("help", "Помощь"),
    ]
    await bot_application.bot.set_my_commands(commands)

    await bot_application.updater.start_polling(drop_pending_updates=True,
                                                 allowed_updates=["message", "callback_query"])

    asyncio.create_task(background_checker(bot_application))

    logger.info("🚀 Бот и веб-сервер запущены!")
    for aid in ADMIN_IDS:
        try:
            await bot_application.bot.send_message(aid, "🟢 Бот + Mini App запущены!")
        except: pass


async def on_shutdown(app_web):
    global bot_application
    if bot_application:
        await bot_application.updater.stop()
        await bot_application.stop()
        await bot_application.shutdown()
    logger.info("Бот остановлен")


def main():
    db.init_db()

    app_web = web.Application()
    app_web.on_startup.append(on_startup)
    app_web.on_shutdown.append(on_shutdown)
    app_web.router.add_routes(routes)

    logger.info(f"Запуск на {WEBAPP_HOST}:{WEBAPP_PORT}")
    web.run_app(app_web, host=WEBAPP_HOST, port=WEBAPP_PORT)


if __name__ == "__main__":
    main()
