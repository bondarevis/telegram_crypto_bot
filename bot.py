from telethon import TelegramClient, events
import logging
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ваши API данные
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Список каналов для парсинга
SOURCE_CHANNELS = [
    "@RBCCrypto",
    "@DeCenter",
    "@cryptwit"
]

client = TelegramClient('session_name', API_ID, API_HASH).start(bot_token=TOKEN)

async def send_post(message):
    """Отправка поста"""
    try:
        logger.info(f"Attempting to send post: {message[:50]}...")
        await client.send_message(CHANNEL_ID, message)
        logger.info(f"Post sent at {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")
        await asyncio.sleep(300)
        await send_post(message)

async def parse_channels():
    """Парсинг каналов"""
    logger.info("Starting scheduler...")
    while True:
        try:
            now = datetime.now()
            logger.info(f"Current time: {now.strftime('%H:%M')}")
            
            # Отправка постов сразу при запуске
            if not hasattr(parse_channels, 'initial_run'):
                await initial_post()
                parse_channels.initial_run = True
            
            # Регулярная отправка по расписанию
            if 8 <= now.hour < 23:
                for channel in SOURCE_CHANNELS:
                    try:
                        logger.info(f"Parsing channel: {channel}")
                        async for message in client.iter_messages(channel, limit=1):
                            logger.info(f"Found message: {message.text[:50]}...")
                            await send_post(message.text)
                    except Exception as e:
                        logger.error(f"Error parsing channel {channel}: {str(e)}")
                await asyncio.sleep(3600)  # Ждем час
            else:
                await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Main loop error: {str(e)}")
            await asyncio.sleep(60)

async def initial_post():
    """Отправка начального поста"""
    logger.info("Sending initial posts...")
    for channel in SOURCE_CHANNELS:
        try:
            async for message in client.iter_messages(channel, limit=1):
                await send_post(message.text)
                break
        except Exception as e:
            logger.error(f"Initial post error for {channel}: {str(e)}")

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(parse_channels())
