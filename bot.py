import os
import logging
import json
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask

app = Flask(__name__)

# Конфигурация
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
DATA_FILE = "posted_news.json"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_posted_news():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_posted_news(posted):
    with open(DATA_FILE, 'w') as f:
        json.dump(posted, f)

def get_crypto_news():
    logger.info("Начало парсинга новостей")
    url = "https://www.coindesk.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news = []
        for article in soup.find_all('article')[:10]:
            try:
                title = article.find('h2').text.strip()
                link = article.find('a')['href']
                time = article.find('time')['datetime']
                
                # Проверка на относительные ссылки
                if not link.startswith('http'):
                    link = f'https://www.coindesk.com{link}'
                    
                news.append({
                    'title': title,
                    'link': link,
                    'time': time
                })
            except Exception as e:
                logger.error(f"Ошибка парсинга статьи: {str(e)}")
        return news
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {str(e)}")
        return []

def post_news():
    logger.info("Запуск процедуры публикации")
    now = datetime.now()
    
    # Проверка времени публикации
    if 8 <= now.hour <= 22:
        bot = Bot(token=BOT_TOKEN)
        posted = load_posted_news()
        
        # Получение новостей
        news = get_crypto_news()
        
        for article in news:
            if article['title'] not in posted:
                # Форматирование сообщения
                message = (
                    f"📰 *{article['title']}*\n\n"
                    f"🔗 [Читать статью]({article['link']})\n"
                    f"🕒 {datetime.fromisoformat(article['time']).strftime('%d.%m.%Y %H:%M')}"
                )
                
                try:
                    # Публикация поста
                    bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Опубликован пост: {article['title']}")
                    
                    # Сохранение в истории
                    posted.append(article['title'])
                    save_posted_news(posted)
                    break
                except Exception as e:
                    logger.error(f"Ошибка публикации: {str(e)}")
                    continue

@app.route('/')
def home():
    return "Бот активен", 200

def run_scheduler():
    scheduler = BlockingScheduler()
    
    # Планировщик на каждый час с 08:00 до 22:00
    scheduler.add_job(
        post_news,
        trigger=CronTrigger(
            hour='8-22',
            minute=0,
            timezone='Europe/Moscow'
        )
    )
    
    # Немедленный запуск при старте
    try:
        post_news()
    except Exception as e:
        logger.error(f"Ошибка при стартовой публикации: {str(e)}")
    
    scheduler.start()

if __name__ == '__main__':
    logger.info("Запуск приложения")
    from threading import Thread
    Thread(target=run_scheduler).start()
    app.run(host='0.0.0.0', port=10000)
