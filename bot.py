import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup

# Настройки
TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = "@YOUR_CHANNEL_NAME"
CMC_API_KEY = "YOUR_CMC_API_KEY"

bot = telebot.TeleBot(TOKEN)

# Получение данных с CoinGecko
def fetch_coingecko():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url)
        data = response.json()
        btc_dominance = round(data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap = round(data["data"]["total_market_cap"]["usd"] / 1e9, 2)
        market_change = round(data["data"]["market_cap_change_percentage_24h_usd"], 2)
        return f"CoinGecko: Капитализация ${total_market_cap}B | BTC домин. {btc_dominance}% | Изм. 24ч: {market_change}%"
    except:
        return "CoinGecko: ошибка получения данных."

# Получение данных с CoinMarketCap
def fetch_cmc():
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        response = requests.get(url, headers=headers)
        data = response.json()["data"]
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e9, 2)
        market_change = round(data["quote"]["USD"]["total_market_cap_yesterday_percentage_change"], 2)
        return f"CoinMarketCap: Капитализация ${total_market_cap}B | BTC домин. {btc_dominance}% | Изм. вч.: {market_change}%"
    except:
        return "CoinMarketCap: ошибка получения данных."

# Парсинг RBK Crypto
def fetch_rbk_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = soup.select(".item__title")[:1]
        return f"RBK Crypto: {headlines[0].text.strip()}" if headlines else "RBK Crypto: нет свежих новостей."
    except:
        return "RBK Crypto: ошибка парсинга."

# Компиляция поста
def generate_post():
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    parts = [fetch_coingecko(), fetch_cmc(), fetch_rbk_crypto()]
    return f"**Обзор крипторынка на {now}**\n\n" + "\n".join(parts) + "\n\n#crypto #новости"

# Отправка поста
def send_market_update():
    try:
        summary = generate_post()
        bot.send_message(CHANNEL_ID, summary, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# Планировщик
def schedule_posts():
    for hour in range(8, 23):
        schedule.every().day.at(f"{hour:02d}:00").do(send_market_update)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Обработчик ошибок и перезапуска
def run_bot():
    bot.remove_webhook()
    while True:
        try:
            print("Бот запущен...")
            bot.infinity_polling()
        except telebot.apihelper.ApiTelegramException as e:
            if "Conflict" in str(e):
                print(f"Обнаружен конфликт: {e}. Перезапуск через 10 секунд...")
                time.sleep(10)
            else:
                raise e
        except Exception as e:
            print(f"Критическая ошибка: {e}. Перезапуск через 30 секунд...")
            time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=schedule_posts, daemon=True).start()
    run_bot()
