import os
import telebot
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import random

# Инициализация Flask приложения
app = Flask(__name__)

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Инициализация планировщика
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)

def get_coin_news():
    """Парсинг новостей с CoinDesk"""
    try:
        url = "https://www.coindesk.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        for item in soup.select('.heading-v5 a')[:5]:
            title = item.text.strip()
            link = "https://www.coindesk.com" + item['href']
            news.append(f"• {title}\n{link}")
        return news
    except Exception as e:
        logger.error(f"Ошибка парсинга: {str(e)}")
        return None

def prepare_post():
    """Формирование поста"""
    try:
        news = get_coin_news()
        if not news:
            return None
            
        post = "📰 *Свежие крипто-новости*\n\n"
        post += random.choice(news)
        post += "\n\n#Новости #Криптовалюта"
        return post
    except Exception as e:
        logger.error(f"Ошибка подготовки поста: {str(e)}")
        return None

def send_daily_post():
    """Отправка поста"""
    try:
        post = prepare_post()
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            logger.info(f"Пост отправлен в {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    """Расписание"""
    schedule_times = ['09:00', '14:00', '17:00', '20:00']
    
    for time_str in schedule_times:
        hour, minute = map(int, time_str.split(':'))
        scheduler.add_job(
            send_daily_post,
            'cron',
            hour=hour,
            minute=minute
        )

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

# Инициализация планировщика при старте
def initialize():
    setup_scheduler()
    scheduler.start()

if __name__ == "__main__":
    initialize()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
