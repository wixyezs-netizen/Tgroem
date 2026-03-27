import logging
from config import ADMIN_ID   # на всякий случай, если понадобится

logger = logging.getLogger(__name__)

async def deliver_premium(user_id):
    logger.info(f"Выдача премиума пользователю {user_id}")
    # Здесь реальная интеграция
    return True, "Telegram Premium активирован на 1 месяц. Наслаждайтесь!"

async def deliver_stars(user_id, amount):
    stars = amount * 2   # пример
    logger.info(f"Выдача {stars} звёзд пользователю {user_id}")
    return True, f"На ваш счёт зачислено {stars} звёзд."

async def deliver_nft(user_id):
    logger.info(f"Выдача NFT пользователю {user_id}")
    return True, "Ваше NFT отправлено на кошелёк. Ссылка: https://opensea.io/..."
