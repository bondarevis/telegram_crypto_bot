from flask import Flask
from telethon import TelegramClient, events
import logging
import os
from datetime import datetime, timedelta
from threading import Thread
import time
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ваши API данные
API_ID = 27952573  # Ваш api_id
API_HASH = '1bca07bccb96a13a6cc2fa2ca54b063a'  # Ваш api_hash
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"  # Ваш токен бота
CHANNEL_ID = "@Digital_Fund_1"  # ID вашего канала

# Список каналов для парсинга
SOURCE_CHANNELS = [
    "@RBCCrypto",
    "@DeCenter",
    "@cryptwit"
]

# Инициализация клиента
client = TelegramClient('session_name', API_ID, API_HASH)

app = Flask(__name__)

async def send_post(message):
    """Отправка поста"""
    try:
        await client.send_message(CHANNEL_ID, message)
        logger.info(f"Post sent at {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")
        time.sleep(300)
        await send_post(message)

async def parse_channels():
    """Парсинг каналов"""
    while True:
        now = datetime.now()
        logger.info(f"Current time: {now.strftime('%H:%M')}")
        if 8 <= now.hour < 23:
            for channel in SOURCE_CHANNELS:
                try:
                    async for message in client.iter_messages(channel, limit=1):
                        # Форматирование сообщения
                        formatted_message = format_message(message.text)
                        await send_post(formatted_message)
                except Exception as e:
                    logger.error(f"Error parsing channel {channel}: {str(e)}")
            time.sleep(3600)  # Ждем час перед следующей проверкой
        else:
            time.sleep(60)

def format_message(text):
    """Форматирование сообщения"""
    # Пример форматирования, вы можете изменить его в соответствии с вашими требованиями
    return text

@app.route('/')
def home():
    return "Hello, World!"

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    with client:
        client.loop.run_until_complete(parse_channels())

if __name__ == '__main__':
    # Запуск Flask приложения
    Thread(target=run_scheduler).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
