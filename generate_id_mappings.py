import requests
import json
import os

COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
ID_MAPPINGS_FILE = "id_mappings.json"

def get_top_100_coins():
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False
    })
    return response.json()

def generate_id_mappings():
    coingecko_map = {coin['id']: coin['id'] for coin in get_top_100_coins()}

    coinmarketcap_response = requests.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map', headers={
        'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
    })
    coinmarketcap_map = {coin['slug']: coin['symbol'] for coin in coinmarketcap_response.json()['data']}
    
    cryptocompare_response = requests.get('https://min-api.cryptocompare.com/data/all/coinlist', headers={
        'authorization': f'Apikey {CRYPTOCOMPARE_API_KEY}'
    })
    cryptocompare_map = {
        coin['FullName'].lower().replace(' ', '-'): coin['Symbol']
        for coin in cryptocompare_response.json()['Data'].values()
        if int(coin['SortOrder']) <= 1000
    }
    
    messari_response = requests.get('https://data.messari.io/api/v1/assets')
    messari_map = {coin['slug']: coin['symbol'] for coin in messari_response.json()['data']}

    coinpaprika_response = requests.get('https://api.coinpaprika.com/v1/coins')
    coinpaprika_map = {coin['id']: coin['symbol'] for coin in coinpaprika_response.json()}

    mappings = {
        'coingecko': coingecko_map,
        'coinmarketcap': coinmarketcap_map,
        'cryptocompare': cryptocompare_map,
        'messari': messari_map,
        'coinpaprika': coinpaprika_map
    }

    with open(ID_MAPPINGS_FILE, 'w') as f:
        json.dump(mappings, f, indent=4)

generate_id_mappings()
print(f"ID Mappings successfully generated and saved to {ID_MAPPINGS_FILE}")
