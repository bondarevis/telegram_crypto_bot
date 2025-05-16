import telebot
import requests
import datetime
import schedule
import time
import threading
from bs4 import BeautifulSoup
import random

# Настройки
TOKEN = "8067270518:AAFir3k_EuRhNlGF9bD9ER4VHQevld-rquk"
CHANNEL_ID = "@Digital_Fund_1"
CMC_API_KEY = "6316a41d-db32-4e49-a2a3-b66b96c663bf"

bot = telebot.TeleBot(TOKEN)

# Получение данных с CoinGecko (с улучшенной обработкой ошибок)
def fetch_coingecko():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Проверка на HTTP ошибки
        data = response.json()
        
        btc_dominance = round(data["data"]["market_cap_percentage"]["btc"], 2)
        total_market_cap = round(data["data"]["total_market_cap"]["usd"] / 1e12, 2)  # в триллионах
        market_change = round(data["data"]["market_cap_change_percentage_24h_usd"], 2)
        
        # Дополнительные метрики
        active_cryptos = data["data"]["active_cryptocurrencies"]
        total_volume = round(data["data"]["total_volume"]["usd"] / 1e9, 2)  # в миллиардах
        
        return (
            f"📊 *CoinGecko Global Stats*\n"
            f"• Капитализация: *${total_market_cap}T*\n"
            f"• Объем 24ч: *${total_volume}B*\n"
            f"• BTC Доминирование: *{btc_dominance}%*\n"
            f"• Изменение 24ч: *{market_change}%*\n"
            f"• Активные монеты: *{active_cryptos}*"
        )
    except requests.exceptions.RequestException as e:
        print(f"CoinGecko API Error: {e}")
        return "❌ CoinGecko: временные проблемы с API. Данные могут быть неполными."
    except Exception as e:
        print(f"Unexpected CoinGecko error: {e}")
        return "❌ CoinGecko: ошибка обработки данных."

# Получение данных с CoinMarketCap (расширенная версия)
def fetch_cmc():
    try:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        
        btc_dominance = round(data["btc_dominance"], 2)
        total_market_cap = round(data["quote"]["USD"]["total_market_cap"] / 1e12, 2)  # в триллионах
        market_change = round(data["quote"]["USD"]["total_market_cap_yesterday_percentage_change"], 2)
        
        # Дополнительные метрики
        eth_dominance = round(data["eth_dominance"], 2)
        altcoin_market_cap = round((data["quote"]["USD"]["total_market_cap"] * (100 - btc_dominance) / 100) / 1e12, 2)
        
        return (
            f"📈 *CoinMarketCap Global Metrics*\n"
            f"• Рыночная капитализация: *${total_market_cap}T*\n"
            f"• BTC Доминирование: *{btc_dominance}%*\n"
            f"• ETH Доминирование: *{eth_dominance}%*\n"
            f"• Капитализация альткоинов: *${altcoin_market_cap}T*\n"
            f"• Изменение за вчера: *{market_change}%*"
        )
    except requests.exceptions.RequestException as e:
        print(f"CMC API Error: {e}")
        return "❌ CoinMarketCap: временные проблемы с API"
    except Exception as e:
        print(f"Unexpected CMC error: {e}")
        return "❌ CoinMarketCap: ошибка обработки данных"

# Парсинг RBK Crypto (сбор нескольких новостей)
def fetch_rbk_crypto():
    try:
        url = "https://www.rbc.ru/crypto/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select('.item__title')[:3]  # Берем 3 последние новости
        
        if not news_items:
            return "🔍 RBK Crypto: нет свежих новостей"
            
        news_list = []
        for idx, item in enumerate(news_items, 1):
            title = item.text.strip()
            link = item.find('a')['href'] if item.find('a') else '#'
            news_list.append(f"{idx}. [{title}]({link})")
        
        return "📰 *Последние новости RBK Crypto:*\n" + "\n".join(news_list)
    except Exception as e:
        print(f"RBK parsing error: {e}")
        return "❌ RBK Crypto: ошибка при получении новостей"

# Генерация случайного факта о крипте
def get_crypto_fact():
    facts = [
        "💡 Первая покупка с использованием BTC была 2 пиццы за 10,000 BTC в 2010",
        "🔐 Криптовалютные кошельки не хранят ваши монеты - они хранят приватные ключи",
        "🌍 Эфириум был предложен 19-летним Виталиком Бутериным в 2013 году",
        "⚡ Lightning Network позволяет проводить мгновенные BTC транзакции",
        "🦄 Uniswap был создан Хайденом Адамсом без венчурного финансирования"
    ]
    return random.choice(facts)

# Компиляция поста (расширенная версия)
def generate_post():
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Основные данные
    coingecko_data = fetch_coingecko()
    cmc_data = fetch_cmc()
    rbk_news = fetch_rbk_crypto()
    
    # Дополнительный контент
    crypto_fact = get_crypto_fact()
    
    # Форматирование поста
    post = (
        f"🚀 *Обзор крипторынка на {now}*\n\n"
        f"{coingecko_data}\n\n"
        f"{cmc_data}\n\n"
        f"{rbk_news}\n\n"
        f"{crypto_fact}\n\n"
        f"#Crypto #Аналитика #Новости #Блокчейн"
    )
    
    return post

# Отправка поста (с обработкой длинных сообщений)
def send_market_update():
    try:
        summary = generate_post()
        # Разделяем сообщение если оно слишком длинное
        if len(summary) > 4096:
            part1 = summary[:4000]
            part2 = summary[4000:]
            bot.send_message(CHANNEL_ID, part1, parse_mode="Markdown")
            bot.send_message(CHANNEL_ID, part2, parse_mode="Markdown")
        else:
            bot.send_message(CHANNEL_ID, summary, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        # Попытка отправить упрощенную версию при ошибке
        try:
            bot.send_message(CHANNEL_ID, f"🚀 Криптообзор на {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')} - возникли технические сложности. Полная версия скоро будет доступна.")
        except:
            print("Не удалось отправить даже упрощенное сообщение")

# Планировщик (с случайным смещением времени)
def schedule_posts():
    for hour in range(8, 23):
        # Добавляем случайное смещение от 0 до 15 минут
        minute = random.randint(0, 15)
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(send_market_update)
    
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
