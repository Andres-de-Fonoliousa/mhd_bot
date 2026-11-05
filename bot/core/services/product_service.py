import json
import os
import sqlite3
from bot.core.database import DB_PATH
from bot.core.services.api_client import APIClient


# Product categories we care about — maps our category keys to
# API category_name substrings for matching.
CATEGORY_MAP = {
    "cat_ff_subs": {
        "keywords": ["عضوية", "عضويات", "حزمة ترقية", "حزمة المستوى", "تصريح بوياه", "membership", "weekly", "monthly", "booyah"],
        "profit_key": "profit_ff_subs",
    },
    "cat_ff_gems": {
        "keywords": ["free fire", "فري فاير", "جواهر", "diamond"],
        "profit_key": "profit_ff_gems",
    },
    "cat_pubg_uc": {
        "keywords": ["pubg", "ببجي", "شدات", "uc"],
        "profit_key": "profit_pubg_uc",
    },
    "cat_social": {
        "keywords": ["instagram", "انستغرام", "social", "تواصل اجتماعي", "متابعين", "لايكات", "tiktok", "تيك توك", "twitter", "تويتر", "youtube", "يوتيوب", "telegram", "تلغرام", "سبوتي فاي"],
        "profit_key": "profit_ff_gems",
    },
}


class ProductService:
    def __init__(self, api_client: APIClient = None):
        self.api = api_client or APIClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def sync_products(self):
        raw = await self.api.get_products()
        if not isinstance(raw, list):
            print(f"Unexpected API response: {type(raw)}")
            return 0

        matched = []
        for item in raw:
            info = self._classify(item)
            if info:
                matched.append((item, info))

        if not matched:
            print("No relevant products found from API.")
            return 0

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        exchange_rate = self._get_exchange_rate(conn)
        print(f"Syncing with exchange rate: {exchange_rate} SYP/USD")

        counts = {}
        count = 0
        for item, info in matched:
            cat = info["category_key"]
            counts[cat] = counts.get(cat, 0) + 1
            margin = self._get_margin(info["profit_key"], conn)
            price_usd = float(item.get("price", 0))
            price_syp = int(price_usd * exchange_rate * margin)

            qv = item.get("qty_values") or {}
            min_qty = float(qv.get("min", 1)) if qv else 1
            max_qty = float(qv.get("max", 1)) if qv else 1

            price_syp = max(price_syp, 1)

            cursor.execute(
                """
                INSERT INTO services
                    (service_id, name, category, price, original_price,
                     api_service_id, is_active, min_qty, max_qty)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(service_id) DO UPDATE SET
                    price          = excluded.price,
                    original_price = excluded.original_price,
                    is_active      = 1,
                    min_qty        = excluded.min_qty,
                    max_qty        = excluded.max_qty
                """,
                (
                    f"api_{item['id']}",
                    item.get("name", ""),
                    info["category_key"],
                    price_syp,
                    price_usd,
                    str(item["id"]),
                    min_qty,
                    max_qty,
                ),
            )
            count += 1

        conn.commit()
        conn.close()
        cat_summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        print(f"Synced {count} products from API. [{cat_summary}]")
        return count

    def get_local_product_id(self, api_product_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT service_id FROM services WHERE api_service_id = ?",
            (str(api_product_id),),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_service_by_id(self, service_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT service_id, name, category, price, original_price, api_service_id, "
            "       min_qty, max_qty "
            "FROM services WHERE service_id = ?",
            (service_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "service_id": row[0],
                "name": row[1],
                "category": row[2],
                "price": row[3],
                "original_price": row[4],
                "api_service_id": row[5],
                "min_qty": row[6],
                "max_qty": row[7],
            }
        return None

    def get_services_by_category(self, category_key, limit=None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = (
            "SELECT service_id, name, category, price, original_price, api_service_id, "
            "       min_qty, max_qty "
            "FROM services WHERE category = ? AND is_active = 1 "
            "ORDER BY price ASC"
        )
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query, (category_key,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "service_id": r[0],
                "name": r[1],
                "category": r[2],
                "price": r[3],
                "original_price": r[4],
                "api_service_id": r[5],
                "min_qty": r[6],
                "max_qty": r[7],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _classify(self, item):
        cat_name = (item.get("category_name") or "").lower()
        prod_name = (item.get("name") or "").lower()
        combined = f"{cat_name} {prod_name}"

        for cat_key, mapping in CATEGORY_MAP.items():
            for kw in mapping["keywords"]:
                if kw in combined:
                    return {
                        "category_key": cat_key,
                        "profit_key": mapping["profit_key"],
                    }
        return None

    def _get_margin(self, profit_key, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (profit_key,))
        row = cursor.fetchone()
        return float(row[0]) if row else 1.02

    def _get_exchange_rate(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("exchange_rate",))
        row = cursor.fetchone()
        return float(row[0]) if row else 135.0
