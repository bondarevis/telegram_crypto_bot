import telebot
import requests
import datetime

TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1E"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот активен и публикует крипто-новости в канал!")

def fetch_crypto_news():
    now = datetime.datetime.now()
    return f"📰 Крипто-новость на {now.strftime('%H:%M')} — пример новости."

def post_to_channel():
    news = fetch_crypto_news()
    bot.send_message(CHANNEL_ID, news)

if __name__ == "__main__":
    post_to_channel()
