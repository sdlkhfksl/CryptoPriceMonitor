import requests
import re
import base64
import os

# 从环境变量中获取 VLESS 订阅链接
vless_subscription_url = os.getenv('VLESS_SUBSCRIPTION_URL')

# 定义其他 URL
url1 = "https://api.345673.xyz/get_data"
key = "o1zrmHAF"
url2 = "https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/main/index.html"
url3 = "https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestcf.txt"

def fetch_data(url, key=None):
    if key:
        response = requests.post(url, json={"key": key})
    else:
        response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"请求失败，状态码: {response.status_code}")
        return None

def extract_ips(data):
    ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    return re.findall(ip_pattern, data)

# 获取三个 URL 的数据
data1 = fetch_data(url1, key)
data2 = fetch_data(url2)
data3 = fetch_data(url3)

# 提取 IP 地址
ip_addresses = set()
if data1:
    ip_addresses.update(extract_ips(data1))

if data2:
    ip_addresses.update(extract_ips(data2))

if data3:
    ip_addresses.update(extract_ips(data3))

# 打印合并后的 IP 地址列表
print("合并后的 IP 地址列表:")
list1 = list(ip_addresses)
print(list1)

# 获取 VLESS 订阅链接的 base64 编码字符串
vless_response = requests.get(vless_subscription_url)
if vless_response.status_code != 200:
    print(f"请求失败，状态码: {vless_response.status_code}")
    exit()

vless_base64 = vless_response.text.split('#')[0]
vless_data = base64.b64decode(vless_base64).decode('utf-8')
vless_nodes = vless_data.splitlines()

# 筛选出非 IPv6 节点
list2 = [node for node in vless_nodes if '[' not in node]

# 替换 IP 并生成新的节点列表
new_vless_nodes = []
i = 0
while list1:
    ip = list1.pop(0)
    node = list2[i % len(list2)]
    original_ip = re.search(r'@(.+?):', node).group(1)
    new_node = node.replace(original_ip, ip)
    new_vless_nodes.append(new_node)
    i += 1

# 将新的节点添加到原有节点后面
all_vless_nodes = vless_nodes + new_vless_nodes
new_vless_data = "\n".join(all_vless_nodes)
new_vless_base64 = base64.b64encode(new_vless_data.encode('utf-8')).decode('utf-8')

# 将最终的 base64 编码字符串保存到 txt 文件
with open("new_vless_nodes.txt", "w") as f:
    f.write(new_vless_base64)

print("\n新的 VLESS 节点列表已保存到 new_vless_nodes.txt 文件中。")
