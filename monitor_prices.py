import requests
import json
import time
from multiprocessing import Process, Manager
import os
import telegram

COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.json")

threshold = 0.05  # 5% price change threshold
price_history = {}

# Function to send a message via Telegram
def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

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

# Function to generate ID mappings for the top 100 coins
def generate_id_mappings():
    coingecko_map = {coin['id']: coin['id'] for coin in get_top_100_coins()}

    coinmarketcap_response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map', headers={
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
    })
    coinmarketcap_map = {coin['slug']: coin['id'] for coin in coinmarketcap_response.json()['data']}

    cryptocompare_response = requests.get('https://min-api.cryptocompare.com/data/all/coinlist', headers={
        'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
    })
    cryptocompare_map = {coin['FullName'].lower().replace(' ', '-'): coin['Name'] for coin in cryptocompare_response.json()['Data'].values()}

    messari_response = requests.get('https://data.messari.io/api/v1/assets')
    messari_map = {coin['slug']: coin['symbol'] for coin in messari_response.json()['data']}

    return coingecko_map, coinmarketcap_map, cryptocompare_map, messari_map

coingecko_map, coinmarketcap_map, cryptocompare_map, messari_map = generate_id_mappings()

# Function to fetch prices from CoinGecko
def fetch_from_coingecko(coins, current_prices):
    response = requests.get('https://api.coingecko.com/api/v3/simple/price', params={
        'ids': ','.join(coins),
        'vs_currencies': 'usd'
    })
    current_prices.update(response.json())

# Function to fetch prices from CoinMarketCap
def fetch_from_coinmarketcap(coins, current_prices):
    coin_ids = [coinmarketcap_map[coin] for coin in coins if coin in coinmarketcap_map]
    if coin_ids:
        response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?id={",".join(map(str, coin_ids))}', headers={
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
        })
        data = response.json()['data']
        for coin in coins:
            if coin in coinmarketcap_map:
                coin_id = coinmarketcap_map[coin]
                if str(coin_id) in data:
                    current_prices[coin] = data[str(coin_id)]['quote']['USD']['price']

# Function to fetch prices from CryptoCompare
def fetch_from_cryptocompare(coins, current_prices):
    coin_symbols = [cryptocompare_map[coin] for coin in coins if coin in cryptocompare_map]
    if coin_symbols:
        response = requests.get(f'https://min-api.cryptocompare.com/data/pricemulti?fsyms={",".join(coin_symbols)}&tsyms=USD', headers={
            'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
        })
        data = response.json()
        for coin in coins:
            if coin in cryptocompare_map:
                symbol = cryptocompare_map[coin]
                if symbol in data:
                    current_prices[coin] = data[symbol]['USD']

# Function to fetch prices from Messari
def fetch_from_messari(coins, current_prices):
    coin_symbols = [messari_map[coin] for coin in coins if coin in messari_map]
    for symbol in coin_symbols:
        response = requests.get(f'https://data.messari.io/api/v1/assets/{symbol}/metrics/market-data', headers={
            'x-messari-api-key': MESSARI_API_KEY
        })
        data = response.json()
        if 'data' in data and 'market_data' in data['data']:
            current_prices[symbol] = data['data']['market_data']['price_usd']

# Function to save price history to a file
def save_price_history(price_history, file):
    with open(file, 'w') as f:
        json.dump(price_history, f, indent=4)

# Function to load price history from a file
def load_price_history(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {coin: [] for coin in coingecko_map.keys()}

price_history = load_price_history(PRICE_HISTORY_FILE)

# Function to check for significant price changes
def check_price_changes():
    manager = Manager()
    current_prices = manager.dict()
    processes = [
        Process(target=fetch_from_coingecko, args=(batches[0], current_prices)),
        Process(target=fetch_from_coinmarketcap, args=(batches[1], current_prices)),
        Process(target=fetch_from_cryptocompare, args=(batches[2], current_prices)),
        Process(target=fetch_from_messari, args=(batches[3], current_prices)),
        Process(target=fetch_from_coingecko, args=(batches[4], current_prices))
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    print(f"Fetched current prices: {dict(current_prices)}")

    for coin, price_info in current_prices.items():
        # Handle the case where price_info is a dictionary containing 'usd'
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

# Main function to monitor prices
def monitor_prices(history_file):
    while True:
        check_price_changes()
        time.sleep(300)  # Wait for 5 minutes before checking again

if __name__ == "__main__":
    monitor_prices(PRICE_HISTORY_FILE)
