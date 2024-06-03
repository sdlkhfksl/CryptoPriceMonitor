import requests
import json
import os
import time
from multiprocessing import Process, Manager
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从环境变量中获取API密钥和其他配置信息
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
MESSARI_API_KEY = os.getenv("MESSARI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PRICE_HISTORY_FILE = os.getenv("PRICE_HISTORY_FILE", "price_history.json")

threshold = 0.05  # 5% price change threshold
time_window = 10 * 60  # 10 minutes in seconds

# 发送Telegram消息
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Telegram message sent: {message}")
    except requests.RequestException as e:
        logging.error(f"Error sending message to Telegram: {e}")

# 获取前20名的币种价格（1-20）
def fetch_from_coingecko(current_prices):
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 20,
        'page': 1,
        'sparkline': False
    })
    if response.status_code == 200:
        data = response.json()
        for coin in data:
            current_prices[coin['id']] = coin['current_price']
    else:
        logging.error(f"Error fetching from CoinGecko: {response.status_code}, {response.text}")

# 获取排名21-40的币种价格（21-40）
def fetch_from_coinmarketcap(current_prices):
    response = requests.get(f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest', params={
        'start': '21',
        'limit': '20',
        'convert': 'USD'
    }, headers={
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
    })
    if response.status_code == 200:
        data = response.json()['data']
        for coin in data:
            current_prices[coin['slug']] = coin['quote']['USD']['price']
    else:
        logging.error(f"Error fetching from CoinMarketCap: {response.status_code}, {response.text}")

# 获取排名41-60的币种价格（41-60）
def fetch_from_cryptocompare(current_prices):
    response = requests.get(f'https://min-api.cryptocompare.com/data/top/mktcapfull', params={
        'limit': 20,
        'tsym': 'USD',
        'page': 3
    }, headers={
        'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
    })
    if response.status_code == 200:
        data = response.json()['Data']
        for coin in data:
            coin_info = coin['CoinInfo']
            current_prices[coin_info['Name']] = coin['RAW']['USD']['PRICE']
    else:
        logging.error(f"Error fetching from CryptoCompare: {response.status_code}, {response.text}")

# 获取排名61-80的币种价格（61-80）
def fetch_from_messari(current_prices):
    response = requests.get(f'https://data.messari.io/api/v1/assets', params={
        'limit': 20,
        'page': 4,
        'sort': 'marketcap'
    }, headers={
        'x-messari-api-key': MESSARI_API_KEY
    })
    if response.status_code == 200:
        data = response.json()['data']
        for coin in data:
            current_prices[coin['slug']] = coin['metrics']['market_data']['price_usd']
    else:
        logging.error(f"Error fetching from Messari: {response.status_code}, {response.text}")

# 获取排名81-100的币种价格（81-100）
def fetch_from_coinpaprika(current_prices):
    response = requests.get('https://api.coinpaprika.com/v1/coins')
    if response.status_code == 200:
        data = response.json()[80:100]
        for coin in data:
            ticker_response = requests.get(f'https://api.coinpaprika.com/v1/tickers/{coin["id"]}')
            if ticker_response.status_code == 200:
                ticker_data = ticker_response.json()
                current_prices[coin['id']] = ticker_data['quotes']['USD']['price']
            else:
                logging.error(f"Error fetching from CoinPaprika ticker: {ticker_response.status_code}, {ticker_response.text}")
    else:
        logging.error(f"Error fetching from CoinPaprika: {response.status_code}, {response.text}")

# 保存价格历史
def save_price_history(price_history, file):
    with open(file, 'w') as f:
        json.dump(price_history, f, indent=4)

# 加载价格历史
def load_price_history(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

price_history = load_price_history(PRICE_HISTORY_FILE)

# 检查并处理价格变化
def check_price_changes():
    manager = Manager()
    current_prices = manager.dict()
    processes = [
        Process(target=fetch_from_coingecko, args=(current_prices,)),
        Process(target=fetch_from_coinmarketcap, args=(current_prices,)),
        Process(target=fetch_from_cryptocompare, args=(current_prices,)),
        Process(target=fetch_from_messari, args=(current_prices,)),
        Process(target=fetch_from_coinpaprika, args=(current_prices,))
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join()

    logging.info(f"Fetched current prices: {dict(current_prices)}")

    for coin, price in current_prices.items():
        if coin in price_history and len(price_history[coin]) >= 2:
            previous_timestamp = price_history[coin][-2]['timestamp']
            previous_price = price_history[coin][-2]['price']

            # Check if the previous price was recorded within the last 10 minutes
            if time.time() - previous_timestamp <= time_window:
                price_change = (price - previous_price) / previous_price
                if abs(price_change) >= threshold:
                    direction = "up" if price_change > 0 else "down"
                    message = f"Price of {coin} is {direction} by {price_change:.2%} over the last 10 minutes. Current price: ${price:.2f}"
                    send_telegram_message(message)

        if coin not in price_history:
            price_history[coin] = []
        price_history[coin].append({'timestamp': time.time(), 'price': price})

# 检查价格变化
check_price_changes()
# 保存价格历史
save_price_history(price_history, PRICE_HISTORY_FILE)
