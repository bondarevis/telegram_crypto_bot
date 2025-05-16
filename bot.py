import os
import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup
import random
import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Проверка обязательных переменных
REQUIRED_ENV_VARS = ['TELEGRAM_TOKEN', 'TELEGRAM_CHANNEL', 'CMC_API_KEY']
for var in REQUIRED_ENV_VARS:
    if os.getenv(var) is None:
        logger.error(f'Не задана обязательная переменная окружения: {var}')
        exit(1)

# Инициализация Flask
app = Flask(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.environ['8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk']  # Используем os.environ вместо os.getenv для строгой проверки
TELEGRAM_CHANNEL = os.environ['@Digital_Fund_1']
CMC_API_KEY = os.environ['6316a41d-db32-4e49-a2a3-b66b96c663bf']
REQUEST_TIMEOUT = 15
PORT = int(os.getenv('PORT', 10000))

# Инициализация бота
try:
    bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    exit(1)

@app.route('/')
def health_check():
    return "Crypto Bot is Running", 200

# ... (остальные функции оставить без изменений, как в предыдущем коде)

if __name__ == "__main__":
    try:
        # Запуск планировщика в отдельном потоке
        scheduler_thread = threading.Thread(target=schedule_posts, daemon=True)
        scheduler_thread.start()
        
        # Запуск Flask-сервера
        threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=PORT),
            daemon=True
        ).start()
        
        # Запуск бота
        logger.info("Запуск основного цикла бота")
        run_bot()
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        exit(1)
