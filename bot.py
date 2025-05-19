import telebot
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import random

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
PORT = 10000

# Инициализация
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)

def get_coin_news():
    """Парсинг свежих новостей с CoinDesk"""
    try:
        url = "https://www.coindesk.com/livewire/"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        for item in soup.select('.card-title a')[:5]:
            title = item.text.strip()
            link = "https://www.coindesk.com" + item['href']
            news.append(f"• {title}\n{link}")
        
        return news
    except Exception as e:
        logger.error(f"Ошибка парсинга: {str(e)}")
        return None

def get_crypto_updates():
    """Парсинг последних обновлений с CoinTelegraph"""
    try:
        url = "https://cointelegraph.com/rss"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'xml')
        
        updates = []
        for item in soup.select('item')[:5]:
            title = item.title.text.strip()
            link = item.link.text.strip()
            updates.append(f"• {title}\n{link}")
        
        return updates
    except Exception as e:
        logger.error(f"Ошибка парсинга: {str(e)}")
        return None

def prepare_post():
    """Формирование поста из случайной новости"""
    try:
        sources = [get_coin_news, get_crypto_updates]
        random_source = random.choice(sources)()
        
        if not random_source:
            return "🔧 Сегодня технические неполадки. Попробуйте позже."
            
        post = "📰 *Свежие крипто-новости*\n\n"
        post += random.choice(random_source)[:1000]
        post += "\n\n#КриптоНовости #Актуальное"
        return post
    except Exception as e:
        logger.error(f"Ошибка подготовки поста: {str(e)}")
        return None

def send_daily_post():
    """Отправка поста в канал"""
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
    """Настройка расписания"""
    schedule = {
        '09:00': 'утренний выпуск',
        '14:00': 'дневной выпуск',
        '17:00': 'вечерний выпуск', 
        '20:00': 'итоги дня'
    }
    
    for time_str, _ in schedule.items():
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

if __name__ == "__main__":
    setup_scheduler()
    scheduler.start()
    
    # Запуск Flask
    app.run(host='0.0.0.0', port=PORT)
