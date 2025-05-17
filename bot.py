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
from googletrans import Translator  # Добавлен переводчик

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
translator = Translator()  # Инициализация переводчика

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)

# ... [остальные функции из предыдущего кода] ...

def parse_forklog():
    try:
        url = "https://forklog.com/news"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.post_item:not(.media_pt)')
        if not article:
            return None
            
        title = article.select_one('.post_title').text.strip()
        link = article.find('a')['href']
        if not link.startswith('http'):
            link = f"https://forklog.com{link}"
            
        return {
            'title': title,
            'content': parse_forklog_article(link),
            'source': 'ForkLog',
            'link': link
        }
    except Exception as e:
        logger.error(f"ForkLog error: {str(e)}")
        return None

def parse_forklog_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = ' '.join([p.text.strip() for p in soup.select('.post_content p')[:3]])
        return f"{content[:400]}..." if content else "Читать далее ➡️"
    except:
        return "Читать далее ➡️"

def parse_yahoo_crypto():
    try:
        url = "https://finance.yahoo.com/topic/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('li.js-stream-content')
        if not article:
            return None
            
        title = article.select_one('h3').text.strip()
        link = article.find('a')['href']
        if not link.startswith('http'):
            link = f"https://finance.yahoo.com{link}"
            
        # Перевод контента
        translated = translator.translate(title, src='en', dest='ru').text
        return {
            'title': f"[Перевод] {translated}",
            'content': translate_yahoo_content(link),
            'source': 'Yahoo Finance',
            'link': link
        }
    except Exception as e:
        logger.error(f"Yahoo error: {str(e)}")
        return None

def translate_yahoo_content(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = ' '.join([p.text.strip() for p in soup.select('.caas-body p')[:2]])
        return translator.translate(content[:500], src='en', dest='ru').text + "..."
    except:
        return "Читать оригинал ➡️"

def parse_beincrypto():
    try:
        url = "https://ru.beincrypto.com/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.listingArticle')
        if not article:
            return None
            
        title = article.select_one('.title').text.strip()
        link = article.find('a')['href']
        return {
            'title': title,
            'content': parse_beincrypto_article(link),
            'source': 'BeInCrypto',
            'link': link
        }
    except Exception as e:
        logger.error(f"BeInCrypto error: {str(e)}")
        return None

def parse_beincrypto_article(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = ' '.join([p.text.strip() for p in soup.select('.article-content p')[:3]])
        return f"{content[:400]}..." if content else "Читать далее ➡️"
    except:
        return "Читать далее ➡️"

def fetch_news(source):
    try:
        time.sleep(2)  # Задержка между источниками
        if source == "rbc":
            return parse_rbc_news()
        elif source == "tradingview":
            return parse_tradingview_news()
        elif source == "forklog":
            return parse_forklog()
        elif source == "yahoo":
            return parse_yahoo_crypto()
        elif source == "beincrypto":
            return parse_beincrypto()
        return None
    except Exception as e:
        logger.error(f"News fetch error ({source}): {str(e)}")
        return None

def schedule_tasks():
    logger.info("Инициализация расписания...")
    
    # Рыночные отчеты
    schedule.every().day.at("08:00").do(lambda: send_post(generate_daily_report())).tag('reports')
    schedule.every().day.at("22:00").do(lambda: send_post(generate_daily_report())).tag('reports')
    
    # Новости с ротацией источников
    sources = ['rbc', 'tradingview', 'forklog', 'yahoo', 'beincrypto']
    for hour in range(9, 22):
        source = sources[(hour-9) % len(sources)]  # Ротация источников
        schedule.every().day.at(f"{hour:02d}:00").do(
            lambda s=source: post_news_update(s)
        ).tag('news')

def post_news_update(source):
    try:
        logger.info(f"🚀 Запуск новостной задачи для {source} в {get_current_time().strftime('%H:%M:%S')}")
        news_item = fetch_news(source)
        if news_item:
            post = generate_news_post(news_item)
            if post:
                send_post(post, is_news=True)
        else:
            logger.warning(f"Новости из {source} не получены")
    except Exception as e:
        logger.error(f"Ошибка в задаче {source}: {str(e)}")

# ... [остальные функции остаются без изменений] ...

if __name__ == "__main__":
    # Настройка временной зоны
    os.environ['TZ'] = 'Europe/Moscow'
    time.tzset()
    
    # Инициализация планировщика
    schedule_tasks()
    
    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("🤖 Бот запущен с новыми источниками")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
