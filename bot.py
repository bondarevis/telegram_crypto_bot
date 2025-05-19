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
    """Профессиональное улучшение перевода"""
    crypto_terms = {
        r'\bBTC\b': 'BTC',
        r'\bblockchain\b': 'блокчейн',
        r'\bmalware\b': 'вредоносное ПО',
        r'\bmining\b': 'майнинг',
        r'\bwallet\b': 'криптокошелек',
        r'\bhash rate\b': 'хешрейт',
        r'\bnode\b': 'нода',
        r'\bdecentralized\b': 'децентрализованный',
        r'\bexchange\b': 'биржа',
        r'\bprivate key\b': 'приватный ключ'
    }
    
    # Замена терминов
    for term, replacement in crypto_terms.items():
        text = re.sub(term, replacement, text, flags=re.IGNORECASE)
    
    # Улучшение грамматики
    improvements = {
        r'(\s)наряду(\s)': r'\1параллельно\2',
        r'загрузили скомпрометированное': 'распространили взломанное',
        r'полный сброс системы': 'полная переустановка системы',
        r'глобального загрузки': 'глобального распространения'
    }
    
    for pattern, replacement in improvements.items():
        text = re.sub(pattern, replacement, text)
    
    return text

def translate_text(text):
    """Многоуровневый перевод с постобработкой"""
    try:
        # Первичный перевод
        translated = GoogleTranslator(source='auto', target='ru').translate(text)
        
        # Улучшение перевода
        enhanced = enhance_translation(translated)
        
        # Коррекция окончаний
        enhanced = re.sub(r'(\b\w+)ые(\b)', r'\1ые\2', enhanced)
        enhanced = re.sub(r'(\b\w+)ие(\b)', r'\1ие\2', enhanced)
        
        return enhanced
    
    except Exception as e:
        logger.error(f"Ошибка перевода: {str(e)}")
        return text

def extract_meaningful_content(soup):
    """Извлечение ключевых данных статьи"""
    content = []
    
    # Основные селекторы для крипто-новостей
    selectors = [
        {'class': ['post-content', 'article__content']},
        {'itemprop': 'articleBody'},
        {'class': 'content'},
        'article'
    ]
    
    for selector in selectors:
        main_content = soup.find('div', selector) or soup.find('article', selector)
        if main_content:
            paragraphs = []
            for p in main_content.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 100 and not re.search(r'(?:http|@|©|Следите за обновлениями)', text):
                    paragraphs.append(text)
            if paragraphs:
                return ' '.join(paragraphs[:8])  # Берем первые 8 значимых абзацев
    
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
        
        # Перевод и улучшение
        translated = translate_text(raw_content[:2500])
        
        # Разделение на логические блоки
        blocks = re.split(r'(?<=[.!?])\s+', translated)
        
        # Фильтрация и объединение
        meaningful_blocks = [
            b for b in blocks 
            if 50 < len(b) < 350 
            and not re.search(r'(?:http|@|реклама|спонсор)', b, re.I)
        ]
        
        return meaningful_blocks[:5]  # Не более 5 блоков
    
    except Exception as e:
        logger.error(f"Ошибка обработки контента: {str(e)}")
        return None

def format_post(blocks):
    """Профессиональное форматирование поста"""
    formatted = []
    
    for i, block in enumerate(blocks, 1):
        # Удаление лишних пробелов
        block = re.sub(r'\s+', ' ', block).strip()
        
        # Первое предложение жирным
        if i == 1:
            formatted.append(f"**{block}**")
        else:
            # Маркировка пунктов
            formatted.append(f"🔸 {block}")
        
        # Добавляем абзац после каждых двух пунктов
        if i % 2 == 0 and i != len(blocks):
            formatted.append("")
    
    return '\n\n'.join(formatted)

def get_crypto_news():
    try:
        url = "https://cointelegraph.com/rss"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(response.text, 'xml')
        
        news = []
        for item in soup.select('item')[:10]:
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
                logger.error(f"Ошибка обработки: {str(e)}")
        
        return news
    
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {str(e)}")
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
        post += "\n#КриптоНовости #Безопасность #Блокчейн"
        
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
            logger.info("Пост отправлен успешно")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    schedule_times = ['09:00', '14:00', '17:00', '20:00', '20:30', '21:00', '21:30']
    
    if scheduler.get_jobs():
        scheduler.remove_all_jobs()
    
    for time_str in schedule_times:
        hour, minute = map(int, time_str.split(':'))
        scheduler.add_job(
            send_daily_post,
            'cron',
            hour=hour,
            minute=minute,
            id=f'job_{time_str.replace(":", "")}'
        )

@app.route('/')
def health_check():
    return "Crypto News Bot Active", 200

def initialize():
    if not scheduler.running:
        setup_scheduler()
        scheduler.start()
        logger.info("Планировщик инициализирован")

initialize()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
