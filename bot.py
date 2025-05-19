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
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
PORT = 10000

# Инициализация
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler(timezone=MOSCOW_TZ)

# Настройка DeepSeek
openai.api_key = DEEPSEEK_API_KEY
openai.api_base = "https://api.deepseek.com/v1"

def generate_hourly_post():
    """Генерация почасового поста с помощью AI"""
    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": "Создай короткий информативный пост о криптовалютах. Темы: DeFi, NFT, Web3. Используй эмодзи и markdown."
            }],
            temperature=0.7,
            max_tokens=500
        )
        return f"🕒 *Крипто-обновление {datetime.datetime.now(MOSCOW_TZ).strftime('%H:%M')}*\n\n{response.choices[0].message.content}\n\n#Новости"
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        return "🔧 Технические неполадки. Обновление появится позже."

def fetch_market_data():
    """Получение рыночных данных от CoinMarketCap"""
    try:
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        response = requests.get(url, headers=headers, timeout=20)
        data = response.json()["data"]
        
        return (
            "📈 *Рыночный отчет*\n\n"
            f"• Капитализация: ${round(data['quote']['USD']['total_market_cap']/1e12, 2)}T\n"
            f"• BTC Доминация: {round(data['btc_dominance'], 2)}%\n"
            f"• Объем 24ч: ${round(data['quote']['USD']['total_volume_24h']/1e9, 2)}B\n"
            "#Статистика #Рынок"
        )
    except Exception as e:
        logger.error(f"Ошибка CoinMarketCap: {str(e)}")
        return None

def generate_educational_post():
    """Генерация образовательного контента"""
    try:
        response = openai.ChatCompletion.create(
            model="deepseek-chat",
            messages=[{
                "role": "user",
                "content": "Объясни концепцию блокчейна простым языком. Примеры, эмодзи, markdown."
            }],
            temperature=0.6,
            max_tokens=800
        )
        return f"📚 *Образовательный раздел*\n\n{response.choices[0].message.content}\n\n#Обучение"
    except Exception as e:
        logger.error(f"Ошибка генерации: {str(e)}")
        return None

def send_post(content):
    """Отправка поста в канал"""
    try:
        if content:
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=content,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Отправлено: {datetime.datetime.now(MOSCOW_TZ).strftime('%d.%m %H:%M')}")
    except Exception as e:
        logger.error(f"Ошибка отправки: {str(e)}")

def setup_scheduler():
    """Настройка расписания"""
    # Почасовые посты 09:00-21:00
    scheduler.add_job(
        lambda: send_post(generate_hourly_post()),
        CronTrigger(hour='9-21', minute=0)
    )
    
    # Рыночная статистика
    scheduler.add_job(
        lambda: send_post(fetch_market_data()),
        CronTrigger(hour='8,22', minute=0)
    )
    
    # Образовательные материалы
    scheduler.add_job(
        lambda: send_post(generate_educational_post()),
        CronTrigger(hour='15,19', minute=30)
    )

@app.route('/')
def health_check():
    return "Бот активен", 200

if __name__ == "__main__":
    os.environ['TZ'] = 'Europe/Moscow'
    time.tzset()
    
    # Запуск планировщика
    setup_scheduler()
    scheduler.start()
    
    # Запуск Flask
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False),
        daemon=True
    ).start()
    
    # Основной цикл
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Работа бота остановлена")
