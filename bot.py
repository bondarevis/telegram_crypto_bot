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
TOKEN = os.getenv("TELEGRAM_TOKEN", "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Digital_Fund_1")
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Инициализация планировщика
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)

def get_crypto_news():
    """Парсинг новостей с CoinTelegraph"""
    try:
        url = "https://cointelegraph.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        # Парсинг главных новостей
        for article in soup.select('article')[:5]:
            title = article.find('span', {'class': 'post__title'})
            if title:
                title = title.text.strip()
                link = article.find('a')['href']
                if not link.startswith('http'):
                    link = f"https://cointelegraph.com{link}"
                news.append(f"• {title}\n{link}")
        
        # Если новостей мало, используем RSS
        if len(news) < 3:
            rss_url = "https://cointelegraph.com/rss"
            rss_response = requests.get(rss_url, headers=headers, timeout=20)
            rss_soup = BeautifulSoup(rss_response.text, 'xml')
            
            for item in rss_soup.select('item')[:5]:
                title = item.title.text.strip()
                link = item.link.text.strip()
                news.append(f"• {title}\n{link}")
        
        return news
    
    except Exception as e:
        logger.error(f"Ошибка парсинга: {str(e)}", exc_info=True)
        return None

def prepare_post():
    """Генерация поста"""
    try:
        news = get_crypto_news()
        if not news:
            return None
            
        post = "🚀 *Свежие крипто-новости*\n\n"
        post += random.choice(news)
        post += f"\n\n📅 _Время публикации: {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')}_\n#Криптовалюта #Новости"
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
                disable_web_page_preview=True
            )
            logger.info(f"Успешная отправка в {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    """Настройка расписания"""
    schedule_times = ['09:00', '14:00', '17:00', '20:00', '20:30']
    
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
    
    for idx, time_str in enumerate(schedule_times):
        hour, minute = map(int, time_str.split(':'))
        scheduler.add_job(
            send_daily_post,
            'cron',
            hour=hour,
            minute=minute,
            id=f'job_{idx}'
        )

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

def initialize():
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Планировщик успешно запущен")

# Инициализация при старте
initialize()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
