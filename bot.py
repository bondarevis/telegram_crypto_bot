import os
import logging
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.utils.helpers import escape_markdown
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
import pytz

app = Flask(__name__)

# Конфигурация
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
DATA_FILE = "posted_news.json"
TIMEZONE = pytz.timezone('Europe/Moscow')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

def load_posted_news():
    try:
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w') as f:
                json.dump([], f)
            logger.info("Создан новый файл истории")
            return []
            
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {str(e)}")
        return []

def save_posted_news(posted):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(posted, f, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения истории: {str(e)}")

def get_crypto_news():
    logger.info("Начало парсинга новостей")
    url = "https://www.coindesk.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        news = []
        
        # Актуальные селекторы для мая 2024
        articles = soup.select('div[data-testid="river"] article, div.article-cardstyles__AcContainer-sc-q1x8lc-0')
        
        for article in articles[:15]:
            try:
                # Извлечение данных с проверкой элементов
                title_elem = article.find('h2', {'data-testid': 'headline'})
                link_elem = article.find('a', href=True)
                time_elem = article.find('time')
                
                if not all([title_elem, link_elem, time_elem]):
                    continue
                
                title = title_elem.get_text(strip=True)
                link = link_elem['href']
                time = time_elem['datetime']
                
                # Корректировка ссылки
                if link.startswith('/'):
                    link = f'https://www.coindesk.com{link}'
                
                # Проверка дубликатов перед добавлением
                if not any(item['title'] == title for item in news):
                    news.append({
                        'title': title,
                        'link': link,
                        'time': time
                    })
                    logger.debug(f"Найдена статья: {title}")
                
            except Exception as e:
                logger.error(f"Ошибка парсинга статьи: {str(e)}")
        
        return news
    
    except Exception as e:
        logger.error(f"Ошибка запроса: {str(e)}")
        return []

def post_news():
    logger.info("Запуск процедуры публикации")
    now = datetime.now(TIMEZONE)
    
    if 8 <= now.hour <= 22:
        try:
            bot = Bot(token=BOT_TOKEN)
            posted = load_posted_news()
            news = get_crypto_news()
            
            if not news:
                logger.warning("Новости не найдены!")
                return
                
            for article in news:
                if article['title'] not in posted:
                    try:
                        article_time = datetime.fromisoformat(article['time']).astimezone(TIMEZONE)
                        
                        # Проверка свежести новости (не старше 24 часов)
                        if (now - article_time).total_seconds() > 86400:
                            logger.info(f"Пропущена устаревшая новость: {article['title']}")
                            continue
                            
                        # Формирование сообщения с экранированием
                        message = (
                            f"🔥 *{escape_markdown(article['title'], version=2)}*\n\n"
                            f"📖 [Читать статью]({escape_markdown(article['link'], version=2)})\n"
                            f"⏰ {article_time.strftime('%d.%m.%Y %H:%M')}"
                        )
                        
                        # Отправка сообщения
                        bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=message,
                            parse_mode='MarkdownV2'
                        )
                        logger.info(f"Успешно опубликовано: {article['title']}")
                        
                        # Обновление истории
                        posted.append(article['title'])
                        save_posted_news(posted)
                        return
                        
                    except Exception as e:
                        logger.error(f"Ошибка публикации: {str(e)}")
                        continue
                        
            logger.info("Нет новых новостей для публикации")
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}")
            raise

@app.route('/')
def home():
    return "🤖 Бот активен | Crypto News Channel", 200

def run_scheduler():
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    
    # Настройка расписания с обработкой пропущенных задач
    scheduler.add_job(
        post_news,
        trigger=CronTrigger(
            hour='8-22',
            minute=0,
            timezone=TIMEZONE
        ),
        misfire_grace_time=600,
        coalesce=True
    )
    
    # Первый запуск
    try:
        post_news()
    except Exception as e:
        logger.error(f"Стартовая ошибка: {str(e)}")
    
    scheduler.start()

if __name__ == '__main__':
    logger.info("🚀 Запуск приложения")
    from threading import Thread
    Thread(target=run_scheduler).start()
    app.run(host='0.0.0.0', port=10000)
