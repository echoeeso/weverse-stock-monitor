import requests
import os

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

PRODUCT_URL = "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782"
API_URL = "https://shop.weverse.io/api/v1/products/43782"

STATUS_FILE = "status.txt"

def send_message(text):
    data = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    requests.post(FEISHU_WEBHOOK, json=data)

def get_current_status():
    r = requests.get(API_URL, timeout=10)
    data = r.json()

    # 关键判断（字段名可能有轻微变化，但这个结构最常见）
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

    # 第一次运行
    if last is None:
        send_message(
            f"📦 Weverse 商品监控已启动\n"
            f"当前状态：{current}\n"
            f"{PRODUCT_URL}"
        )
    # 从无货 → 有货
    elif last == "OUT_OF_STOCK" and current == "IN_STOCK":
        send_message(
            f"🚨 Weverse 商品已补货！\n"
            f"请尽快下单：\n"
            f"{PRODUCT_URL}"
        )

    write_status(current)

if __name__ == "__main__":
    main()
