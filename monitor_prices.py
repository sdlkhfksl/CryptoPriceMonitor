import requests
import time
import json
import os
from multiprocessing import Process
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API keys for different services
API_KEYS = {
    'COINMARKETCAP_API_KEY': os.getenv('COINMARKETCAP_API_KEY'),
    'CRYPTOCOMPARE_API_KEY': os.getenv('CRYPTOCOMPARE_API_KEY'),
    'MESSARI_API_KEY': os.getenv('MESSARI_API_KEY')
}

# Function to fetch data from CoinGecko
def fetch_from_coingecko(coin_ids):
    ids = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from CoinGecko: {e}")
        return {}

# Function to fetch data from CoinMarketCap
def fetch_from_coinmarketcap(coin_ids):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        'X-CMC_PRO_API_KEY': API_KEYS['COINMARKETCAP_API_KEY']
    }
    ids = ",".join(coin_ids)
    params = {
        'id': ids,
        'convert': 'USD'
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return {coin_id: data['data'][coin_id]['quote']['USD']['price'] for coin_id in coin_ids}
    except Exception as e:
        print(f"Error fetching from CoinMarketCap: {e}")
        return {}

# Function to fetch data from CryptoCompare
def fetch_from_cryptocompare(coin_ids):
    ids = ",".join(coin_ids)
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={ids}&tsyms=USD&api_key={API_KEYS['CRYPTOCOMPARE_API_KEY']}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return {coin: response.json()[coin]['USD'] for coin in coin_ids}
    except Exception as e:
        print(f"Error fetching from CryptoCompare: {e}")
        return {}

# Function to fetch data from Messari
def fetch_from_messari(coin_ids):
    ids = ",".join(coin_ids)
    url = f"https://data.messari.io/api/v1/assets"
    headers = {
        'x-messari-api-key': API_KEYS['MESSARI_API_KEY']
    }
    params = {
        'ids': ids
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return {coin['id']: coin['metrics']['market_data']['price_usd'] for coin in data['data'] if coin['id'] in coin_ids}
    except Exception as e:
        print(f"Error fetching from Messari: {e}")
        return {}

# 发送消息到Telegram
def send_telegram_message(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

# 获取市值排名前100的币种
def get_top_100_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [coin['id'] for coin in data]
    except Exception as e:
        print(f"Error fetching top 100 coins from CoinGecko: {e}")
        return []

def load_price_history(filepath):
    print(f"Loading price history from {filepath}")
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {filepath}: {e}")
                return {}
    return {}

def save_price_history(price_history, filepath):
    print(f"Saving price history to {filepath}")
    with open(filepath, 'w') as f:
        try:
            json.dump(price_history, f, indent=4)
        except Exception as e:
            print(f"Error saving JSON to {filepath}: {e}")

# Function to monitor price changes
def monitor_prices(interval=600, threshold=0.05, history_file='price_history.json'):
    coins = get_top_100_coins()
    
    # Split the coins into batches for each API
    n_coins = len(coins)
    batches = [
        coins[0:20],      # 1-20 to CoinGecko
        coins[20:40],     # 21-40 to CoinMarketCap
        coins[40:60],     # 41-60 to CryptoCompare
        coins[60:80],     # 61-80 to Messari
        coins[80:100]     # 81-100 to CoinGecko or another API
    ]
    
    price_history = load_price_history(history_file)

    for coin in coins:
        if coin not in price_history:
            price_history[coin] = []

    def check_price_changes():
        current_prices = {}
        processes = [
            Process(target=lambda: current_prices.update(fetch_from_coingecko(batches[0]))),
            Process(target=lambda: current_prices.update(fetch_from_coinmarketcap(batches[1]))),
            Process(target=lambda: current_prices.update(fetch_from_cryptocompare(batches[2]))),
            Process(target=lambda: current_prices.update(fetch_from_messari(batches[3]))),
            Process(target=lambda: current_prices.update(fetch_from_coingecko(batches[4])))
        ]

        for process in processes:
            process.start()

        for process in processes:
            process.join()

        for coin, price in current_prices.items():
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

        save_price_history(price_history, history_file)

    check_price_changes()

if __name__ == "__main__":
    monitor_prices()
