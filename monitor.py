import json
import time
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# ========== 基本配置 ==========

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/42a71dae-fd65-4bae-b4cf-440e4335e678"

PRODUCTS = [
    {
        "name": "角巴兔原皮",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/43782",
        "state_file": "state_43782.json",
    },
    {
        "name": "txt雪娃",
        "url": "https://shop.weverse.io/en/shop/USD/artists/3/sales/51621",
        "state_file": "state_51621.json",
    },
]

DEBUG = True


# ========== 飞书通知 ==========

def send_feishu(text: str):
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)


# ========== 状态读写 ==========

def load_state(path: str):
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_state(path: str, data: dict):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ========== 核心：网页 SKU 裁决 ==========

def get_sku_status_from_page(page):
    """
    返回：
    {
        "SKU 名字": True / False  # True = 可点击（可买）
    }
    """
    sku_status = {}

    # ⚠️ Weverse SKU 实际是 button / li / div 混合
    # 用最宽松但安全的方式抓
    sku_elements = page.query_selector_all(
        "button, li, div"
    )

    for el in sku_elements:
        text = (el.inner_text() or "").strip()

        if not text:
            continue

        # 过滤明显不是 SKU 的内容
        if len(text) > 40:
            continue
        if "sold" in text.lower() and len(text) > 10:
            continue

        try:
            disabled = el.is_disabled()
        except:
            disabled = False

        aria_disabled = el.get_attribute("aria-disabled") == "true"
        class_name = el.get_attribute("class") or ""

        is_disabled = (
            disabled
            or aria_disabled
            or "disabled" in class_name.lower()
            or "sold" in class_name.lower()
        )

        # 只记录“像 SKU 的东西”
        if text.isupper() or " " in text:
            sku_status[text] = not is_disabled

    return sku_status


# ========== 主流程 ==========

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for product in PRODUCTS:
            name = product["name"]
            url = product["url"]
            state_file = product["state_file"]

            print("\n======== DEBUG ========")
            print("商品：", name)

            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000)

            current_skus = get_sku_status_from_page(page)
            last_state = load_state(state_file)

            if DEBUG:
                print("当前 SKU：", current_skus)
                print("上一次 SKU：", last_state)

            # SKU 级变化检测
            newly_in_stock = []

            for sku, can_buy in current_skus.items():
                last_can_buy = last_state.get(sku, False)
                if can_buy and not last_can_buy:
                    newly_in_stock.append(sku)

            # 商品级兜底判断
            product_in_stock = any(current_skus.values())
            last_product_in_stock = any(last_state.values()) if last_state else False

            # 第一次运行
            if not last_state:
                send_feishu(
                    f"📦 Weverse 商品监控已启动\n"
                    f"商品：{name}\n"
                    f"当前状态：{'IN_STOCK' if product_in_stock else 'OUT_OF_STOCK'}\n"
                    f"{url}"
                )

            # SKU 级提醒（核心）
            if newly_in_stock:
                sku_text = "\n".join(f"✅ {s}" for s in newly_in_stock)
                send_feishu(
                    f"🚨 Weverse SKU 补货提醒\n\n"
                    f"商品：{name}\n"
                    f"可购买 SKU：\n{sku_text}\n\n"
                    f"{url}"
                )

            # 商品级兜底提醒
            elif (not last_product_in_stock) and product_in_stock:
                send_feishu(
                    f"🚨 Weverse 商品已可购买\n\n"
                    f"商品：{name}\n"
                    f"当前网页显示可下单\n\n"
                    f"{url}"
                )

            save_state(state_file, current_skus)

        browser.close()


if __name__ == "__main__":
    main()
