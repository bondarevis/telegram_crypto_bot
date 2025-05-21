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

# Хранилище опубликованных URL
posted_urls = set()

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

client = TelegramClient('crypto_news_bot', API_ID, API_HASH)
lock = asyncio.Lock()

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def send_startup_message():
    try:
        await client.send_message(
            CHANNEL_ID,
            "🚀 Бот успешно запущен!\n"
            "⏰ Режим работы: 08:00-22:00 по МСК"
        )
    except Exception as e:
        logger.error(f"Ошибка стартового сообщения: {str(e)}")

async def fetch_news(session, source):
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
                    
                    if article_url not in posted_urls:
                        articles.append({
                            'source': source['name'],
                            'title': title.text.strip(),
                            'url': article_url
                        })
                        posted_urls.add(article_url)
            return articles
    except Exception as e:
        logger.error(f"Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def post_article(article):
    try:
        message = (
            f"📌 **{article['source']}**\n"
            f"➖ {article['title']}\n"
            f"🔗 [Читать]({article['url']})"
        )
        await client.send_message(CHANNEL_ID, message, link_preview=False)
        logger.info(f"Опубликовано: {article['title'][:50]}...")
        await asyncio.sleep(10)  # Увеличенная задержка
    except Exception as e:
        logger.error(f"Ошибка публикации: {str(e)}")

async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            current_time = datetime.now().time()
            if time(8, 0) <= current_time <= time(22, 0):
                try:
                    logger.info("Начало цикла проверки...")
                    
                    for source in NEWS_SOURCES:
                        articles = await fetch_news(session, source)
                        for article in articles:
                            await post_article(article)
                    
                    await asyncio.sleep(3600)  # 1 час
                except Exception as e:
                    logger.error(f"Ошибка: {str(e)}")
                    await asyncio.sleep(300)
            else:
                await asyncio.sleep(1800)  # 30 минут

async def run_bot():
    await client.start(bot_token=TOKEN)
    await send_startup_message()
    await main_loop()

if __name__ == '__main__':
    try:
        with client:
            client.loop.run_until_complete(run_bot())
    except errors.FloodWaitError as e:
        logger.error(f"Требуется ожидание: {e.seconds} секунд")
        # Можно добавить автоматическое ожидание здесь
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
