import aiohttp
import uuid
import logging
from config import YOOMONEY_WALLET, YOOMONEY_ACCESS_TOKEN

logger = logging.getLogger(__name__)

async def create_payment(amount, product_name, user_id):
    """
    Создаёт платёж в ЮMoney.
    Возвращает (payment_id, confirmation_url) или (None, error_message).
    """
    payment_id = str(uuid.uuid4())
    label = f"payment_{user_id}_{payment_id}"

    url = "https://yoomoney.ru/api/request-payment"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "pattern_id": "p2p",
        "to": YOOMONEY_WALLET,
        "amount": str(amount),
        "comment": f"Покупка: {product_name}",
        "label": label,
        "test_payment": "true"  # Для тестов (в продакшене удалить или установить false)
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as resp:
                result = await resp.json()
                logger.info(f"Payment creation response: {result}")
                if result.get("status") == "success":
                    confirmation_url = result.get("confirmation_url")
                    return payment_id, confirmation_url
                else:
                    error = result.get("error", "Unknown error")
                    return None, f"Ошибка создания платежа: {error}"
        except Exception as e:
            logger.exception("Error creating payment")
            return None, f"Ошибка сети: {e}"

async def check_payment(payment_id):
    """
    Проверяет статус платежа.
    Возвращает True, если оплачен, иначе False.
    """
    url = "https://yoomoney.ru/api/check-payment"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "payment_id": payment_id
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=data) as resp:
                result = await resp.json()
                logger.info(f"Check payment response: {result}")
                return result.get("status") == "success"
        except Exception as e:
            logger.exception("Error checking payment")
            return False
