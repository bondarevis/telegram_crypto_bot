
import telebot
import requests
import datetime
import schedule
import time
import threading

# Настройки
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"

bot = telebot.TeleBot(TOKEN)

# Получение данных с CoinGecko
def fetch_market_summary():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url)
        data = response.json()

        btc_dominance = round(data["data"]["market_cap_percentage"]["btc"], 2)
        eth_dominance = round(data["data"]["market_cap_percentage"]["eth"], 2)
        total_market_cap = round(data["data"]["total_market_cap"]["usd"] / 1e9, 2)
        market_change = round(data["data"]["market_cap_change_percentage_24h_usd"], 2)

        summary = (
            f"**Сводка рынка на {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}**\n\n"
            f"- Общая капитализация: ${total_market_cap} млрд\n"
            f"- Доля BTC: {btc_dominance}%\n"
            f"- Доля ETH: {eth_dominance}%\n"
            f"- Изменение за 24ч: {market_change}%\n\n"
            f"#Крипторынок #Обзор #Bitcoin #Ethereum"
        )

        return summary
    except Exception as e:
        return f"Ошибка при получении данных: {str(e)}"

# Отправка поста в канал
def send_market_update():
    summary = fetch_market_summary()
    bot.send_message(CHANNEL_ID, summary, parse_mode="Markdown")

# Запланировать посты с 08:00 до 22:00 каждый час
def schedule_posts():
    for hour in range(8, 23):
        schedule.every().day.at(f"{hour:02d}:00").do(send_market_update)

    while True:
        schedule.run_pending()
        time.sleep(60)

# Запуск планировщика в отдельном потоке
threading.Thread(target=schedule_posts).start()

# Ожидание команд
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Бот активен и будет публиковать посты каждый час с 08:00 до 22:00.")

bot.infinity_polling()

