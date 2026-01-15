import requests
import os
from bs4 import BeautifulSoup
import json

# ================== 配置 ==================
FEISHU_WEBHOOK = "你的飞书 Webhook"

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
        "sale_id": "43782",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782",
        "status_file": "status_43782.txt",
        "sku_file": "sku_43782.json",
    },
    {
        "name": "txt雪娃",
        "sale_id": "51621",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "status_file": "status_51621.txt",
        "sku_file": "sku_51621.json",
    },
]

# ================== 飞书 ==================
def send_message(text):
    data = {"msg_type": "text", "content": {"text": text}}
    requests.post(FEISHU_WEBHOOK, json=data, timeout=10)

# ================== 网页最终裁决 ==================
def html_in_stock(product_url):
    r = requests.get(product_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    main = soup.find("main")
    if not main:
        return False

    keywords = ["add to cart", "buy now", "purchase"]

    for tag in main.find_all(["button", "a"]):
        text = (tag.get_text() or "").strip().lower()
        if any(k in text for k in keywords):
            if (
                not tag.has_attr("disabled")
                and "disabled" not in tag.get("class", [])
                and "sold out" not in text
            ):
                return True

    return False

# ================== API：只用于 SKU 展示 ==================
def fetch_sku_names(sale_id):
    url = f"https://shop.weverse.io/api/v1/products/{sale_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if not r.headers.get("Content-Type", "").startswith("application/json"):
            return []
        data = r.json()
    except Exception:
        return []

    names = []

    for stock in data.get("saleStocks", []):
        name = (
            stock.get("name")
            or stock.get("optionValue")
            or stock.get("label")
            or f"SKU-{stock.get('saleStockId')}"
        )

        purchasable = (
            stock.get("purchasable") is True
            or stock.get("canBuy") is True
            or stock.get("isSoldOut") is False
        )

        if purchasable:
            names.append(name)

    return sorted(set(names))

# ================== 文件工具 ==================
def read_text(file):
    if not os.path.exists(file):
        return None
    with open(file, "r") as f:
        return f.read().strip()

def write_text(file, content):
    with open(file, "w") as f:
        f.write(content)

def read_json(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return json.load(f)

def write_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== 主逻辑 ==================
def main():
    for product in PRODUCTS:
        in_stock = html_in_stock(product["url"])
        current_status = "IN_STOCK" if in_stock else "OUT_OF_STOCK"
        last_status = read_text(product["status_file"])

        current_skus = fetch_sku_names(product["sale_id"]) if in_stock else []
        last_skus = read_json(product["sku_file"])

        # 第一次运行
        if last_status is None:
            sku_text = ""
            if current_skus:
                sku_text = "\n可选 SKU：\n" + "\n".join(f"- {s}" for s in current_skus)

            send_message(
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{current_status}"
                f"{sku_text}\n"
                f"{product['url']}"
            )

        # 商品级补货
        elif last_status == "OUT_OF_STOCK" and current_status == "IN_STOCK":
            sku_text = ""
            if current_skus:
                sku_text = "\n可选 SKU：\n" + "\n".join(f"- {s}" for s in current_skus)

            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}"
                f"{sku_text}\n\n"
                f"{product['url']}"
            )

        # SKU 级新增提醒
        if in_stock:
            new_skus = sorted(set(current_skus) - set(last_skus))
            for sku in new_skus:
                send_message(
                    f"🆕 SKU 可购买提醒\n"
                    f"商品：{product['name']}\n"
                    f"SKU：{sku}\n\n"
                    f"{product['url']}"
                )

        write_text(product["status_file"], current_status)
        write_json(product["sku_file"], current_skus)

if __name__ == "__main__":
    main()
