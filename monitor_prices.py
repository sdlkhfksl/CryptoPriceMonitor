import requests
import json
import os
import time
from multiprocessing import Manager, Process

# 从环境变量中获取配置信息
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.json")

threshold = 0.05  # 5% price change threshold
batch_size = 20   # 每批处理的币种数量
rate_limit_interval = 3  # 设置间隔时间为3秒

# Function to send a message via Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print(f"Telegram message sent: {message}")
    except requests.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

# Function to fetch top 100 coins from CoinGecko
def get_top_100_coins():
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False
    })
    return response.json()

# Function to fetch prices from CoinGecko
def fetch_from_coingecko(coins, current_prices):
    ids = ','.join(coins)
    response = requests.get('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': ids,
        'vs_currencies': 'usd'
    })
    if response.status_code == 200:
        current_prices.update(response.json())
    else:
        print(f"Error fetching from CoinGecko: {response.status_code}, {response.text}")

# Function to save price history to a file
def save_price_history(price_history, file):
    with open(file, 'w') as f:
        json.dump(price_history, f, indent=4)

# Function to load price history from a file
def load_price_history(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {coin['id']: [] for coin in get_top_100_coins()}

price_history = load_price_history(PRICE_HISTORY_FILE)

# Function to check for significant price changes
def check_price_changes(batches):
    manager = Manager()
    current_prices = manager.dict()

    def fetch_batches():
        for batch in batches:
            fetch_from_coingecko(batch, current_prices)
            time.sleep(rate_limit_interval)

    process = Process(target=fetch_batches)
    process.start()
    process.join()

    print(f"Fetched current prices: {dict(current_prices)}")

    for coin, price_info in current_prices.items():
        if isinstance(price_info, dict):
            price = price_info['usd'] if 'usd' in price_info else None
        else:
            price = price_info
        
        if price is not None:
            if len(price_history[coin]) >= 3:
                price_history[coin].pop(0)
            price_history[coin].append(price)
            if len(price_history[coin]) == 3:  # 10 minutes, every 5 minutes 1 price
                initial_price = price_history[coin][0]
                latest_price = price_history[coin][-1]
                price_change = (latest_price - initial_price) / initial_price
                if abs(price_change) >= threshold:
                    change_pct = price_change * 100
                    msg = f"Coin {coin}: Price changed by {change_pct:.2f}% over the last 10 minutes."
                    print(msg)
                    send_telegram_message(msg)

    save_price_history(price_history, PRICE_HISTORY_FILE)

if __name__ == "__main__":
    top_100_coins = [coin['id'] for coin in get_top_100_coins()]
    batches = [top_100_coins[i:i + batch_size] for i in range(0, len(top_100_coins), batch_size)]

    check_price_changes(batches)
