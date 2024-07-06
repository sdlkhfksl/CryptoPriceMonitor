import requests
import re
import random
import base64
import logging

# Configure logging to both console and file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('script.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# URLs to fetch IPs from
urls = [
    "https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/main/index.html",
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt",
    "https://api.345673.xyz/get_data"
]

# Fetch IPs from URLs
ip_list = set()  # Using a set to avoid duplicates

for url in urls:
    logger.info(f"Fetching IPs from URL: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text
        
        # Extract IPv4 addresses using regex
        ipv4_addresses = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', content)
        
        # Add to the set of IPs
        ip_list.update(ipv4_addresses)
        logger.info(f"Found {len(ipv4_addresses)} IPv4 addresses")

# Additional IPs from key URL (assuming JSON format)
key_url = "https://api.345673.xyz/get_data"
key_params = {"key": "o1zrmHAF"}

logger.info(f"Fetching additional IPs from {key_url}")
key_response = requests.get(key_url, params=key_params)

if key_response.status_code == 200:
    key_data = key_response.json()
    additional_ips = key_data.get('ips', [])
    ip_list.update(additional_ips)
    logger.info(f"Found additional {len(additional_ips)} IPs from key URL")

# Now `ip_list` contains all unique IPv4 addresses

# Fetch and decode subscription link
subscription_url = "https://sp.codewith.fun/sub/89b3cbba-e6ac-485a-9481-976a0415eab9#BPB-Normal"

logger.info(f"Fetching subscription link from {subscription_url}")
response = requests.get(subscription_url)

if response.status_code == 200:
    # Decode Base64 content
    base64_content = response.content.strip()
    decoded_content = base64.b64decode(base64_content).decode('utf-8')

    # Parse vless nodes from decoded content
    existing_nodes = re.findall(r'vless://[^"]+', decoded_content)
    logger.info(f"Found {len(existing_nodes)} existing vless nodes")

    # Modify IPv4 addresses in nodes with random IPs from ip_list
    modified_nodes = []
    for node in existing_nodes:
        # Replace IPv4 in `node` with a random IP from `ip_list`
        random_ip = random.choice(list(ip_list))
        modified_node = re.sub(r'@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:', f'@{random_ip}:', node)
        modified_nodes.append(modified_node)

    # Generate new subscription link
    new_subscription_link = re.sub(r'vless://[^"]+', lambda _: modified_nodes.pop(0), decoded_content)

    # Save new subscription link to a file
    with open('subscription_link.txt', 'w') as file:
        file.write(new_subscription_link)
        logger.info("New subscription link saved to subscription_link.txt")

    print("New subscription link saved to subscription_link.txt")
else:
    logger.error("Failed to fetch subscription link")
    print("Failed to fetch subscription link.")
