import os
import telebot
import requests
from bs4 import BeautifulSoup
import pytz
import logging
from flask import Flask
import random
import hashlib
from deep_translator import GoogleTranslator
import re
from datetime import datetime, timedelta
from threading import Thread
import time

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk")
CHANNEL_ID = os.getenv("@Digital_Fund_1")
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

bot = telebot.TeleBot(TOKEN)
sent_posts = set()
is_scheduler_running = False

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        content = []

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
        rss_url = "https://cointelegraph.com/rss"
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml-xml')
        items = soup.select('item')[:20]

        if not items:
            logger.error("Empty RSS feed")
            return None

        for _ in range(3):
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
    """Безопасная отправка поста"""
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
        time.sleep(300)
        send_post()

def scheduler_loop():
    """Цикл планировщика"""
    global is_scheduler_running
    while True:
        now = datetime.now(MOSCOW_TZ)
        logger.info(f"Current time: {now.strftime('%H:%M')}")
        if 8 <= now.hour < 23 and now.minute == 0:
            logger.info("Sending post...")
            send_post()
            time.sleep(60)
        else:
            time.sleep(30)

@app.route('/')
def health_check():
    logger.info("Health check passed")
    return "Bot is operational", 200

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    global is_scheduler_running
    if not is_scheduler_running:
        is_scheduler_running = True
        logger.info("Starting scheduler thread")
        scheduler_thread = Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()

if __name__ == "__main__":
    log_system_info()
    run_scheduler()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
else:
    run_scheduler()
