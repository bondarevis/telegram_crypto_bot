from flask import Flask
from telethon import TelegramClient, events
import logging
import os
from datetime import datetime, timedelta
from threading import Thread
import time

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

# Инициализация клиента
client = TelegramClient('session_name', API_ID, API_HASH)

app = Flask(__name__)

async def send_post():
    """Отправка поста"""
    try:
        # Пример отправки сообщения в канал
        await client.send_message(CHANNEL_ID, "Пример сообщения")
        logger.info(f"Post sent at {datetime.now().strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")
        time.sleep(300)
        await send_post()

async def main():
    await client.start()
    logger.info("Client created and started")

    # Отправка поста сразу после запуска
    await send_post()

    # Запуск планировщика
    while True:
        now = datetime.now()
        logger.info(f"Current time: {now.strftime('%H:%M')}")
        if 8 <= now.hour < 23 and now.minute == 0:
            logger.info("Sending post...")
            await send_post()
            time.sleep(60)
        else:
            time.sleep(30)

@app.route('/')
def home():
    return "Hello, World!"

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    with client:
        client.loop.run_until_complete(main())

if __name__ == '__main__':
    # Запуск Flask приложения
    Thread(target=run_scheduler).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
