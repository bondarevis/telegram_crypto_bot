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
API_ID = int(os.getenv("API_ID", 27952573))
API_HASH = os.getenv("API_HASH", "1bca07bccb96a13a6cc2fa2ca54b063a")
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"

# Хранилище URL
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

# Инициализация клиента без файла сессии
client = TelegramClient(None, API_ID, API_HASH)

def normalize_url(url: str) -> str:
    """Нормализация URL-адресов"""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def safe_start():
    """Безопасная инициализация бота"""
    try:
        await client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Успешная аутентификация через бот-токен")
        return True
    except errors.FloodWaitError as e:
        logger.error(f"⏳ Требуется ожидание: {e.seconds} секунд")
        await asyncio.sleep(e.seconds)
        return False
    except Exception as e:
        logger.error(f"🚨 Критическая ошибка аутентификации: {str(e)}")
        return False

async def fetch_articles(session: aiohttp.ClientSession, source: dict):
    """Получение статей из источника"""
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
        logger.error(f"⚠️ Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def publish_post(article: dict):
    """Публикация поста с защитой от флуда"""
    try:
        message = (
            f"📌 **{article['source']}**\n"
            f"▫️ {article['title']}\n"
            f"🔗 [Читать статью]({article['url']})"
        )
        await client.send_message(CHANNEL_ID, message, link_preview=False)
        logger.info(f"📤 Успешно опубликовано: {article['title'][:50]}...")
        await asyncio.sleep(20)  # Задержка между постами
    except errors.FloodWaitError as e:
        logger.error(f"⏸️ Пауза из-за флуда: {e.seconds} сек.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"❌ Ошибка публикации: {str(e)}")

async def monitoring_loop():
    """Основной рабочий цикл"""
    async with aiohttp.ClientSession() as session:
        while True:
            current_time = datetime.now().time()
            if time(8, 0) <= current_time <= time(22, 0):
                try:
                    logger.info("🔄 Начало цикла проверки источников")
                    
                    for source in NEWS_SOURCES:
                        articles = await fetch_articles(session, source)
                        for article in articles:
                            await publish_post(article)
                    
                    logger.info("⏳ Следующая проверка через 1 час")
                    await asyncio.sleep(3600)
                except Exception as e:
                    logger.error(f"🔧 Ошибка в основном цикле: {str(e)}")
                    await asyncio.sleep(600)
            else:
                now = datetime.now()
                next_run = now.replace(hour=8, minute=0, second=0)
                if now.hour >= 22:
                    next_run += timedelta(days=1)
                delay = (next_run - now).total_seconds()
                logger.info(f"⏰ Режим ожидания до {next_run.strftime('%H:%M')}")
                await asyncio.sleep(delay)

async def main():
    """Точка входа приложения"""
    if await safe_start():
        try:
            await client.send_message(CHANNEL_ID, "🤖 Бот успешно активирован!")
            await monitoring_loop()
        except Exception as e:
            logger.error(f"🚨 Фатальная ошибка: {str(e)}")
        finally:
            await client.disconnect()
    else:
        logger.error("🛑 Не удалось инициализировать бота")

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("🔌 Принудительное завершение работы")
    except Exception as e:
        logger.error(f"💥 Необработанная ошибка: {str(e)}")
