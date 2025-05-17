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
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
PORT = int(os.getenv('PORT', 10000))

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
        # CoinGecko
        gecko_url = "https://api.coingecko.com/api/v3/global"
        gecko_response = requests.get(gecko_url, timeout=REQUEST_TIMEOUT)
        gecko_data = gecko_response.json()
        
        btc_dominance_gecko = round(gecko_data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap_gecko = round(gecko_data["data"]["total_market_cap"]["usd"] / 1e12, 2)

        # CoinMarketCap
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

def parse_rbc_crypto():
    try:
        base_url = "https://www.rbc.ru"
        crypto_url = f"{base_url}/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(crypto_url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем первую новость в крипто-ленте (исключая рекламу)
        article = soup.select_one('.js-news-feed-item:not(.news-feed__item--hidden)')
        if not article:
            return None
            
        title = article.select_one('.news-feed__item__title').text.strip()
        link = article['href']
        
        # Парсим содержимое статьи
        try:
            article_response = requests.get(link, headers=headers, timeout=REQUEST_TIMEOUT)
            article_soup = BeautifulSoup(article_response.text, 'html.parser')
            content_blocks = article_soup.select('.article__text p')
            content = ' '.join([p.text.strip() for p in content_blocks[:3]])[:400] + "..."
        except:
            content = "Читать полную статью ➡️"

        return {
            'title': title,
            'content': content,
            'source': 'РБК Крипто',
            'link': link
        }
    except Exception as e:
        logger.error(f"RBK Crypto error: {e}")
        return None

def generate_post(news_item):
    try:
        time_now = get_current_time().strftime("%d.%m.%Y %H:%M")
        return (
            f"📰 *Крипто-новости ({time_now})*\n\n"
            f"🏷 *{news_item['title']}*\n"
            f"{news_item['content']}\n\n"
            f"🔗 [Источник]({news_item['link']})\n"
            f"#Новости #Аналитика #РБК"
        )
    except Exception as e:
        logger.error(f"Post generation error: {e}")
        return None

def send_market_update():
    try:
        news_item = parse_rbc_crypto()
        if news_item:
            post = generate_post(news_item)
            bot.send_message(CHANNEL_ID, post, parse_mode="Markdown", disable_web_page_preview=True)
            logger.info("Пост из РБК Крипто успешно отправлен")
        else:
            logger.warning("Не удалось получить новости из РБК Крипто")
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def schedule_posts():
    logger.info("Настройка расписания...")
    
    # Рыночные отчеты в 08:00 и 22:00
    schedule.every().day.at("08:00").do(lambda: send_post(generate_daily_report()))
    schedule.every().day.at("22:00").do(lambda: send_post(generate_daily_report()))
    
    # Новости каждый час с 09:00 до 21:00
    for hour in range(9, 22):
        schedule.every().day.at(f"{hour:02d}:00").do(send_market_update)

    logger.info(f"Запланированные задачи: {schedule.get_jobs()}")

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
    
    # Запуск Flask
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Запуск планировщика
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("🤖 Бот РБК Крипто запущен")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
