import requests
import os
import json

# =========================
# 基础配置
# =========================

FEISHU_WEBHOOK = "你的飞书 Webhook"

DEBUG = True  # ← 想看 sku 映射就 True，用稳定了改成 False

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
        "status_file": "status_43782.json",
    },
    {
        "name": "txt雪娃",
        "product_url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "api_url": "https://shop.weverse.io/api/v1/products/51621",
        "status_file": "status_51621.json",
    },
]

# =========================
# 工具函数
# =========================

def send_message(text):
    requests.post(
        FEISHU_WEBHOOK,
        json={"msg_type": "text", "content": {"text": text}},
        timeout=10
    )

def build_sku_name_map(obj, mapping):
    """递归提取 saleStockId ↔ SKU 名称"""
    if isinstance(obj, dict):
        if "saleStockId" in obj and "value" in obj:
            mapping[obj["saleStockId"]] = obj["value"]
        for v in obj.values():
            build_sku_name_map(v, mapping)
    elif isinstance(obj, list):
        for item in obj:
            build_sku_name_map(item, mapping)

def read_last_state(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def write_state(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

# =========================
# 核心逻辑
# =========================

def get_stock_status(product):
    r = requests.get(
        product["api_url"],
        headers={**HEADERS, "Referer": product["product_url"]},
        timeout=10
    )

    if not r.headers.get("Content-Type", "").startswith("application/json"):
        return "OUT_OF_STOCK", []

    data = r.json()

    # 建立 SKU 映射
    sku_name_map = {}
    build_sku_name_map(data, sku_name_map)

    if DEBUG:
        print(f"\n[DEBUG] {product['name']} SKU 映射：")
        for k, v in sku_name_map.items():
            print(f"  saleStockId {k} → {v}")

    available = []

    for stock in data.get("saleStocks", []):
        if stock.get("purchasable") is True:
            sid = stock.get("saleStockId")
            name = sku_name_map.get(sid, f"SKU-{sid}")
            available.append(name)

    if available:
        return "IN_STOCK", available

    return "OUT_OF_STOCK", []

# =========================
# 主流程
# =========================

def main():
    for product in PRODUCTS:
        status, skus = get_stock_status(product)
        last = read_last_state(product["status_file"])

        current_state = {
            "status": status,
            "skus": skus
        }

        # 第一次运行
        if last is None:
            send_message(
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{status}\n"
                f"{product['product_url']}"
            )

        # 从无货 → 有货
        elif last["status"] == "OUT_OF_STOCK" and status == "IN_STOCK":
            sku_text = "\n".join(skus)
            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}\n"
                f"可购买 SKU：\n{sku_text}\n"
                f"{product['product_url']}"
            )

        write_state(product["status_file"], current_state)

if __name__ == "__main__":
    main()
