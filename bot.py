import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from bs4 import BeautifulSoup
import aiohttp

load_dotenv()

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

# Хранилище URL
posted_urls = set()

# Источники новостей
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

# Инициализация клиента
client = TelegramClient('news_bot_session', API_ID, API_HASH)

def normalize_url(url):
    """Нормализация URL"""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def send_start_message():
    """Отправка стартового сообщения"""
    try:
        await client.send_message(
            CHANNEL_ID,
            "🤖 Бот активирован!\n"
            "⌚ Режим работы: 08:00-22:00 МСК"
        )
    except Exception as e:
        logger.error(f"Ошибка стартового уведомления: {str(e)}")

async def fetch_articles(session, source):
    """Парсинг статей"""
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
                    full_url = normalize_url(
                        raw_url if raw_url.startswith('http') 
                        else f"{source['url']}{raw_url.lstrip('/')}"
                    )
                    
                    if full_url not in posted_urls:
                        articles.append({
                            'source': source['name'],
                            'title': title.text.strip(),
                            'url': full_url
                        })
                        posted_urls.add(full_url)
            return articles
    except Exception as e:
        logger.error(f"Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def publish_post(article):
    """Публикация поста"""
    try:
        message = (
            f"📣 **{article['source']}**\n"
            f"▫️ {article['title']}\n"
            f"🔗 [Источник]({article['url']})"
        )
        await client.send_message(CHANNEL_ID, message, link_preview=False)
        logger.info(f"Успешно: {article['title'][:50]}...")
        await asyncio.sleep(15)  # Задержка для предотвращения флуда
    except errors.FloodWaitError as e:
        logger.error(f"Требуется пауза: {e.seconds} сек.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Ошибка публикации: {str(e)}")

async def monitoring_loop():
    """Основной цикл"""
    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now().time()
            if time(8, 0) <= now <= time(22, 0):
                try:
                    logger.info("Запуск проверки источников...")
                    
                    for source in NEWS_SOURCES:
                        articles = await fetch_articles(session, source)
                        for article in articles:
                            await publish_post(article)
                    
                    await asyncio.sleep(3600)  # Интервал 1 час
                except Exception as e:
                    logger.error(f"Ошибка цикла: {str(e)}")
                    await asyncio.sleep(600)
            else:
                # Расчет времени до следующего рабочего периода
                next_run = datetime.now().replace(hour=8, minute=0, second=0)
                if datetime.now().hour >= 22:
                    next_run += timedelta(days=1)
                delay = (next_run - datetime.now()).total_seconds()
                logger.info(f"Ожидание до {next_run.strftime('%H:%M')}")
                await asyncio.sleep(delay)

async def main():
    """Точка входа"""
    await client.start(bot_token=TOKEN)
    await send_start_message()
    await monitoring_loop()

if __name__ == '__main__':
    try:
        with client:
            client.loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Фатальная ошибка: {str(e)}")
