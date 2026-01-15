import requests
import os
from bs4 import BeautifulSoup

# ========= 基本配置 =========
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PRODUCTS = [
    {
        "name": "角巴兔原皮",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782",
        "status_file": "status_43782.txt",
    },
    {
        "name": "txt雪娃",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "status_file": "status_51621.txt",
    },
]

# ========= 飞书通知 =========
def send_message(text):
    data = {
        "msg_type": "text",
        "content": {"text": text}
    }
    requests.post(FEISHU_WEBHOOK, json=data, timeout=10)

# ========= 网页最终裁决 =========
def get_status_from_html(product_url):
    r = requests.get(product_url, headers=HEADERS, timeout=15)
    html = r.text.lower()

    soup = BeautifulSoup(html, "html.parser")

    # 所有 button / a 都检查
    clickable_texts = [
        "add to cart",
        "buy now",
        "purchase",
    ]

    for tag in soup.find_all(["button", "a"]):
        text = (tag.get_text() or "").strip().lower()

        if any(t in text for t in clickable_texts):
            # 判断是否被禁用
            disabled = (
                tag.has_attr("disabled")
                or "disabled" in tag.get("class", [])
                or "sold out" in text
            )

            if not disabled:
                return "IN_STOCK"

    return "OUT_OF_STOCK"

# ========= 状态文件 =========
def read_last_status(file):
    if not os.path.exists(file):
        return None
    with open(file, "r") as f:
        return f.read().strip()

def write_status(file, status):
    with open(file, "w") as f:
        f.write(status)

# ========= 主逻辑 =========
def main():
    for product in PRODUCTS:
        current = get_status_from_html(product["url"])
        last = read_last_status(product["status_file"])

        # 第一次运行：一定提醒
        if last is None:
            send_message(
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{current}\n"
                f"{product['url']}"
            )

        # 无货 → 有货
        elif last == "OUT_OF_STOCK" and current == "IN_STOCK":
            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}\n"
                f"请尽快下单：\n"
                f"{product['url']}"
            )

        write_status(product["status_file"], current)

if __name__ == "__main__":
    main()
