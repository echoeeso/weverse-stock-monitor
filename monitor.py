import requests

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

PRODUCT_URL = "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782"

def send_message(text):
    data = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    requests.post(FEISHU_WEBHOOK, json=data)

def check_stock():
    r = requests.get(PRODUCT_URL, timeout=10)
    if "Sold Out" not in r.text:
        send_message(f"🚨 Weverse 商品可能已补货！\n{PRODUCT_URL}")

if __name__ == "__main__":
    check_stock()
