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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация (данные уже вставлены)
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
CMC_API_KEY = "6316a41d-db32-4e49-a2a3-b66b96c663bf"
REQUEST_TIMEOUT = 15
PORT = int(os.getenv('PORT', 10000))

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
try:
    bot = telebot.TeleBot(TOKEN, num_threads=1, skip_pending=True)
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    exit(1)

@app.route('/')
def health_check():
    return "Crypto Bot is Running", 200

def fetch_coingecko():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        btc_dominance = round(data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap = round(data["data"]["total_market_cap"]["usd"] / 1e12, 2)
        market_change = round(data["data"]["market_cap_change_percentage_24h_usd"], 2)
        return f"📊 CoinGecko: Капитализация ${total_market_cap}T | BTC домин. {btc_dominance}% | Изм. 24ч: {market_change}%"
    except Exception as e:
        logger.error(f"CoinGecko error: {e}")
        return "❌ CoinGecko: временные проблемы"

def fetch_cmc():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()["data"]
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e12, 2)
        market_change = round(data["quote"]["USD"]["total_market_cap_yesterday_percentage_change"], 2)
        return f"📈 CMC: Капитализация ${total_market_cap}T | BTC домин. {btc_dominance}% | Изм.: {market_change}%"
    except Exception as e:
        logger.error(f"CMC error: {e}")
        return "❌ CMC: временные проблемы"

def fetch_rbk_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = [h.text.strip() for h in soup.select('.item__title')[:3]]
        return "📰 RBK Crypto:" " + "\n".join(f"• {h}" for h in headlines)
    except Exception as e:
        logger.error(f"RBK error: {e}")
        return "❌ RBK: ошибка парсинга"

def generate_post():
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""🚀 Крипто-обзор на {now}

{fetch_coingecko()}
{fetch_cmc()}
{fetch_rbk_crypto()}

#Crypto #Аналитика #Новости"""

def send_market_update():
    try:
        bot.send_message(CHANNEL_ID, generate_post(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Send error: {e}")

def schedule_posts():
    for hour in range(8, 23):
        schedule.every().day.at(f"{hour:02d}:00").do(send_market_update)
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_bot():
    bot.remove_webhook()
    logger.info("Starting bot polling...")
    bot.infinity_polling(none_stop=True, timeout=30)

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=schedule_posts, daemon=True)
    scheduler_thread.start()

    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=PORT),
        daemon=True
    ).start()

    run_bot()
