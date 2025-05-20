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

def enhance_translation(text):
    crypto_dict = {
        r'\bTaps\b': 'использует',
        r'\bпростоя\b': 'неиспользуемых',
        r'\bDEFI\b': 'DeFi',
        r'\bstaking\b': 'стейкинг',
        r'\bairdrop\b': 'эйрдроп'
    }
    for pattern, replacement in crypto_dict.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def translate_text(text):
    try:
        return enhance_translation(
            GoogleTranslator(source='auto', target='ru').translate(text)
        )
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text

def get_article_content(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = []
        for p in soup.select('div.post-content p, article p'):
            text = p.get_text(strip=True)
            if 50 < len(text) < 500:
                content.append(text)
        
        return translate_text(' '.join(content[:6])) if content else None
    except Exception as e:
        logger.error(f"Content error: {str(e)}")
        return None

def format_content(content):
    sentences = re.split(r'(?<=[.!?])\s+', content)
    return [s.strip() for s in sentences if 30 < len(s) < 300][:4]

def get_news():
    try:
        rss = requests.get("https://cointelegraph.com/rss", timeout=20).text
        soup = BeautifulSoup(rss, 'xml')
        
        news = []
        for item in soup.select('item')[:15]:
            title = translate_text(item.title.text.strip())
            link = item.link.text.strip()
            content = get_article_content(link)
            
            if not content:
                continue
                
            post_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
            if post_hash not in sent_posts:
                news.append({
                    'title': title,
                    'content': '\n\n🔸 '.join(format_content(content)),
                    'link': link,
                    'hash': post_hash
                })
        
        return news
    except Exception as e:
        logger.error(f"RSS error: {str(e)}")
        return []

def send_post():
    try:
        news = get_news()
        if not news:
            logger.warning("No new posts available")
            return
            
        post_data = random.choice(news)
        sent_posts.add(post_data['hash'])
        
        post = f"🚀 *{post_data['title']}*\n\n🔸 {post_data['content']}\n\n🔗 [Читать полностью]({post_data['link']})\n#КриптоНовости #Аналитика"
        bot.send_message(CHANNEL_ID, post, parse_mode="Markdown")
        logger.info(f"Post sent at {datetime.now(MOSCOW_TZ)}")
        
    except Exception as e:
        logger.error(f"Sending error: {str(e)}")

@app.route('/')
def health_check():
    logger.info("Health check received")
    return "Bot is active", 200

def init_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
        
        # Clear old jobs
        scheduler.remove_all_jobs()
        
        # Add hourly jobs 08:00-22:00
        for hour in range(8, 23):
            scheduler.add_job(
                send_post,
                'cron',
                hour=hour,
                minute=0,
                id=f'hour_{hour}'
            )
        logger.info(f"Added {23-8} hourly jobs")

if __name__ == "__main__":
    init_scheduler()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
