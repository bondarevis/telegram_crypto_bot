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
from bs4 import NavigableString
import threading

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
post_lock = threading.Lock()

def enhance_translation(text):
    """Улучшение перевода для криптотерминов"""
    term_map = {
        r'\bairdrop\b': 'эйрдроп',
        r'\bstaking\b': 'стейкинг',
        r'\bgas fee\b': 'комиссия сети',
        r'\bwhitepaper\b': 'технический документ',
        r'\bflash loan\b': 'мгновенный займ',
        r'\byield farming\b': 'фермерство доходности'
    }
    for pattern, replacement in term_map.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def translate_text(text):
    try:
        translated = GoogleTranslator(source='auto', target='ru').translate(text)
        return enhance_translation(translated)
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text

def extract_content(soup):
    """Извлечение основного контента статьи"""
    content_selectors = [
        {'class': 'post-content'},
        {'itemprop': 'articleBody'},
        {'class': 'article__content'},
        'article'
    ]
    
    for selector in content_selectors:
        main_content = soup.find('div', selector) or soup.find('article', selector)
        if main_content:
            paragraphs = [p.get_text(strip=True) for p in main_content.find_all('p')]
            return ' '.join(paragraphs[:8])
    return None

def get_post_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = extract_content(soup)
        if not content:
            return None
            
        translated = translate_text(content[:2500])
        sentences = re.split(r'(?<=[.!?])\s+', translated)
        return [s.strip() for s in sentences if 50 < len(s) < 300][:5]
    except Exception as e:
        logger.error(f"Content error: {str(e)}")
        return None

def format_post(blocks):
    """Форматирование поста с нумерацией"""
    return '\n\n'.join([f"🔹 {b}" for b in blocks[:4]])

def get_fresh_news():
    """Получение и фильтрация новых статей"""
    try:
        rss_url = "https://cointelegraph.com/rss"
        response = requests.get(rss_url, timeout=20)
        soup = BeautifulSoup(response.text, 'xml')
        
        news_items = []
        for item in soup.select('item')[:20]:
            try:
                title = translate_text(item.title.text.strip())
                link = item.link.text.strip()
                content = get_post_data(link)
                
                if not content or len(content) < 3:
                    continue
                
                post_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                
                if post_hash not in sent_posts:
                    news_items.append({
                        'title': title,
                        'content': format_post(content),
                        'link': link,
                        'hash': post_hash
                    })
            except Exception as e:
                logger.error(f"News processing error: {str(e)}")
        
        return news_items
    except Exception as e:
        logger.error(f"RSS error: {str(e)}")
        return []

def prepare_unique_post():
    """Подготовка уникального поста с блокировкой"""
    with post_lock:
        news = get_fresh_news()
        if not news:
            logger.warning("No new posts available")
            return None
            
        post_data = random.choice(news)
        if post_data['hash'] in sent_posts:
            return None
            
        sent_posts.add(post_data['hash'])
        logger.info(f"New post prepared: {post_data['hash']}")
        
        return (
            f"🚀 *{post_data['title']}*\n\n"
            f"{post_data['content']}\n\n"
            f"🔗 [Полная версия статьи]({post_data['link']})\n"
            "#КриптоНовости #Аналитика #Блокчейн"
        )

def send_scheduled_post():
    """Безопасная отправка поста"""
    try:
        post = prepare_unique_post()
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Post sent at {datetime.datetime.now(MOSCOW_TZ).isoformat()}")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")

def setup_scheduler():
    """Настройка почасового расписания"""
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
        logger.info("Cleared existing jobs")
    
    for hour in range(8, 23):
        scheduler.add_job(
            send_scheduled_post,
            'cron',
            hour=hour,
            minute=0,
            id=f'hourly_{hour}',
            misfire_grace_time=300
        )
    logger.info(f"Scheduled {23-8} hourly jobs")

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

def initialize():
    if not scheduler.running:
        scheduler.start()
        setup_scheduler()
        logger.info("Scheduler initialized")

if __name__ == "__main__":
    initialize()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
