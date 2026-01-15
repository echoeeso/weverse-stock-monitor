import requests
import os
import json

# =========================
# 基础配置
# =========================

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"
DEBUG = False   # 调试 saleStockId ↔ SKU 名称时改成 True

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
        "state_file": "state_43782.json",
    },
    {
        "name": "txt雪娃",
        "product_url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "api_url": "https://shop.weverse.io/api/v1/products/51621",
        "state_file": "state_51621.json",
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
    """递归提取 saleStockId → SKU 名称"""
    if isinstance(obj, dict):
        if "saleStockId" in obj and "value" in obj:
            mapping[obj["saleStockId"]] = obj["value"]
        for v in obj.values():
            build_sku_name_map(v, mapping)
    elif isinstance(obj, list):
        for item in obj:
            build_sku_name_map(item, mapping)

def load_state(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def save_state(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

# =========================
# 核心兜底判断（重点）
# =========================

def is_stock_purchasable(stock):
    # 明确可买
    if stock.get("purchasable") is True:
        return True

    # 曾出现过的可买字段
    if stock.get("canBuy") is True:
        return True

    # 明确未售罄
    if stock.get("isSoldOut") is False:
        return True

    # 数量型字段兜底
    for key in ("stockQuantity", "purchasableQuantity", "quantity"):
        try:
            if int(stock.get(key, 0)) > 0:
                return True
        except Exception:
            pass

    # 状态兜底（部分商品只有这个）
    if stock.get("status") in ("ON_SALE", "SALE"):
        return True

    return False

# =========================
# 获取当前库存状态
# =========================

def get_current_state(product):
    r = requests.get(
        product["api_url"],
        headers={**HEADERS, "Referer": product["product_url"]},
        timeout=10
    )

    if not r.headers.get("Content-Type", "").startswith("application/json"):
        return {"status": "OUT_OF_STOCK", "skus": []}

    data = r.json()

    # SKU 名称映射
    sku_name_map = {}
    build_sku_name_map(data, sku_name_map)

    if DEBUG:
        print(f"\n[DEBUG] {product['name']} SKU 映射：")
        for k, v in sku_name_map.items():
            print(f"  {k} → {v}")

    available_skus = []

    for stock in data.get("saleStocks", []):
        if is_stock_purchasable(stock):
            sid = stock.get("saleStockId")
            name = sku_name_map.get(sid, f"SKU-{sid}")
            available_skus.append(name)

    status = "IN_STOCK" if available_skus else "OUT_OF_STOCK"

    return {
        "status": status,
        "skus": sorted(set(available_skus))
    }

# =========================
# 主流程（商品 + SKU 双提醒）
# =========================

def main():
    for product in PRODUCTS:
        current = get_current_state(product)
        last = load_state(product["state_file"])

        # 第一次运行
        if last is None:
            send_message(
                f"📦 Weverse 商品监控已启动\n"
                f"商品：{product['name']}\n"
                f"当前状态：{current['status']}\n"
                f"{product['product_url']}"
            )
            save_state(product["state_file"], current)
            continue

        # 商品级补货
        if last["status"] == "OUT_OF_STOCK" and current["status"] == "IN_STOCK":
            send_message(
                f"🚨 Weverse 商品已补货！\n"
                f"商品：{product['name']}\n\n"
                f"📦 可购买 SKU：\n" + "\n".join(current["skus"]) + "\n"
                f"{product['product_url']}"
            )

        # SKU 级补货
        new_skus = sorted(set(current["skus"]) - set(last.get("skus", [])))
        if new_skus:
            send_message(
                f"🧸 Weverse SKU 补货！\n"
                f"商品：{product['name']}\n"
                f"新增 SKU：\n" + "\n".join(new_skus) + "\n"
                f"{product['product_url']}"
            )

        save_state(product["state_file"], current)

if __name__ == "__main__":
    main()
