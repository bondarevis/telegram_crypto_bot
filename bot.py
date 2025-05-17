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
from googletrans import Translator

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
translator = Translator()

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)

@app.route('/')
def health_check():
    return "Crypto Bot is Running", 200

def get_current_time():
    return datetime.datetime.now(MOSCOW_TZ)

def parse_rbc_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
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
        logger.error(f"RBK Crypto error: {str(e)}")
        return None

def parse_yahoo_crypto():
    try:
        url = "https://finance.yahoo.com/topic/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('li.js-stream-content')
        title = article.select_one('h3').text.strip()
        link = article.find('a')['href']
        
        # Перевод контента
        translated_title = translator.translate(title, dest='ru').text
        content = translator.translate(article.select_one('p').text, dest='ru').text
        
        return {
            'title': translated_title,
            'content': content[:2000] + '...' if len(content) > 2000 else content,
            'source': 'Yahoo Finance',
            'link': f"https://finance.yahoo.com{link}"
        }
    except Exception as e:
        logger.error(f"Yahoo Finance error: {str(e)}")
        return None

def parse_beincrypto():
    try:
        url = "https://ru.beincrypto.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.listingArticle')
        title = article.select_one('.title').text.strip()
        link = article.find('a')['href']
        
        # Парсинг полного текста
        article_response = requests.get(link, headers=headers, timeout=REQUEST_TIMEOUT)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        content = '\n'.join([p.text.strip() for p in article_soup.select('.article-content p')[:5]])
        
        return {
            'title': title,
            'content': content[:2000] + '...' if len(content) > 2000 else content,
            'source': 'BeInCrypto',
            'link': link
        }
    except Exception as e:
        logger.error(f"BeInCrypto error: {str(e)}")
        return None

def parse_tradingview():
    try:
        url = "https://ru.tradingview.com/news-flow/?market=crypto"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.card-EoF7qPjG')
        title = article.select_one('.title-GrnlXkDQ').text.strip()
        link = f"https://ru.tradingview.com{article['href']}"
        content = article.select_one('.description-GrnlXkDQ').text.strip()
        
        return {
            'title': title,
            'content': content[:2000] + '...' if len(content) > 2000 else content,
            'source': 'TradingView',
            'link': link
        }
    except Exception as e:
        logger.error(f"TradingView error: {str(e)}")
        return None

def generate_post(news_item):
    try:
        return (
            f"📰 *{news_item['title']}*\n\n"
            f"{news_item['content']}\n\n"
            f"🔍 Источник: {news_item['source']}\n"
            f"🔗 [Читать полностью]({news_item['link']})\n\n"
            "#Криптовалюта #Новости #Аналитика"
        )
    except Exception as e:
        logger.error(f"Post generation error: {str(e)}")
        return None

def send_post(news_item):
    try:
        if not news_item:
            return
            
        post = generate_post(news_item)
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Пост от {news_item['source']} успешно отправлен")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def schedule_tasks():
    logger.info("Настройка расписания...")
    
    # Расписание публикаций
    schedule_config = {
        '09:00': parse_rbc_crypto,
        '10:00': parse_yahoo_crypto,
        '11:00': parse_beincrypto,
        '12:00': parse_tradingview,
        '13:00': parse_rbc_crypto,
        '14:00': parse_yahoo_crypto,
        '15:00': parse_beincrypto,
        '16:00': parse_tradingview,
        '17:00': parse_rbc_crypto,
        '18:00': parse_yahoo_crypto,
        '19:00': parse_beincrypto,
        '20:00': parse_tradingview
    }

    for time_str, parser in schedule_config.items():
        schedule.every().day.at(time_str).do(
            lambda p=parser: send_post(p())
        ).tag('news')

    logger.info(f"Активные задачи: {schedule.get_jobs()}")

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
