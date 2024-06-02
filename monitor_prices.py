import requests
import json
import os
from multiprocessing import Process, Manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API keys for different services
API_KEYS = {
    'COINMARKETCAP_API_KEY': os.getenv('COINMARKETCAP_API_KEY'),
    'CRYPTOCOMPARE_API_KEY': os.getenv('CRYPTOCOMPARE_API_KEY'),
    'MESSARI_API_KEY': os.getenv('MESSARI_API_KEY')
}

# Function to get top 100 coins
def get_top_100_coins():
    print("Fetching top 100 coins from CoinGecko")
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

# Function to dynamically generate ID mappings from different APIs
def generate_id_mappings():
    coingecko_map = {coin: coin for coin in get_top_100_coins()}
    
    coinmarketcap_response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map', headers={
        'X-CMC_PRO_API_KEY': API_KEYS['COINMARKETCAP_API_KEY']
    })
    coinmarketcap_map = {coin['name'].lower().replace(' ', '-'): coin['symbol'] for coin in coinmarketcap_response.json()['data']}
    
    cryptocompare_response = requests.get('https://min-api.cryptocompare.com/data/all/coinlist?summary=true')
    cryptocompare_map = {coin['FullName'].lower().replace(' ', '-'): coin['Name'] for coin in cryptocompare_response.json()['Data'].values()}
    
    messari_response = requests.get('https://data.messari.io/api/v1/assets')
    messari_map = {coin['slug']: coin['id'] for coin in messari_response.json()['data']}

    return coingecko_map, coinmarketcap_map, cryptocompare_map, messari_map

# Fetch mappings
coingecko_map, coinmarketcap_map, cryptocompare_map, messari_map = generate_id_mappings()

# Function to fetch data from CoinGecko
def fetch_from_coingecko(coin_ids, current_prices):
    print(f"Fetching data from CoinGecko for {coin_ids}")
    ids = ",".join(coin_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        current_prices.update(response.json())
    except Exception as e:
        print(f"Error fetching from CoinGecko: {e}")

# Function to fetch data from CoinMarketCap
def fetch_from_coinmarketcap(coin_ids, current_prices):
    print(f"Fetching data from CoinMarketCap for {coin_ids}")
    ids = ",".join(coinmarketcap_map.get(coin, '') for coin in coin_ids if coin in coinmarketcap_map)
    if not ids:
        print(f"No valid CoinMarketCap IDs found for {coin_ids}")
        return
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        'X-CMC_PRO_API_KEY': API_KEYS['COINMARKETCAP_API_KEY']
    }
    params = {
        'symbol': ids,
        'convert': 'USD'
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        for coin in coin_ids:
            if coin in coinmarketcap_map:
                current_prices[coin] = data['data'][coinmarketcap_map[coin]]['quote']['USD']['price']
    except Exception as e:
        print(f"Error fetching from CoinMarketCap: {e}")

# Function to fetch data from CryptoCompare
def fetch_from_cryptocompare(coin_ids, current_prices):
    print(f"Fetching data from CryptoCompare for {coin_ids}")
    ids = ",".join(cryptocompare_map.get(coin, '') for coin in coin_ids if coin in cryptocompare_map)
    if not ids:
        print(f"No valid CryptoCompare IDs found for {coin_ids}")
        return
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={ids}&tsyms=USD&api_key={API_KEYS['CRYPTOCOMPARE_API_KEY']}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        for coin in coin_ids:
            if coin in cryptocompare_map:
                current_prices[coin] = response.json()[cryptocompare_map[coin]]['USD']
    except Exception as e:
        print(f"Error fetching from CryptoCompare: {e}")

# Function to fetch data from Messari
def fetch_from_messari(coin_ids, current_prices):
    print(f"Fetching data from Messari for {coin_ids}")
    ids = ",".join(messari_map.get(coin, '') for coin in coin_ids if coin in messari_map)
    if not ids:
        print(f"No valid Messari IDs found for {coin_ids}")
        return
    url = f"https://data.messari.io/api/v1/assets?{ids}"
    headers = {
        'x-messari-api-key': API_KEYS['MESSARI_API_KEY']
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        for coin in coin_ids:
            if coin in messari_map:
                current_prices[coin] = data['data'][messari_map[coin]]['metrics']['market_data']['price_usd']
    except Exception as e:
        print(f"Error fetching from Messari: {e}")

# Function to send message to Telegram
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
        print(f"Telegram message sent: {message}")
    except requests.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

# Function to load price history
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

# Function to save price history
def save_price_history(price_history, filepath):
    print(f"Saving price history to {filepath}")
    with open(filepath, 'w') as f:
        try:
            json.dump(price_history, f, indent=4)
            print(f"Saved price history to {filepath}")
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

        current_prices = dict(current_prices)
        print("Fetched current prices:", current_prices)

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
    history_file = os.getenv('PRICE_HISTORY_FILE', 'price_history.json')
    monitor_prices(history_file=history_file)
