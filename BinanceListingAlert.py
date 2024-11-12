import requests
import time
import ccxt
from itertools import cycle
import json
from datetime import datetime


# 本地保存公告ID的文件
PROCESSED_IDS_FILE = "processed_ids.json"


# 从文件加载已处理的公告ID
def load_processed_ids():
    try:
        with open(PROCESSED_IDS_FILE, 'r') as file:
            return set(json.load(file))
    except FileNotFoundError:
        return set()


# 保存已处理的公告ID到文件
def save_processed_ids(processed_ids):
    with open(PROCESSED_IDS_FILE, 'w') as file:
        json.dump(list(processed_ids), file)


# 从本地文件加载代理
def load_proxies(filename):
    with open(filename, 'r') as file:
        proxies = [line.strip() for line in file if line.strip()]
    return proxies


# 将代理转换为 requests 格式
def get_proxies(proxy):
    ip, port, user, password = proxy.split(":")
    proxy_url = f"http://{user}:{password}@{ip}:{port}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


# 初始化代理池
proxy_list = load_proxies("proxies.txt")
proxy_pool = cycle(proxy_list)

# 初始化 ccxt 并设置 Gate.io API 密钥
gate = ccxt.gateio({
    'apiKey': '',  # 请替换为您的 API Key
    'secret': '',  # 请替换为您的 Secret Key
    'options': {
        'createMarketBuyOrderRequiresPrice': False  # 设置为 False，允许市价买单按总花费下单
    }
})

# 币安公告接口
url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=5"

# 加载已处理的公告ID
processed_ids = load_processed_ids()


# 购买指定代币的函数
def buy_token(token_symbol):
    # 构建交易对，默认对USDT
    symbol = f"{token_symbol}/USDT"

    try:
        # 加载市场数据，确保代币存在于Gate.io的市场列表
        markets = gate.load_markets()
        if symbol not in markets:
            print(f"{symbol} 不在 Gate.io 交易所上市")
            return

        # 直接按花费500 USDT进行市价买单
        order = gate.create_order(symbol, 'market', 'buy', amount=500)
        print(f"成功购买 {symbol}，总花费: 500 USDT")
        print("订单详情:", order)
    except Exception as e:
        print(f"购买 {symbol} 失败: {e}")


# 检查公告更新和执行购买
def check_for_updates_and_buy():
    global processed_ids
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在监控公告更新...")
    proxy = next(proxy_pool)  # 从代理池获取下一个代理
    proxies = get_proxies(proxy)

    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 检查公告列表
        catalogs = data['data']['catalogs']
        for catalog in catalogs:
            for article in catalog['articles']:
                article_id = article['id']

                # 如果是新公告，且尚未处理过
                if article_id not in processed_ids:
                    processed_ids.add(article_id)  # 标记公告为已处理
                    title = article['title']

                    # 提取代币符号（在括号中）
                    token_start = title.find('(')
                    token_end = title.find(')')
                    if token_start != -1 and token_end != -1:
                        token_symbol = title[token_start + 1:token_end]

                        # 执行市价买单操作
                        print(f"新公告发现，准备购买 {token_symbol}")
                        buy_token(token_symbol)

        # 更新已处理的公告ID文件
        save_processed_ids(processed_ids)

    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")


while True:
    start_time = time.time()  # 记录开始时间

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 轮询中...")
    check_for_updates_and_buy()

    # 计算剩余的时间
    elapsed_time = time.time() - start_time
    sleep_time = max(0, 1 - elapsed_time) 
    time.sleep(sleep_time)
