import os
import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup
import logging
from flask import Flask
import pytz

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
CMC_API_KEY = "6316a41d-db32-4e49-a2a3-b66b96c663bf"
REQUEST_TIMEOUT = 25
PORT = int(os.getenv('PORT', 10000))
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)

@app.route('/')
def health_check():
    return "Crypto Bot is Running", 200

def get_current_time():
    return datetime.datetime.now(MOSCOW_TZ)

def fetch_market_data():
    try:
        # CoinGecko данные
        gecko_url = "https://api.coingecko.com/api/v3/global"
        gecko_response = requests.get(gecko_url, timeout=REQUEST_TIMEOUT)
        gecko_data = gecko_response.json()
        
        btc_dominance_gecko = round(gecko_data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap_gecko = round(gecko_data["data"]["total_market_cap"]["usd"] / 1e12, 2)

        # CoinMarketCap данные
        cmc_url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        cmc_headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        cmc_response = requests.get(cmc_url, headers=cmc_headers, timeout=REQUEST_TIMEOUT)
        cmc_data = cmc_response.json()["data"]
        
        btc_dominance_cmc = round(cmc_data["btc_dominance"], 2)
        total_market_cap_cmc = round(cmc_data["quote"]["USD"]["total_market_cap"] / 1e12, 2)

        return (
            "📊 *Рыночная статистика*\n\n"
            f"• Общая капитализация: ${(total_market_cap_gecko + total_market_cap_cmc)/2:.2f}T\n"
            f"• Средняя доминация BTC: {(btc_dominance_gecko + btc_dominance_cmc)/2:.2f}%\n"
            f"• Данные: CoinGecko & CoinMarketCap"
        )
    except Exception as e:
        logger.error(f"Market data error: {e}")
        return "🔴 Рыночные данные временно недоступны"

def parse_rbc_news():
    try:
        base_url = "https://www.rbc.ru"
        main_url = f"{base_url}/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(main_url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.js-news-feed-item')
        if not article:
            return None
            
        title = article.select_one('.news-feed__item__title').text.strip()
        link = article['href']
        description = parse_article_content(link)
        
        return {
            'title': title,
            'content': description,
            'source': 'RBK Crypto',
            'link': link if link.startswith('http') else base_url + link
        }
    except Exception as e:
        logger.error(f"RBK News error: {e}")
        return None

def parse_tradingview_news():
    try:
        url = "https://www.tradingview.com/news/cryptocurrencies/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article = soup.select_one('.news-item-card')
        if not article:
            return None
            
        title = article.select_one('.title').text.strip()
        link = "https://www.tradingview.com" + article['href']
        description = article.select_one('.description').text.strip()[:300] + "..."
        
        return {
            'title': title,
            'content': description,
            'source': 'TradingView',
            'link': link
        }
    except Exception as e:
        logger.error(f"TradingView News error: {e}")
        return None

def parse_article_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_blocks = soup.select('.article__text p')
        return ' '.join([p.text.strip() for p in content_blocks[:3]])[:400] + "..."
    except Exception as e:
        logger.error(f"Article parsing error: {e}")
        return "Читать полную версию статьи ➡️"

def generate_daily_report():
    try:
        time_now = get_current_time().strftime("%d.%m.%Y %H:%M")
        market_data = fetch_market_data()
        
        return (
            f"🌍 *Ежедневный рыночный отчет* ({time_now})\n\n"
            f"{market_data}\n\n"
            "#Рынок #Статистика #Аналитика"
        )
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return None

def generate_news_post(news_item):
    try:
        time_now = get_current_time().strftime("%d.%m.%Y %H:%M")
        return (
            f"📰 *Крипто-новости* ({time_now})\n\n"
            f"🏷 *{news_item['title']}*\n"
            f"{news_item['content']}\n\n"
            f"🔍 Источник: {news_item['source']}\n"
            f"🔗 [Читать полностью]({news_item['link']})\n\n"
            "#Новости #Аналитика"
        )
    except Exception as e:
        logger.error(f"News post error: {e}")
        return None

def send_post(post, is_news=False):
    try:
        if not post:
            return
            
        logger.info("Отправка поста...")
        bot.send_message(
            chat_id=CHANNEL_ID,
            text=post,
            parse_mode="Markdown",
            disable_web_page_preview=not is_news
        )
        logger.info("Пост успешно отправлен")
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def schedule_tasks():
    logger.info("Настройка расписания...")
    
    # Рыночные отчеты в 08:00 и 22:00 по Москве
    schedule.every().day.at("08:00").do(lambda: send_post(generate_daily_report()))
    schedule.every().day.at("22:00").do(lambda: send_post(generate_daily_report()))
    
    # Новости каждый час с 09:00 до 21:00 по Москве
    for hour in range(9, 22):
        schedule.every().day.at(f"{hour:02d}:00").do(post_news_update)

def post_news_update():
    try:
        # Чередуем источники новостей
        sources = ['rbc', 'tradingview']
        for source in sources:
            news_item = fetch_news(source)
            if news_item:
                post = generate_news_post(news_item)
                if post:
                    send_post(post, is_news=True)
                    time.sleep(5)  # Пауза между постами
    except Exception as e:
        logger.error(f"News update error: {e}")

def fetch_news(source):
    try:
        if source == "rbc":
            return parse_rbc_news()
        elif source == "tradingview":
            return parse_tradingview_news()
        return None
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return None

def run_scheduler():
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # Настройка временной зоны
    os.environ['TZ'] = 'Europe/Moscow'
    time.tzset()
    
    # Инициализация планировщика
    schedule_tasks()
    
    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Основной цикл
    logger.info("Бот запущен")
    while True:
        time.sleep(3600)
