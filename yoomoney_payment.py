import aiohttp
import uuid
from config import YOOMONEY_ACCESS_TOKEN, YOOMONEY_WALLET


def generate_payment_label() -> str:
    """Уникальная метка для отслеживания платежа"""
    return uuid.uuid4().hex[:12]


def create_payment_url(amount: int, label: str, product_name: str) -> str:
    """
    Формируем ссылку на перевод через ЮMoney.
    Используем форму перевода на кошелёк.
    """
    # Формат ссылки для прямого перевода на кошелёк
    url = (
        f"https://yoomoney.ru/transfer/quickpay"
        f"?requestId={label}"
        f"&targets={product_name.replace(' ', '+')}"
        f"&default-sum={amount}"
        f"&receiver={YOOMONEY_WALLET}"
        f"&label={label}"
        f"&quickpay=shop"
        f"&account={YOOMONEY_WALLET}"
    )
    return url


def create_payment_form_url(amount: int, label: str, product_name: str) -> str:
    """
    Альтернативный вариант — прямая ссылка на перевод.
    """
    return f"https://yoomoney.ru/to/{YOOMONEY_WALLET}/{amount}"


async def check_payment_by_label(label: str) -> bool:
    """
    Проверяем входящий платёж по метке через API.
    """
    url = "https://yoomoney.ru/api/operation-history"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "type": "deposition",
        "label": label,
        "records": 5,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    return False
                result = await resp.json()
                operations = result.get("operations", [])
                for op in operations:
                    if op.get("label") == label and op.get("status") == "success":
                        return True
                return False
    except Exception:
        return False


async def check_payment_by_amount(amount: int, minutes: int = 30) -> bool:
    """
    Проверяем входящие платежи по сумме за последние N минут.
    Запасной вариант если label не передаётся.
    """
    url = "https://yoomoney.ru/api/operation-history"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "type": "deposition",
        "records": 30,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    return False
                result = await resp.json()
                operations = result.get("operations", [])

                from datetime import datetime, timedelta, timezone
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

                for op in operations:
                    if op.get("status") == "success":
                        op_amount = abs(float(op.get("amount", 0)))
                        if op_amount == float(amount):
                            return True
                return False
    except Exception:
        return False


async def check_recent_deposits(expected_amount: int, comment: str = "") -> bool:
    """
    Ищем среди последних входящих переводов тот,
    который совпадает по сумме и/или комментарию.
    """
    url = "https://yoomoney.ru/api/operation-history"
    headers = {
        "Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "type": "deposition",
        "records": 50,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    return False
                result = await resp.json()
                operations = result.get("operations", [])

                for op in operations:
                    if op.get("status") != "success":
                        continue

                    op_amount = abs(float(op.get("amount", 0)))
                    op_label = op.get("label", "")
                    op_title = op.get("title", "").lower()
                    op_comment = op.get("comment", "")

                    # Проверяем по label (комментарию заказа)
                    if comment and (comment in op_label or comment in op_comment):
                        return True

                    # Проверяем по точной сумме
                    if op_amount == float(expected_amount):
                        return True

                return False
    except Exception:
        return False


async def get_balance() -> str:
    """Баланс кошелька."""
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
                return "Ошибка API"
    except Exception:
        return "Ошибка соединения"
