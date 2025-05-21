import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from bs4 import BeautifulSoup
import aiohttp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"

# Хранилище URL
posted_urls = set()

NEWS_SOURCES = [...]  # Ваши источники

client = TelegramClient('bot_session', API_ID, API_HASH)

async def safe_start():
    """Безопасная инициализация бота"""
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("Успешная аутентификация")
        return True
    except errors.FloodWaitError as e:
        logger.error(f"Требуется ожидание: {e.seconds} сек.")
        await asyncio.sleep(e.seconds)
        return False
    except Exception as e:
        logger.error(f"Ошибка аутентификации: {str(e)}")
        return False

async def main():
    """Основная логика"""
    while True:
        if await safe_start():
            try:
                await client.send_message(CHANNEL_ID, "✅ Бот активирован")
                await monitoring_loop()
            except Exception as e:
                logger.error(f"Ошибка: {str(e)}")
                await client.disconnect()
                await asyncio.sleep(60)
        else:
            await asyncio.sleep(300)

if __name__ == '__main__':
    client.loop.run_until_complete(main())
