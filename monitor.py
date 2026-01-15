import requests
import os

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

PRODUCT_URL = "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782"
API_URL = "https://shop.weverse.io/api/v1/products/43782"

STATUS_FILE = "status.txt"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": PRODUCT_URL,
}

def send_message(text):
    data = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    requests.post(FEISHU_WEBHOOK, json=data, timeout=10)

def get_current_status():
    r = requests.get(API_URL, headers=HEADERS, timeout=10)

    # 👇 关键防御：不是 JSON 就直接当没货
    if not r.headers.get("Content-Type", "").startswith("application/json"):
        return "OUT_OF_STOCK"

    data = r.json()

    # 接口字段兜底判断
    if data.get("purchasable") is True:
        return "IN_STOCK"

    return "OUT_OF_STOCK"

def read_last_status():
    if not os.path.exists(STATUS_FILE):
        return None
    with open(STATUS_FILE, "r") as f:
        return f.read().strip()

def write_status(status):
    with open(STATUS_FILE, "w") as f:
        f.write(status)

def main():
    current = get_current_status()
    last = read_last_status()

    # 第一次运行：一定提醒
    if last is None:
        send_message(
            "📦 Weverse 商品监控已启动\n"
            f"当前状态：{current}\n"
            f"{PRODUCT_URL}"
        )

    # 从无货 → 有货：提醒
    elif last == "OUT_OF_STOCK" and current == "IN_STOCK":
        send_message(
            "🚨 Weverse 商品已补货！\n"
            "请尽快下单：\n"
            f"{PRODUCT_URL}"
        )

    write_status(current)

if __name__ == "__main__":
    main()
