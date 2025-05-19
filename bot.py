import os
import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup
import logging
from flask import Flask
import pytz

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
CMC_API_KEY = "6316a41d-db32-4e49-a2a3-b66b96c663bf"
REQUEST_TIMEOUT = 30
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
PORT = int(os.getenv('PORT', 10000))

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)

@app.route('/')
def health_check():
    return "Crypto Bot is Running", 200

def get_current_time():
    return datetime.datetime.now(MOSCOW_TZ)

def fetch_market_data():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()["data"]
        
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e12, 2)
        volume_24h = round(data["quote"]["USD"]["total_volume_24h"] / 1e9, 2)
        
        return (
            "📊 *Рыночная статистика*\n\n"
            f"• Общая капитализация: ${total_market_cap}T\n"
            f"• Доминация BTC: {btc_dominance}%\n"
            f"• Объем за 24ч: ${volume_24h}B\n"
            f"• Данные: CoinMarketCap"
        )
    except Exception as e:
        logger.error(f"Ошибка CoinMarketCap: {str(e)}")
        return "🔴 Данные о рынке временно недоступны"

def parse_rbc_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.js-news-feed-item:not(.news-feed__item--hidden)')
        if not article:
            return None
            
        title = article.select_one('.news-feed__item__title').text.strip()
        link = article['href']
        
        # Парсинг полного текста
        article_response = requests.get(link, headers=headers, timeout=REQUEST_TIMEOUT)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        content = '\n'.join([p.text.strip() for p in article_soup.select('.article__text p')[:5]])
        
        return {
            'title': title,
            'content': content[:2000] + '...' if len(content) > 2000 else content,
            'source': 'РБК Крипто',
            'link': link
        }
    except Exception as e:
        logger.error(f"Ошибка РБК Крипто: {str(e)}")
        return None

def generate_market_post():
    try:
        market_data = fetch_market_data()
        return f"{market_data}\n\n#Рынок #Статистика"
    except Exception as e:
        logger.error(f"Ошибка генерации поста: {str(e)}")
        return None

def generate_news_post(news_item):
    try:
        return (
            f"📰 *{news_item['title']}*\n\n"
            f"{news_item['content']}\n\n"
            f"🔍 Источник: {news_item['source']}\n"
            f"🔗 [Читать полностью]({news_item['link']})\n\n"
            "#Новости #Аналитика"
        )
    except Exception as e:
        logger.error(f"Ошибка генерации новости: {str(e)}")
        return None

def send_post(post):
    try:
        if not post:
            return
            
        bot.send_message(
            chat_id=CHANNEL_ID,
            text=post,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info("Пост успешно отправлен")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def schedule_tasks():
    logger.info("Настройка расписания...")
    
    # Рыночная статистика в 08:00 и 22:00
    schedule.every().day.at("08:00").do(lambda: send_post(generate_market_post()))
    schedule.every().day.at("22:00").do(lambda: send_post(generate_market_post()))
    
    # Новости РБК Крипто каждый час с 09:00 до 21:00
    for hour in range(9, 22):
        schedule.every().day.at(f"{hour:02d}:00").do(
            lambda: send_post(generate_news_post(parse_rbc_crypto()))
        )

def run_scheduler():
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка планировщика: {str(e)}")
            time.sleep(10)

if __name__ == "__main__":
    # Настройка временной зоны
    os.environ['TZ'] = 'Europe/Moscow'
    time.tzset()
    
    # Инициализация планировщика
    schedule_tasks()
    
    # Запуск Flask
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Запуск планировщика
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("🤖 Бот успешно запущен с новым расписанием")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
