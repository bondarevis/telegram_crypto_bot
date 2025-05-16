import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup
import random
import socket

# --- Блокировка множественных экземпляров ---
try:
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    lock_socket.bind('\0digital_fund_bot_lock')
except socket.error:
    print("⛔ Обнаружен уже запущенный экземпляр бота. Закройте предыдущую версию!")
    exit(1)

# Настройки
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
CMC_API_KEY = "6316a41d-db32-4e49-a2a3-b66b96c663bf"
REQUEST_TIMEOUT = 15  # секунд

bot = telebot.TeleBot(TOKEN, threaded=False)  # Отключаем многопоточность для избежания конфликтов

# --- Улучшенное получение данных с CoinGecko ---
def fetch_coingecko():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        btc_dominance = round(data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap = round(data["data"]["total_market_cap"]["usd"] / 1e12, 2)
        market_change = round(data["data"]["market_cap_change_percentage_24h_usd"], 2)
        active_cryptos = data["data"]["active_cryptocurrencies"]
        total_volume = round(data["data"]["total_volume"]["usd"] / 1e9, 2)
        
        return (
            f"📊 *CoinGecko Global Stats*\n"
            f"• Капитализация: *${total_market_cap}T*\n"
            f"• Объем 24ч: *${total_volume}B*\n"
            f"• BTC Доминирование: *{btc_dominance}%*\n"
            f"• Изменение 24ч: *{market_change}%*\n"
            f"• Активные монеты: *{active_cryptos}*"
        )
    except Exception as e:
        print(f"CoinGecko error: {str(e)}")
        return "❌ CoinGecko: временные проблемы с данными"

# --- Улучшенное получение данных с CoinMarketCap ---
def fetch_cmc():
    try:
        headers = {
            "X-CMC_PRO_API_KEY": CMC_API_KEY,
            "Accept": "application/json"
        }
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()["data"]
        
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e12, 2)
        market_change = round(data["quote"]["USD"]["total_market_cap_yesterday_percentage_change"], 2)
        eth_dominance = round(data["eth_dominance"], 2)
        
        return (
            f"📈 *CoinMarketCap Metrics*\n"
            f"• Капитализация: *${total_market_cap}T*\n"
            f"• BTC Доминирование: *{btc_dominance}%*\n"
            f"• ETH Доминирование: *{eth_dominance}%*\n"
            f"• Изменение за вчера: *{market_change}%*"
        )
    except Exception as e:
        print(f"CMC error: {str(e)}")
        return "❌ CoinMarketCap: временные проблемы с API"

# --- Парсинг новостей с улучшенной обработкой ---
def fetch_rbk_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select('.item__title')[:3]
        
        if not news_items:
            return "🔍 RBK Crypto: нет свежих новостей"
            
        news_list = []
        for idx, item in enumerate(news_items, 1):
            title = item.text.strip()
            link = item.find('a')['href'] if item.find('a') else '#'
            news_list.append(f"{idx}. [{title}]({link})")
        
        return "📰 *Последние новости RBK Crypto:*\n" + "\n".join(news_list)
    except Exception as e:
        print(f"RBK error: {str(e)}")
        return "❌ RBK Crypto: ошибка при получении новостей"

# --- Генерация случайного факта ---
def get_crypto_fact():
    facts = [
        "💡 Первая BTC транзакция: 10,000 BTC за 2 пиццы в 2010",
        "🔐 Кошельки хранят не монеты, а приватные ключи",
        "🌍 Эфириум предложен 19-летним Бутериным в 2013",
        "⚡ Lightning Network - решение для мгновенных BTC платежей",
        "🦄 Uniswap создан без венчурного финансирования"
    ]
    return random.choice(facts)

# --- Генерация поста с обработкой ошибок ---
def generate_post():
    try:
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        post = (
            f"🚀 *Крипто-обзор на {now}*\n\n"
            f"{fetch_coingecko()}\n\n"
            f"{fetch_cmc()}\n\n"
            f"{fetch_rbk_crypto()}\n\n"
            f"{get_crypto_fact()}\n\n"
            f"#Crypto #Аналитика #Новости #Блокчейн"
        )
        return post
    except Exception as e:
        print(f"Post generation error: {str(e)}")
        return f"🚀 Экстренный обзор на {now}\n\nПриносим извинения - временные технические сложности. Полная версия скоро будет доступна."

# --- Отправка поста с разделением длинных сообщений ---
def send_market_update():
    try:
        post = generate_post()
        if len(post) > 4096:
            parts = [post[i:i+4000] for i in range(0, len(post), 4000)]
            for part in parts:
                bot.send_message(CHANNEL_ID, part, parse_mode="Markdown")
                time.sleep(1)
        else:
            bot.send_message(CHANNEL_ID, post, parse_mode="Markdown")
    except Exception as e:
        print(f"Send error: {str(e)}")

# --- Планировщик со случайным смещением ---
def schedule_posts():
    for hour in range(8, 23):
        minute = random.randint(0, 20)
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(send_market_update)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- Запуск бота с защитой от конфликтов ---
def run_bot():
    bot.remove_webhook()
    while True:
        try:
            print("🟢 Бот успешно запущен и ожидает обновлений...")
            bot.infinity_polling(long_polling_timeout=20, timeout=90)
        except telebot.apihelper.ApiTelegramException as e:
            if "Conflict" in str(e):
                print(f"🔴 Конфликт обнаружен: {e}")
                print("🟠 Ожидание 30 секунд перед перезапуском...")
                time.sleep(30)
            else:
                print(f"🔴 Ошибка Telegram API: {e}")
                time.sleep(60)
        except Exception as e:
            print(f"🔴 Критическая ошибка: {str(e)}")
            print("🟠 Перезапуск через 60 секунд...")
            time.sleep(60)

if __name__ == "__main__":
    print("=== Запуск крипто-бота ===")
    print(f"Версия: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=schedule_posts, daemon=True)
    scheduler_thread.start()
    
    # Запускаем основного бота
    run_bot()
