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

def get_status(product):
    r = requests.get(
        product["api_url"],
        headers={**HEADERS, "Referer": product["product_url"]},
        timeout=10
    )

    if not r.headers.get("Content-Type", "").startswith("application/json"):
        return "OUT_OF_STOCK"

    data = r.json()
    if data.get("purchasable") is True:
        return "IN_STOCK"

    return "OUT_OF_STOCK"

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
        current = get_status(product)
        last = read_last_status(product["status_file"])

        # 第一次运行：一定提醒
        if last is None:
            send_message(
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{current}\n"
                f"{product['product_url']}"
            )

        # 从无货 → 有货：提醒
        elif last == "OUT_OF_STOCK" and current == "IN_STOCK":
            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}\n"
                f"请尽快下单：\n"
                f"{product['product_url']}"
            )

        write_status(product["status_file"], current)

if __name__ == "__main__":
    main()
