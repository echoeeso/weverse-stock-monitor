import requests
import os

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

PRODUCTS = [
    {
        "name": "角巴兔原皮",
        "product_url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782",
        "api_url": "https://shop.weverse.io/api/v1/products/43782",
        "status_file": "status_43782.txt",
    },
    {
        "name": "txt雪娃",
        "product_url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "api_url": "https://shop.weverse.io/api/v1/products/51621",
        "status_file": "status_51621.txt",
    },
]

def send_message(text):
    data = {
        "msg_type": "text",
        "content": {"text": text}
    }
    requests.post(FEISHU_WEBHOOK, json=data, timeout=10)

import json
import re
import requests

def extract_sale_stocks(obj, results):
    """
    递归遍历 JSON，抓所有包含 saleStockId 的对象
    """
    if isinstance(obj, dict):
        if "saleStockId" in obj:
            results.append(obj)
        for v in obj.values():
            extract_sale_stocks(v, results)
    elif isinstance(obj, list):
        for item in obj:
            extract_sale_stocks(item, results)


def get_status_html(product):
    r = requests.get(
        product["product_url"],
        headers=HEADERS,
        timeout=15
    )

    html = r.text

    # 1️⃣ 提取 __NEXT_DATA__
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S
    )
    if not m:
        return "OUT_OF_STOCK", []

    data = json.loads(m.group(1))

    # 2️⃣ 全局搜索 saleStock
    sale_stocks = []
    extract_sale_stocks(data, sale_stocks)

    in_stock_skus = []

    for stock in sale_stocks:
        # SKU 名称多重兜底
        name = (
            stock.get("optionValue")
            or stock.get("optionName")
            or stock.get("name")
            or stock.get("displayName")
            or f"SKU-{stock.get('saleStockId')}"
        )

        # 是否可买（网页最终逻辑）
        purchasable = (
            stock.get("purchasable") is True
            or stock.get("canBuy") is True
            or stock.get("isSoldOut") is False
        )

        if purchasable:
            in_stock_skus.append(name)

    if in_stock_skus:
        return "IN_STOCK", sorted(set(in_stock_skus))

    return "OUT_OF_STOCK", []


def read_last_status(file):
    if not os.path.exists(file):
        return None
    with open(file, "r") as f:
        return f.read().strip()

def write_status(file, status):
    with open(file, "w") as f:
        f.write(status)

def main():
    for product in PRODUCTS:
        current, skus = get_status_html(product)
        last = read_last_status(product["status_file"])

        # 第一次运行：一定提醒
        if last is None:
            msg = (
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{current}\n"
            )
            if skus:
                msg += "可购买 SKU：\n" + "\n".join(skus) + "\n"
            msg += product["product_url"]

            send_message(msg)

        # 无 → 有：提醒
        elif last == "OUT_OF_STOCK" and current == "IN_STOCK":
            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}\n"
                f"可购买 SKU：\n"
                f"{chr(10).join(skus)}\n"
                f"{product['product_url']}"
            )

        write_status(product["status_file"], current)

if __name__ == "__main__":
    main()
