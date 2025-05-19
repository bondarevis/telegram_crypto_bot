import os
import telebot
import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import random
import hashlib
from deep_translator import GoogleTranslator

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

def translate_text(text):
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        logger.error(f"Ошибка перевода: {str(e)}")
        return text

def get_post_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Парсинг основного содержимого
        content = ""
        main_content = soup.find('div', class_='post-content')
        if main_content:
            paragraphs = main_content.find_all('p')[:5]
            content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])
        
        return content[:1000] + '...' if content else "Читать полностью по ссылке"
    except Exception as e:
        logger.error(f"Ошибка парсинга контента: {str(e)}")
        return ""

def get_crypto_news():
    try:
        url = "https://cointelegraph.com/rss"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'xml')
        
        news = []
        for item in soup.select('item')[:10]:
            try:
                title = translate_text(item.title.text.strip())
                link = item.link.text.strip()
                content = translate_text(get_post_content(link))
                
                # Генерируем уникальный хеш для поста
                post_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                
                if post_hash not in sent_posts:
                    news.append({
                        'title': title,
                        'content': content,
                        'link': link,
                        'hash': post_hash
                    })
            except Exception as e:
                logger.error(f"Ошибка обработки новости: {str(e)}")
        
        return news
    except Exception as e:
        logger.error(f"Ошибка парсинга RSS: {str(e)}")
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
        post += f"[Читать полностью]({post_data['link']})\n\n"
        post += "#Криптовалюта #Новости #Аналитика"
        
        return post
    except Exception as e:
        logger.error(f"Ошибка подготовки поста: {str(e)}")
        return None

def send_daily_post():
    try:
        post = prepare_post()
        if post:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=post,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            logger.info(f"Успешная отправка поста")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    schedule_times = ['09:00', '14:00', '17:00', '20:00', '20:30', '21:00']
    
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
    
    for time_str in schedule_times:
        hour, minute = map(int, time_str.split(':'))
        scheduler.add_job(
            send_daily_post,
            'cron',
            hour=hour,
            minute=minute,
            id=f'job_{time_str}'
        )

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

def initialize():
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Планировщик успешно запущен")

initialize()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
