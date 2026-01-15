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
    html = r.text

    # 只有明确出现“可购买按钮”才提醒
    if ("Add to Cart" in html) or ("Buy Now" in html):
        send_message(
            "🚨 Weverse 商品【确认可能可购买】！\n"
            "请立刻打开链接查看：\n"
            f"{PRODUCT_URL}"
        )

if __name__ == "__main__":
    check_stock()
