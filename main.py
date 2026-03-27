import asyncio
import logging
import threading
import time
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config import BOT_TOKEN, CHECK_INTERVAL
from database import init_db, get_pending_payments, update_payment_status, mark_delivered
from yoomoney import check_payment
from handlers import (
    start, product_callback, confirm_callback, check_payment_callback, cancel,
    SELECTING_PRODUCT, CONFIRMING, WAITING_PAYMENT, help_command, history_command
)
from admin import admin_panel, admin_callback, handle_admin_message

# Настройка логирования в файл и консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Фоновая проверка платежей (запускается в отдельном потоке)
async def background_checker(application):
    while True:
        try:
            pending = get_pending_payments()
            for p in pending:
                # Проверяем каждый платеж
                success = await check_payment(p["payment_id"])
                if success:
                    update_payment_status(p["payment_id"], "success")
                    # Выдаём товар
                    from delivery import deliver_premium, deliver_stars, deliver_nft
                    user_id = p["user_id"]
                    product_key = p["product"]
                    # Определяем тип товара
                    from config import PRODUCTS
                    if product_key == "premium":
                        ok, msg = await deliver_premium(user_id)
                    elif product_key == "stars":
                        ok, msg = await deliver_stars(user_id, p["amount"])
                    elif product_key == "nft":
                        ok, msg = await deliver_nft(user_id)
                    else:
                        ok, msg = False, "Неизвестный товар"
                    if ok:
                        mark_delivered(p["payment_id"])
                        await application.bot.send_message(user_id, f"✅ Ваш платёж подтверждён! {msg}")
                    else:
                        # Сообщаем админу
                        await application.bot.send_message(
                            ADMIN_ID,
                            f"❗️ Автоматическая выдача не удалась для платежа {p['payment_id']}\nПользователь: {user_id}\nТовар: {product_key}\nОшибка: {msg}"
                        )
                # Небольшая пауза между запросами, чтобы не перегружать API
                await asyncio.sleep(1)
        except Exception as e:
            logger.exception("Ошибка в фоновом проверяльщике")
        await asyncio.sleep(CHECK_INTERVAL)

def run_background(loop, app):
    asyncio.set_event_loop(loop)
    loop.create_task(background_checker(app))
    loop.run_forever()

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для покупки
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_PRODUCT: [
                CallbackQueryHandler(product_callback, pattern="^(product_|cancel)$")
            ],
            CONFIRMING: [
                CallbackQueryHandler(confirm_callback, pattern="^(confirm|back_to_products)$")
            ],
            WAITING_PAYMENT: [
                CallbackQueryHandler(check_payment_callback, pattern="^check_payment$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True  # исправление предупреждения
    )
    application.add_handler(conv_handler)

    # Обычные команды
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("admin", admin_panel))

    # Админские callback'и
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    # Обработчик сообщений для админа (ручной ввод ID)
    application.add_handler(MessageHandler(filters.TEXT & filters.USER, handle_admin_message))

    # Запуск фонового проверяльщика в отдельном потоке
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=run_background, args=(loop, application), daemon=True)
    thread.start()

    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
