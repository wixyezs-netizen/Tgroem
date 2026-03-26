import aiohttp
import uuid
from urllib.parse import urlencode
from config import YOOMONEY_ACCESS_TOKEN, YOOMONEY_WALLET


def generate_payment_label() -> str:
    """Уникальная метка для отслеживания платежа"""
    return f"order_{uuid.uuid4().hex[:12]}"


def create_payment_url(amount: int, label: str, product_name: str) -> str:
    """
    Создаём ссылку на оплату через ЮMoney (quickpay форма).
    amount — сумма в рублях (целое число).
    label — уникальная метка заказа.
    """
    base_url = "https://yoomoney.ru/quickpay/confirm"

    params = {
        "receiver": YOOMONEY_WALLET,
        "quickpay-form": "shop",
        "targets": product_name,
        "paymentType": "AC",  # AC = банк. карта, PC = кошелёк ЮMoney
        "sum": str(amount),
        "label": label,
        "successURL": "https://t.me",
    }

    return f"{base_url}?{urlencode(params)}"


async def check_payment_by_label(label: str) -> bool:
    """
    Проверяем, пришёл ли платёж с данной меткой через API ЮMoney.
    """
    url = "https://yoomoney.ru/api/operation-history"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "type": "deposition",
        "label": label,
        "records": 1,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    return False
                result = await resp.json()
                operations = result.get("operations", [])
                if operations:
                    for op in operations:
                        if op.get("label") == label and op.get("status") == "success":
                            return True
                return False
    except Exception:
        return False


async def get_balance() -> str:
    """Получить баланс кошелька (для админа)."""
    url = "https://yoomoney.ru/api/account-info"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return f"{result.get('balance', '?')} ₽"
                return "Ошибка"
    except Exception:
        return "Ошибка"
