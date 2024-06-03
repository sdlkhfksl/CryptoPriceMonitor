import requests
import json
import os
import time
from multiprocessing import Process, Manager

COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.json")
ID_MAPPINGS_FILE = "id_mappings.json"

threshold = 0.05  # 5% price change threshold

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

def load_id_mappings():
    if os.path.exists(ID_MAPPINGS_FILE):
        with open(ID_MAPPINGS_FILE, 'r') as f:
            return json.load(f)
    raise FileNotFoundError(f"{ID_MAPPINGS_FILE} not found. Please run the ID mappings generation script.")

mappings = load_id_mappings()
coingecko_map = mappings['coingecko']
coinmarketcap_map = mappings['coinmarketcap']
cryptocompare_map = mappings['cryptocompare']
messari_map = mappings['messari']
coinpaprika_map = mappings['coinpaprika']

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

def fetch_from_coinmarketcap(coins, current_prices):
    coin_ids = [coinmarketcap_map[coin] for coin in coins if coin in coinmarketcap_map]
    if coin_ids:
        response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?id={",".join(map(str, coin_ids))}', headers={
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
        })
        if response.status_code == 200:
            data = response.json().get('data', {})
            for coin in coins:
                if coin in coinmarketcap_map:
                    coin_id = coinmarketcap_map[coin]
                    if str(coin_id) in data:
                        current_prices[coin] = data[str(coin_id)]['quote']['USD']['price']
        else:
            print(f"Error fetching from CoinMarketCap: {response.status_code}, {response.text}")

def fetch_from_cryptocompare(coins, current_prices):
    coin_symbols = [cryptocompare_map[coin] for coin in coins if coin in cryptocompare_map]
    if coin_symbols:
        response = requests.get(f'https://min-api.cryptocompare.com/data/pricemulti?fsyms={",".join(coin_symbols)}&tsyms=USD', headers={
            'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
        })
        if response.status_code == 200:
            data = response.json()
            for coin in coins:
                if coin in cryptocompare_map:
                    symbol = cryptocompare_map[coin]
                    if symbol in data:
                        current_prices[coin] = data[symbol]['USD']
        else:
            print(f"Error fetching from CryptoCompare: {response.status_code}, {response.text}")

def fetch_from_messari(coins, current_prices):
    coin_symbols = [messari_map[coin] for coin in coins if coin in messari_map]
    for symbol in coin_symbols:
        response = requests.get(f'https://data.messari.io/api/v1/assets/{symbol}/metrics/market-data', headers={
            'x-messari-api-key': MESSARI_API_KEY
        })
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'market_data' in data['data']:
                current_prices[symbol] = data['data']['market_data']['price_usd']
        else:
            print(f"Error fetching from Messari: {response.status_code}, {response.text}")

def fetch_from_coinpaprika(coins, current_prices):
    for coin in coins:
        if coin in coinpaprika_map:
            response = requests.get(f'https://api.coinpaprika.com/v1/tickers/{coin}')
            if response.status_code == 200:
                data = response.json()
                current_prices[coin] = data['quotes']['USD']['price']
            else:
                print(f"Error fetching from CoinPaprika: {response.status_code}, {response.text}")

def save_price_history(price_history, file):
    with open(file, 'w') as f:
        json.dump(price_history, f, indent=4)

def load_price_history(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {coin: [] for coin in coingecko_map.keys()}

price_history = load_price_history(PRICE_HISTORY_FILE)

def check_price_changes(batches):
    manager = Manager()
    current_prices = manager.dict()
    processes = [
        Process(target=fetch_from_coingecko, args=(batches[0], current_prices)),
        Process(target=fetch_from_coinmarketcap, args=(batches[1], current_prices)),
        Process(target=fetch_from_cryptocompare, args=(batches[2], current_prices)),
        Process(target=fetch_from_messari, args=(batches[3], current_prices)),
        Process(target=fetch_from_coinpaprika, args=(batches[4], current_prices))
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    print(f"Fetched current prices: {dict(current_prices)}")

    for coin, price_info in current_prices.items():
        if isinstance(price_info, dict):
            price = price_info['usd']
        else:
            price = price_info

        if len(price_history[coin]) >= 3:
            previous_price = price_history[coin][-3]['price']
            price_change = (price - previous_price) / previous_price
            if abs(price_change) >= threshold:
                direction = "up" if price_change > 0 else "down"
                message = f"Price of {coin} is {direction} by {price_change:.2%} over the last 15 minutes. Current price: ${price:.2f}"
                send_telegram_message(message)
        price_history[coin].append({'timestamp': time.time(), 'price': price})

def split_into_batches(coins):
    return [coins[i::5] for i in range(5)]

batches = split_into_batches(list(coingecko_map.keys()))

check_price_changes(batches)
save_price_history(price_history, PRICE_HISTORY_FILE)
