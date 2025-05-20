import os
import telebot
import requests
from bs4 import BeautifulSoup
import pytz
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import random
import hashlib
from deep_translator import GoogleTranslator
import re
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN", "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@Digital_Fund_1")
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)
sent_posts = set()

def log_system_info():
    """Логирование системной информации"""
    logger.info(f"System time: {datetime.now(MOSCOW_TZ)}")
    logger.info(f"Bot token: {'set' if TOKEN else 'not set'}")
    logger.info(f"Channel ID: {CHANNEL_ID}")

def enhance_translation(text):
    """Улучшение перевода криптотерминов"""
    term_map = {
        r'\bTaps\b': 'использует',
        r'\bYield\b': 'доходность',
        r'\bWallet\b': 'кошелек',
        r'\bDEFI\b': 'DeFi',
        r'\bNFT\b': 'NFT'
    }
    for pattern, replacement in term_map.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def get_article_content(url):
    """Получение содержимого статьи с улучшенной обработкой ошибок"""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content = []
        
        # Поиск основного контента
        main_selectors = [
            {'class': 'post-content'},
            {'itemprop': 'articleBody'},
            'article'
        ]
        
        for selector in main_selectors:
            elements = soup.find_all('div', selector) or soup.find_all('article', selector)
            if elements:
                for p in elements[0].find_all('p'):
                    text = p.get_text(strip=True)
                    if 50 < len(text) < 500:
                        content.append(text)
                if content:
                    return ' '.join(content[:6])
        
        logger.warning("Content not found")
        return None

    except Exception as e:
        logger.error(f"Content error: {str(e)}")
        return None

def prepare_post():
    """Подготовка поста с проверкой всех этапов"""
    try:
        # Получение новостей
        rss_url = "https://cointelegraph.com/rss"
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'xml')
        items = soup.select('item')[:20]
        
        if not items:
            logger.error("Empty RSS feed")
            return None

        # Выбор и обработка новости
        for _ in range(3):  # 3 попытки найти новую новость
            item = random.choice(items)
            title = GoogleTranslator(source='auto', target='ru').translate(item.title.text.strip())
            link = item.link.text.strip()
            
            post_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
            if post_hash in sent_posts:
                continue
                
            content = get_article_content(link)
            if not content:
                continue
                
            translated = enhance_translation(
                GoogleTranslator(source='auto', target='ru').translate(content[:2000])
            )
            
            # Форматирование
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', translated) if 30 < len(s) < 300]
            if len(sentences) < 3:
                continue
                
            post = (
                f"🚀 *{title}*\n\n" +
                '\n\n🔸 '.join(sentences[:4]) +
                f"\n\n🔗 [Читать полностью]({link})" +
                "\n#КриптоНовости #Аналитика"
            )
            
            sent_posts.add(post_hash)
            logger.info(f"New post prepared: {post_hash}")
            return post

        logger.warning("No new posts after 3 attempts")
        return None

    except Exception as e:
        logger.error(f"Prepare post error: {str(e)}")
        return None

def send_post():
    """Безопасная отправка поста с повтором"""
    try:
        post = prepare_post()
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Post sent at {datetime.now(MOSCOW_TZ).strftime('%H:%M')}")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")
        # Повторная попытка через 5 минут
        scheduler.add_job(
            send_post,
            'date',
            run_date=datetime.now(MOSCOW_TZ) + timedelta(minutes=5),
            id=f'retry_{datetime.now().timestamp()}'
        )

def init_scheduler():
    """Инициализация планировщика с проверкой"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
        
        # Очистка старых задач
        scheduler.remove_all_jobs()
        
        # Добавление почасовых задач
        for hour in range(8, 23):
            scheduler.add_job(
                send_post,
                'cron',
                hour=hour,
                minute=0,
                id=f'hour_{hour}'
            )
        logger.info(f"Added {23-8} hourly jobs (08:00-22:00 MSK)")
        
        # Тестовая отправка при старте
        scheduler.add_job(
            send_post,
            'date',
            run_date=datetime.now(MOSCOW_TZ) + timedelta(seconds=30),
            id='initial_test'
        )

@app.route('/')
def health_check():
    logger.info("Health check passed")
    return "Bot is operational", 200

if __name__ == "__main__":
    log_system_info()
    init_scheduler()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
