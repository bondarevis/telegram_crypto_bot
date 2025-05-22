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
HISTORY_FILE = "/tmp/posted_urls.json"  # Путь для Render Persistent Storage

NEWS_SOURCES = [...]  # Ваши источники без изменений

client = TelegramClient(None, API_ID, API_HASH)
lock = asyncio.Lock()

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

async def save_history(urls):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(list(urls), f)

async def safe_start():
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Auth success")
        return True
    except errors.FloodWaitError as e:
        logger.error(f"⏳ Flood wait: {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return False
    except Exception as e:
        logger.error(f"🚨 Auth error: {str(e)}")
        return False

async def send_start_message():
    try:
        if not await client.is_connected():
            await client.connect()
        
        # Проверка последнего сообщения
        last_msg = await client.get_messages(CHANNEL_ID, limit=1)
        if not last_msg or "активирован" not in last_msg[0].text:
            await client.send_message(CHANNEL_ID, "🚀 Бот успешно запущен!")
    except Exception as e:
        logger.error(f"⚠️ Startup error: {str(e)}")

async def fetch_and_publish(session):
    posted_urls = await load_history()
    new_urls = set()
    
    for source in NEWS_SOURCES:
        try:
            async with session.get(source['url']) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                
                for item in soup.select(source['selectors']['articles']):
                    title = item.select_one(source['selectors']['title'])
                    link = item.select_one(source['selectors']['link'])
                    
                    if title and link:
                        url = normalize_url(link['href'])
                        if url not in posted_urls:
                            message = f"📌 {title.text.strip()}\n🔗 {url}"
                            await client.send_message(CHANNEL_ID, message)
                            new_urls.add(url)
                            await asyncio.sleep(30)  # Задержка между постами
        except Exception as e:
            logger.error(f"🔧 Error processing {source['name']}: {str(e)}")
    
    if new_urls:
        await save_history(posted_urls | new_urls)

async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now()
            if time(8, 0) <= now.time() <= time(22, 0):
                async with lock:
                    await fetch_and_publish(session)
                    await asyncio.sleep(3600)  # Каждый час
            else:
                # Расчет времени до 08:00
                next_run = now.replace(hour=8, minute=0, second=0) + timedelta(days=1 if now.hour >= 22 else 0)
                delay = (next_run - now).total_seconds()
                logger.info(f"⏳ До следующей проверки: {delay//3600} ч.")
                await asyncio.sleep(delay)

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(safe_start())
        client.loop.run_until_complete(send_start_message())
        client.loop.run_until_complete(main_loop())
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
    finally:
        client.loop.run_until_complete(client.disconnect())
