import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from handlers import (
    start, product_callback, confirm_callback, check_payment_callback, cancel,
    SELECTING_PRODUCT, CONFIRMING, WAITING_PAYMENT
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Инициализация БД
    init_db()

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для процесса покупки
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
    )

    application.add_handler(conv_handler)

    # Обработчик команды /check (альтернативная проверка)
    async def check_command(update, context):
        # Можно реализовать проверку по последнему платежу
        await update.message.reply_text("Используйте кнопку 'Проверить оплату' после выбора товара.")
    application.add_handler(CommandHandler("check", check_command))

    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
