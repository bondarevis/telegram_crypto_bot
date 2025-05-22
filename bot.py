import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from telethon import TelegramClient
from bs4 import BeautifulSoup
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"

SOURCE_URL = "https://cointelegraph.com/"
SELECTORS = {
    "articles": "div.posts-listing__item",
    "title": "span.posts-listing__title",
    "link": "a.posts-listing__item__permalink"
}

client = TelegramClient('render_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def send_instant_post():
    """Отправляет тестовый пост сразу после запуска"""
    try:
        await client.send_message(CHANNEL_ID, "✅ Бот успешно активирован!")
        logger.info("Тестовый пост отправлен")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

async def get_latest_news():
    """Получает последнюю новость с сайта"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SOURCE_URL) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                article = soup.select_one(SELECTORS["articles"])
                
                if article:
                    title = article.select_one(SELECTORS["title"]).text.strip()
                    link = article.select_one(SELECTORS["link"])['href']
                    return f"📌 {title}\n🔗 {link}"
    except Exception as e:
        logger.error(f"Ошибка парсинга: {str(e)}")
    return None

async def scheduler():
    """Управляет расписанием публикаций"""
    await send_instant_post()
    last_post = None
    
    while True:
        now = datetime.now()
        current_time = now.time()
        
        # Проверка времени (08:00-22:00 МСК)
        if time(8, 0) <= current_time <= time(22, 0):
            # Проверяем последнюю публикацию
            if not last_post or (now - last_post).total_seconds() >= 3600:
                news = await get_latest_news()
                if news:
                    try:
                        await client.send_message(CHANNEL_ID, news)
                        logger.info("Пост опубликован")
                        last_post = now
                    except Exception as e:
                        logger.error(f"Ошибка публикации: {str(e)}")
                await asyncio.sleep(60)  # Проверка каждую минуту
            else:
                await asyncio.sleep(300)  # Проверка каждые 5 минут
        else:
            # Расчет времени до 08:00
            next_run = now.replace(hour=8, minute=0, second=0) + timedelta(days=1 if now.hour >= 22 else 0)
            delay = (next_run - now).total_seconds()
            logger.info(f"Следующий пост в {next_run.strftime('%H:%M')}")
            await asyncio.sleep(delay)

async def main():
    await client.start()
    await scheduler()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
