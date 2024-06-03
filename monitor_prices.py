import requests
import json
import os
from datetime import datetime

# 从环境变量中获取API密钥和其他配置信息
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.json")

threshold = 0.05  # 5% price change threshold

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

# Function to fetch prices from CoinGecko for coins 1-20
def fetch_from_coingecko(current_prices):
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 20,
        'page': 1
    })
    if response.status_code == 200:
        data = response.json()
        for coin in data:
            current_prices[coin['id']] = coin['current_price']
    else:
        print(f"Error fetching from CoinGecko: {response.status_code}, {response.text}")

# Function to fetch prices from CoinMarketCap for coins 21-40
def fetch_from_coinmarketcap(current_prices):
    response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest', headers={
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
    }, params={
        'start': 21,
        'limit': 20,
        'convert': 'USD'
    })
    if response.status_code == 200:
        data = response.json().get('data', [])
        for coin in data:
            current_prices[coin['id']] = coin['quote']['USD']['price']
    else:
        print(f"Error fetching from CoinMarketCap: {response.status_code}, {response.text}")

# Function to fetch prices from CryptoCompare for coins 41-60
def fetch_from_cryptocompare(current_prices):
    response = requests.get('https://min-api.cryptocompare.com/data/top/mktcapfull', headers={
        'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
    }, params={
        'limit': 20,
        'tsym': 'USD',
        'page': 3
    })
    if response.status_code == 200:
        data = response.json().get('Data', [])
        for coin in data:
            symbol = coin['CoinInfo']['Name']
            current_prices[symbol] = coin['RAW']['USD']['PRICE']
    else:
        print(f"Error fetching from CryptoCompare: {response.status_code}, {response.text}")

# Function to fetch prices from Messari for coins 61-80
def fetch_from_messari(current_prices):
    response = requests.get('https://data.messari.io/api/v1/assets', headers={
        'x-messari-api-key': MESSARI_API_KEY
    }, params={
        'limit': 20,
        'page': 4
    })
    if response.status_code == 200:
        data = response.json().get('data', [])
        for coin in data:
            symbol = coin['slug']
            current_prices[symbol] = coin['metrics']['market_data']['price_usd']
    else:
        print(f"Error fetching from Messari: {response.status_code}, {response.text}")

# Function to fetch prices from CoinPaprika for coins 81-100
def fetch_from_coinpaprika(current_prices):
    response = requests.get('https://api.coinpaprika.com/v1/coins', params={
        'limit': 20,
        'page': 5
    })
    if response.status_code == 200:
        data = response.json()
        for coin in data:
            coin_id = coin['id']
            price_response = requests.get(f'https://api.coinpaprika.com/v1/tickers/{coin_id}')
            if price_response.status_code == 200:
                price_data = price_response.json()
                current_prices[coin_id] = price_data['quotes']['USD']['price']
            else:
                print(f"Error fetching price from CoinPaprika: {price_response.status_code}, {price_response.text}")
    else:
        print(f"Error fetching from CoinPaprika: {response.status_code}, {response.text}")

# Function to monitor prices and detect changes
def monitor_prices():
    current_prices = {}
    fetch_from_coingecko(current_prices)
    fetch_from_coinmarketcap(current_prices)
    fetch_from_cryptocompare(current_prices)
    fetch_from_messari(current_prices)
    fetch_from_coinpaprika(current_prices)

    # Load historical prices if available
    if os.path.exists(PRICE_HISTORY_FILE):
        with open(PRICE_HISTORY_FILE, 'r') as f:
            historical_prices = json.load(f)
    else:
        historical_prices = {}

    # Check for price changes and send alerts if necessary
    for coin, current_price in current_prices.items():
        if coin in historical_prices:
            historical_data = historical_prices[coin]
            if len(historical_data) >= 2:
                historical_price = historical_data[-2]['price']
                price_change = abs(current_price - historical_price) / historical_price
                if price_change >= threshold:
                    message = f"{coin} price changed by {price_change * 100:.2f}% from {historical_price} to {current_price}"
                    send_telegram_message(message)

        # Update historical prices
        if coin not in historical_prices:
            historical_prices[coin] = []
        historical_prices[coin].append({'timestamp': datetime.now().isoformat(), 'price': current_price})
        if len(historical_prices[coin]) > 3:
            historical_prices[coin].pop(0)

    # Save current prices for future comparison
    with open(PRICE_HISTORY_FILE, 'w') as f:
        json.dump(historical_prices, f, indent=4)

if __name__ == "__main__":
    monitor_prices()
