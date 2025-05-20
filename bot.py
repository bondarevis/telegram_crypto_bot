from flask import Flask
from telethon import TelegramClient, events
import logging
import os
from datetime import datetime, timedelta
from threading import Thread
import time
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

# Вывод значений переменных окружения для проверки
print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH}")
print(f"TOKEN: {TOKEN}")
print(f"CHANNEL_ID: {CHANNEL_ID}")

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
                        await send_post(message.text)
                except Exception as e:
                    logger.error(f"Error parsing channel {channel}: {str(e)}")
            time.sleep(3600)  # Ждем час перед следующей проверкой
        else:
            time.sleep(60)

@app.route('/')
def home():
    return "Hello, World!"

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    with client:
        client.loop.run_until_complete(parse_channels())

async def initial_post():
    """Отправка начального поста"""
    for channel in SOURCE_CHANNELS:
        try:
            async for message in client.iter_messages(channel, limit=1):
                await send_post(message.text)
                break  # Отправляем только одно сообщение
        except Exception as e:
            logger.error(f"Error sending initial post from channel {channel}: {str(e)}")

if __name__ == '__main__':
    # Запуск Flask приложения
    Thread(target=run_scheduler).start()
    port = int(os.environ.get('PORT', 10000))

    # Отправка начального поста сразу после запуска
    with client:
        client.loop.run_until_complete(initial_post())

    app.run(host='0.0.0.0', port=port)
