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
    """Профессиональная постобработка перевода"""
    crypto_dict = {
        r'\bTaps\b': 'использует',
        r'\bпростоя\b': 'неиспользуемых',
        r'\bодабок\b': 'решений',
        r'\bDEFI\b': 'DeFi',
        r'\bхолостое время\b': 'периоды простоя',
        r'\bзарплату\b': 'заработную плату',
        r'\bконсервативные запасы\b': 'резервные средства'
    }
    
    for pattern, replacement in crypto_dict.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text)
    return text

def translate_text(text):
    try:
        translated = GoogleTranslator(source='auto', target='ru').translate(text)
        return enhance_translation(translated)
    except Exception as e:
        logger.error(f"Ошибка перевода: {str(e)}")
        return text

def extract_meaningful_content(soup):
    """Извлечение ключевого контента"""
    content = []
    
    selectors = [
        {'class': ['article__content', 'post-content']},
        {'itemprop': 'articleBody'},
        'article'
    ]
    
    for selector in selectors:
        main_content = soup.find('div', selector) or soup.find('article', selector)
        if main_content:
            for p in main_content.find_all('p'):
                text = p.get_text(strip=True)
                if 50 < len(text) < 500 and not re.search(r'(?:http|@|©|Спонсор)', text):
                    content.append(text)
            if content:
                return ' '.join(content[:6])
    
    return None

def get_post_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US;q=0.9, ru;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        raw_content = extract_meaningful_content(soup)
        if not raw_content:
            return None
        
        translated = translate_text(raw_content[:2000])
        sentences = re.split(r'(?<=[.!?])\s+', translated)
        return [s for s in sentences if 30 < len(s) < 300][:5]
    
    except Exception as e:
        logger.error(f"Ошибка контента: {str(e)}")
        return None

def format_post(blocks):
    """Чистое форматирование поста"""
    formatted = [f"🔸 {block.strip()}" for block in blocks if block.strip()]
    return '\n\n'.join(formatted)

def get_crypto_news():
    try:
        url = "https://cointelegraph.com/rss"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(response.text, 'xml')
        
        news = []
        for item in soup.select('item')[:15]:
            try:
                title = translate_text(item.title.text.strip())
                link = item.link.text.strip()
                content_blocks = get_post_content(link)
                
                if not content_blocks or len(content_blocks) < 3:
                    continue
                
                post_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                
                if post_hash not in sent_posts:
                    news.append({
                        'title': title,
                        'content': format_post(content_blocks),
                        'link': link,
                        'hash': post_hash
                    })
            except Exception as e:
                logger.error(f"Ошибка новости: {str(e)}")
        
        return news
    
    except Exception as e:
        logger.error(f"Ошибка RSS: {str(e)}")
        return []

def prepare_post():
    try:
        news = get_crypto_news()
        if not news:
            return None
        
        post_data = random.choice(news)
        sent_posts.add(post_data['hash'])
        
        post = f"🚀 *{post_data['title']}*\n\n"
        post += f"{post_data['content']}\n\n"
        post += f"🔗 [Читать полный отчет]({post_data['link']})\n"
        post += "\n#КриптоНовости #Финансы #Блокчейн"
        
        return post
    
    except Exception as e:
        logger.error(f"Ошибка подготовки: {str(e)}")
        return None

def send_daily_post():
    try:
        post = prepare_post()
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info("Успешная публикация")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    """Почасовая публикация с 08:00 до 22:00"""
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
    
    for hour in range(8, 23):
        scheduler.add_job(
            send_daily_post,
            'cron',
            hour=hour,
            minute=0,
            id=f'hourly_{hour}'
        )

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

def initialize():
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Планировщик активирован")

initialize()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
