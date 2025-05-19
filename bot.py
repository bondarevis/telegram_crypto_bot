import os
import telebot
import requests
import datetime
import threading
import logging
import time
from flask import Flask
import pytz
import openai
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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
DEEPSEEK_API_KEY = "sk-1b4a385cf98446f2995a58ba9a6fd4b8"
REQUEST_TIMEOUT = 20
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
PORT = 10000

# Инициализация
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)

# Настройка DeepSeek
openai.api_key = DEEPSEEK_API_KEY
openai.api_base = "https://api.deepseek.com/v1"

@app.route('/')
def health_check():
    logger.info("Health check received")
    return "Crypto Bot is Running", 200

def get_current_time():
    return datetime.datetime.now(MOSCOW_TZ)

def generate_crypto_basics_post():
    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": "Напиши образовательный пост о базовых концепциях криптовалют. Освещи темы: блокчейн, майнинг, смарт-контракты. Пост должен быть понятен новичкам, содержать примеры и эмодзи для наглядности. Форматируй как markdown."
            }],
            temperature=0.7,
            max_tokens=1000
        )
        content = response.choices[0].message.content
        return f"📚 *Основы криптовалют*\n\n{content}\n\n#Обучение #КриптоОсновы"
    except Exception as e:
        logger.error(f"DeepSeek error: {str(e)}", exc_info=True)
        return None

def fetch_market_data():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY,
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()["data"]
        
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e12, 2)
        volume_24h = round(data["quote"]["USD"]["total_volume_24h"] / 1e9, 2)
        
        return (
            "📊 *Рыночная статистика*\n\n"
            f"• Общая капитализация: ${total_market_cap}T\n"
            f"• Доминация BTC: {btc_dominance}%\n"
            f"• Объем за 24ч: ${volume_24h}B\n"
            f"• Данные: CoinMarketCap"
        )
    except Exception as e:
        logger.error(f"CoinMarketCap error: {str(e)}", exc_info=True)
        return None

def generate_market_post():
    try:
        market_data = fetch_market_data()
        return f"{market_data}\n\n#Рынок #Статистика" if market_data else None
    except Exception as e:
        logger.error(f"Market post error: {str(e)}")
        return None

def send_post(post):
    try:
        if not post:
            logger.warning("Attempt to send empty post")
            return
            
        logger.info(f"Sending post at {get_current_time()}")
        bot.send_message(
            chat_id=CHANNEL_ID,
            text=post,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info("Post sent successfully")
    except Exception as e:
        logger.error(f"Send error: {str(e)}")

def setup_scheduler():
    logger.info("Initializing scheduler...")
    
    # Рыночная статистика
    scheduler.add_job(
        lambda: send_post(generate_market_post()),
        CronTrigger(hour='8,22', minute='0', timezone=MOSCOW_TZ)
    )
    
    # Образовательные посты
    scheduler.add_job(
        lambda: send_post(generate_crypto_basics_post()),
        CronTrigger(hour='15,19', minute='30', timezone=MOSCOW_TZ)
    )
    
    logger.info(f"Total jobs scheduled: {len(scheduler.get_jobs())}")

if __name__ == "__main__":
    os.environ['TZ'] = 'Europe/Moscow'
    time.tzset()
    logger.info(f"Server started at {get_current_time()}")
    
    # Настройка планировщика
    setup_scheduler()
    scheduler.start()
    
    # Запуск Flask
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Ожидание прерывания
    try:
        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Bot stopped successfully")
