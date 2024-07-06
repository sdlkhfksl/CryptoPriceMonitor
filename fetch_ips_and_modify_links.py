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
    existing_nodes = decoded_content.splitlines()
    logger.info(f"Found {len(existing_nodes)} existing vless nodes")

    if len(existing_nodes) == 0:
        logger.error("No existing vless nodes found in the decoded content.")
        print("No existing vless nodes found. Check script.log for details.")
    else:
        # List to store modified nodes
        modified_nodes = []

        # Select a random existing node to use as a template
        random_existing_node = random.choice(existing_nodes)

        # Generate new nodes for each backup IP
        for backup_ip in ip_list:
            match = re.search(r'(vless://[^@]+@)([^:]+)(:.+)', random_existing_node)
            if match:
                prefix = match.group(1)
                suffix = match.group(3)

                # Create new node with backup IP
                new_node = f"{prefix}{backup_ip}{suffix}"
                modified_nodes.append(new_node)

        # Append modified nodes to the original list
        all_nodes = existing_nodes + modified_nodes

        # Encode the updated list back to Base64
        new_subscription_content = "\n".join(all_nodes)
        new_subscription_base64 = base64.b64encode(new_subscription_content.encode('utf-8')).decode('utf-8')

        # Save the updated subscription link to a file
        try:
            with open('subscription_link.txt', 'w') as file:
                file.write(new_subscription_base64)
            logger.info("New subscription link saved to subscription_link.txt")
            print("New subscription link saved to subscription_link.txt")
            print("Base64 encoded content:")
            print(new_subscription_base64)
        except IOError as e:
            logger.error(f"Failed to write to subscription_link.txt: {e}")
            print(f"Failed to write to subscription_link.txt. Check script.log for details.")
else:
    logger.error(f"Failed to fetch subscription link, status code: {response.status_code}")
    print(f"Failed to fetch subscription link, status code: {response.status_code}")
