import requests
import re
import random

# URLs to fetch IPs from
urls = [
    "https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/main/index.html",
    "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt",
    "https://api.345673.xyz/get_data"
]

# Fetch IPs from URLs
ip_list = set()  # Using a set to avoid duplicates

for url in urls:
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text
        
        # Extract IPv4 addresses using regex
        ipv4_addresses = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', content)
        
        # Add to the set of IPs
        ip_list.update(ipv4_addresses)

# Additional IPs from key URL (assuming JSON format)
key_url = "https://api.345673.xyz/get_data"
key_params = {"key": "o1zrmHAF"}
key_response = requests.get(key_url, params=key_params)

if key_response.status_code == 200:
    key_data = key_response.json()
    additional_ips = key_data.get('ips', [])
    ip_list.update(additional_ips)

# Now `ip_list` contains all unique IPv4 addresses

# Fetch and modify subscription link
subscription_url = "https://sp.codewith.fun/sub/89b3cbba-e6ac-485a-9481-976a0415eab9#BPB-Normal"
response = requests.get(subscription_url)

if response.status_code == 200:
    # Parse existing vless nodes
    existing_nodes = re.findall(r'vless://[^"]+', response.text)

    # Modify IPv4 addresses in nodes with random IPs from ip_list
    modified_nodes = []
    for node in existing_nodes:
        # Replace IPv4 in `node` with a random IP from `ip_list`
        random_ip = random.choice(list(ip_list))
        modified_node = re.sub(r'@[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:', f'@{random_ip}:', node)
        modified_nodes.append(modified_node)

    # Generate new subscription link
    new_subscription_link = re.sub(r'vless://[^"]+', lambda _: modified_nodes.pop(0), response.text)

    # Save new subscription link to a file
    with open('subscription_link.txt', 'w') as file:
        file.write(new_subscription_link)

    print("New subscription link saved to subscription_link.txt")
else:
    print("Failed to fetch subscription link.")
