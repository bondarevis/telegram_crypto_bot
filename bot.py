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

# Загрузка конфигурации из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация (значения по умолчанию для тестирования)
API_ID = int(os.getenv("API_ID", 27952573))          # Получить на my.telegram.org
API_HASH = os.getenv("API_HASH", "1bca07bccb96a13a6cc2fa2ca54b063a")  # Ваш секретный хэш
BOT_TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
HISTORY_FILE = "/tmp/posted_urls.json"       # Для Render Persistent Storage
STARTUP_FLAG = "/tmp/first_run.flag"         # Флаг первого запуска

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

# Инициализация Telegram клиента
client = TelegramClient(None, API_ID, API_HASH)
lock = asyncio.Lock()  # Для предотвращения конкурентного доступа

def normalize_url(url: str) -> str:
    """Приводит URL к единому формату, удаляя параметры"""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))

async def load_history() -> set:
    """Загружает историю опубликованных URL"""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

async def save_history(urls: set):
    """Сохраняет историю в файл"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(list(urls), f)

async def safe_start() -> bool:
    """Безопасная инициализация бота"""
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
    """Отправляет сообщение только при первом запуске"""
    try:
        if not os.path.exists(STARTUP_FLAG):
            await client.send_message(
                CHANNEL_ID,
                "🤖 Бот активирован! Ожидайте новостей с 08:00 до 22:00 по МСК."
            )
            with open(STARTUP_FLAG, 'w') as f:
                f.write("1")
            logger.info("Стартовое сообщение отправлено")
    except Exception as e:
        logger.error(f"⚠️ Ошибка запуска: {str(e)}")

async def fetch_articles(session: aiohttp.ClientSession, source: dict):
    """Парсит статьи с указанного источника"""
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
                    articles.append({
                        'source': source['name'],
                        'title': title.text.strip(),
                        'url': full_url
                    })
            return articles
    except Exception as e:
        logger.error(f"🔧 Ошибка парсинга {source['name']}: {str(e)}")
        return []

async def publish_posts(articles: list, history: set):
    """Публикует новые статьи с защитой от дубликатов"""
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
                await asyncio.sleep(30)  # Задержка между публикациями
            except Exception as e:
                logger.error(f"❌ Ошибка публикации: {str(e)}")
    return new_urls

async def main_loop():
    """Основной рабочий цикл с расписанием"""
    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now()
            current_time = now.time()
            
            # Рабочее время: 08:00-22:00
            if time(8, 0) <= current_time <= time(22, 0):
                async with lock:  # Блокировка для конкурентного доступа
                    try:
                        history = await load_history()
                        total_new = 0
                        
                        # Парсинг и публикация для каждого источника
                        for source in NEWS_SOURCES:
                            articles = await fetch_articles(session, source)
                            new_urls = await publish_posts(articles, history)
                            total_new += len(new_urls)
                            history.update(new_urls)
                        
                        # Сохранение истории если есть новые статьи
                        if total_new > 0:
                            await save_history(history)
                        
                        logger.info(f"🔄 Опубликовано новых статей: {total_new}")
                        await asyncio.sleep(3600)  # Интервал 1 час
                        
                    except Exception as e:
                        logger.error(f"💥 Ошибка цикла: {str(e)}")
                        await asyncio.sleep(600)  # Повтор через 10 мин при ошибке
            else:
                # Расчет времени до следующего рабочего периода
                next_run = now.replace(
                    hour=8,
                    minute=0,
                    second=0,
                    microsecond=0
                ) + timedelta(days=1 if now.hour >= 22 else 0)
                
                delay = (next_run - now).total_seconds()
                logger.info(f"⏳ Следующая проверка в {next_run.strftime('%d.%m %H:%M')}")
                await asyncio.sleep(delay)

async def main():
    """Точка входа в приложение"""
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
