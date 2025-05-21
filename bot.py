import os
import logging
import asyncio
import json
from datetime import datetime, time, timedelta
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from telethon import TelegramClient
from bs4 import BeautifulSoup
import aiohttp

# Загрузка конфигурации
load_dotenv()

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
HISTORY_FILE = "posted_urls.json"

# Список источников для парсинга
NEWS_SOURCES = [
    {
        "name": "Cointelegraph",
        "url": "https://cointelegraph.com/",
        "selectors": {
            "articles": "div.posts-listing__item",
            "title": "span.posts-listing__title",
            "link": "a.posts-listing__item__permalink"
        }
    },
    {
        "name": "Coindesk",
        "url": "https://www.coindesk.com/",
        "selectors": {
            "articles": "div.main-body section div.card",
            "title": "div.card-title a",
            "link": "div.card-title a"
        }
    }
]

# Инициализация Telegram клиента
client = TelegramClient('crypto_news_bot', API_ID, API_HASH).start(bot_token=TOKEN)
lock = asyncio.Lock()  # Блокировка для предотвращения параллельных выполнений

def normalize_url(url):
    """Нормализация URL с удалением параметров"""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def load_history():
    """Загрузка истории опубликованных URL"""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {source['name']: [] for source in NEWS_SOURCES}

async def save_history(history):
    """Сохранение истории в файл"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

async def send_startup_message():
    """Отправка сообщения при запуске"""
    try:
        await client.send_message(
            CHANNEL_ID,
            "🚀 Бот запущен! Мониторинг крипто-новостей активирован.\n"
            "⏰ Расписание работы: ежечасно с 08:00 до 22:00"
        )
        logger.info("Стартовое сообщение отправлено")
    except Exception as e:
        logger.error(f"Ошибка отправки стартового сообщения: {str(e)}")

async def fetch_news(session, source):
    """Парсинг новостей с сайта"""
    try:
        async with session.get(source['url']) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')
            
            articles = []
            for item in soup.select(source['selectors']['articles']):
                title = item.select_one(source['selectors']['title'])
                link = item.select_one(source['selectors']['link'])
                
                if title and link:
                    raw_url = link['href']
                    article_url = normalize_url(
                        raw_url if raw_url.startswith('http') 
                        else source['url'] + raw_url.lstrip('/')
                    )
                    
                    articles.append({
                        'source': source['name'],
                        'title': title.text.strip(),
                        'url': article_url
                    })
            return articles
    except Exception as e:
        logger.error(f"Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def post_to_channel(article):
    """Форматирование и отправка поста"""
    try:
        message = (
            f"📰 **{article['source']}**\n"
            f"🔹 *{article['title']}*\n"
            f"📎 [Читать статью]({article['url']})\n"
            f"⏳ {datetime.now().strftime('%H:%M %d.%m.%Y')}"
        )
        await client.send_message(CHANNEL_ID, message, link_preview=False)
        logger.info(f"Опубликовано: {article['title'][:50]}...")
        return True
    except Exception as e:
        logger.error(f"Ошибка публикации: {str(e)}")
        return False

async def scheduled_parser():
    """Планировщик с улучшенной защитой от дубликатов"""
    history = await load_history()
    last_articles = {source['name']: set(history.get(source['name'], [])) for source in NEWS_SOURCES}
    
    async with aiohttp.ClientSession() as session:
        while True:
            async with lock:  # Блокировка выполнения
                current_time = datetime.now().time()
                if time(8, 0) <= current_time <= time(22, 0):
                    try:
                        logger.info("Начало цикла парсинга...")
                        
                        for source in NEWS_SOURCES:
                            articles = await fetch_news(session, source)
                            new_articles = [
                                a for a in articles
                                if a['url'] not in last_articles[source['name']]
                            ]
                            
                            for article in new_articles:
                                success = await post_to_channel(article)
                                if success:
                                    last_articles[source['name']].add(article['url'])
                                    await asyncio.sleep(5)
                            
                            logger.info(f"{source['name']}: новых статей {len(new_articles)}")
                        
                        await save_history({k: list(v) for k, v in last_articles.items()})
                        await asyncio.sleep(3600)
                    
                    except Exception as e:
                        logger.error(f"Ошибка в основном цикле: {str(e)}")
                        await asyncio.sleep(300)
                else:
                    now = datetime.now()
                    next_run = now.replace(hour=8, minute=0, second=0)
                    if now.hour >= 22:
                        next_run += timedelta(days=1)
                    wait_seconds = (next_run - now).total_seconds()
                    logger.info(f"Не рабочее время. Следующая проверка в {next_run.strftime('%H:%M')}")
                    await asyncio.sleep(wait_seconds)

async def main():
    """Основная функция"""
    await client.start()
    await send_startup_message()
    await scheduled_parser()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
