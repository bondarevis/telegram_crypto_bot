import os
import logging
import asyncio
import json
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

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
HISTORY_FILE = "/tmp/posted_urls.json"

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

client = TelegramClient(None, API_ID, API_HASH)
lock = asyncio.Lock()

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def load_history() -> set:
    try:
        with open(HISTORY_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

async def save_history(urls: set):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(list(urls), f)

async def safe_start() -> bool:
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Успешная аутентификация")
        return True
    except errors.FloodWaitError as e:
        logger.error(f"⏳ Требуется ожидание: {e.seconds} сек.")
        await asyncio.sleep(e.seconds)
        return False
    except Exception as e:
        logger.error(f"🚨 Ошибка аутентификации: {str(e)}")
        return False

async def send_start_message():
    try:
        if not client.is_connected():  # Исправлено: убран await
            await client.connect()
        
        last_msg = await client.get_messages(CHANNEL_ID, limit=1)
        if not last_msg or "Бот активирован" not in last_msg[0].text:
            await client.send_message(CHANNEL_ID, "🚀 Бот активирован!")
    except Exception as e:
        logger.error(f"⚠️ Ошибка запуска: {str(e)}")

async def fetch_articles(session: aiohttp.ClientSession, source: dict):
    try:
        async with session.get(source['url']) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'lxml')
            articles = []
            
            for item in soup.select(source['selectors']['articles']):
                title = item.select_one(source['selectors']['title'])
                link = item.select_one(source['selectors']['link'])
                
                if title and link:
                    url = normalize_url(link['href'])
                    articles.append({
                        'source': source['name'],
                        'title': title.text.strip(),
                        'url': url
                    })
            return articles
    except Exception as e:
        logger.error(f"🔧 Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def publish_posts(articles: list, history: set):
    new_urls = set()
    for article in articles:
        if article['url'] not in history:
            try:
                message = (
                    f"📌 **{article['source']}**\n"
                    f"▫️ {article['title']}\n"
                    f"🔗 [Читать]({article['url']})"
                )
                await client.send_message(CHANNEL_ID, message, link_preview=False)
                new_urls.add(article['url'])
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"❌ Ошибка публикации: {str(e)}")
    return new_urls

async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            current_time = datetime.now().time()
            if time(8, 0) <= current_time <= time(22, 0):
                async with lock:
                    try:
                        history = await load_history()
                        total_new = 0
                        
                        for source in NEWS_SOURCES:
                            articles = await fetch_articles(session, source)
                            new_urls = await publish_posts(articles, history)
                            total_new += len(new_urls)
                            history.update(new_urls)
                        
                        if total_new > 0:
                            await save_history(history)
                        
                        logger.info(f"🔄 Найдено новых статей: {total_new}")
                        await asyncio.sleep(3600)
                    except Exception as e:
                        logger.error(f"💥 Ошибка цикла: {str(e)}")
                        await asyncio.sleep(600)
            else:
                now = datetime.now()
                next_run = now.replace(hour=8, minute=0, second=0)
                if now.hour >= 22:
                    next_run += timedelta(days=1)
                delay = (next_run - now).total_seconds()
                logger.info(f"⏳ До следующей проверки: {delay//3600:.1f} ч.")
                await asyncio.sleep(delay)

async def main():
    if await safe_start():
        await send_start_message()
        await main_loop()
    await client.disconnect()

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("🔌 Принудительное завершение работы")
    except Exception as e:
        logger.error(f"💣 Критическая ошибка: {str(e)}")
