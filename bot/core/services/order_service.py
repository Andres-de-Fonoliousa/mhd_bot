import asyncio
import json
import uuid
from datetime import datetime, timezone
import sqlite3
from bot.core.database import DB_PATH
from bot.core.services.api_client import APIClient, InsufficientBalanceError, DuplicateOrderError


class OrderService:
    def __init__(self, api_client: APIClient = None):
        self.api = api_client or APIClient()

    async def create_order(self, api_product_id, qty, player_id, chat_id=None, product_name="", any_key=None):
        order_uuid = str(uuid.uuid4())
        raw = await self.api.create_order(
            product_id=api_product_id,
            qty=qty,
            player_id=player_id,
            order_uuid=order_uuid,
            any_key=any_key,
        )
        self._save_order(raw, order_uuid, api_product_id, qty, player_id, chat_id, product_name)
        return {
            "order_uuid": order_uuid,
            "status": raw.get("status"),
            "data": raw.get("data"),
        }

    async def check_order(self, order_uuid):
        raw = await self.api.check_order(order_uuid)
        entries = raw.get("data", [])
        if entries:
            self._update_order_status(order_uuid, entries[0].get("status"))
        return raw

    async def wait_for_order(self, order_uuid, max_retries=15, interval=5):
        for attempt in range(max_retries):
            result = await self.check_order(order_uuid)
            entries = result.get("data", [])
            if not entries:
                return {"status": "unknown", "data": result}
            entry = entries[0]
            status = entry.get("status")
            if status == "accept":
                return {"status": "accept", "data": entry}
            if status == "reject":
                return {"status": "reject", "data": entry, "reason": entry.get("replay_api")}
            if attempt < max_retries - 1:
                await asyncio.sleep(interval)
        return {"status": "timeout", "data": entry}

    def _parse_error_reason(self, raw_json):
        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            msg = data.get("message") or ""
            replay = (data.get("data") or {}).get("replay_api") or ""
            return replay or msg or ""
        except (json.JSONDecodeError, TypeError, AttributeError):
            return ""

    def get_order(self, order_uuid):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT order_uuid, api_product_id, qty, player_id, status, "
            "created_at, chat_id, product_name, raw_response "
            "FROM api_orders WHERE order_uuid = ?",
            (order_uuid,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "order_uuid": row[0],
                "api_product_id": row[1],
                "qty": row[2],
                "player_id": row[3],
                "status": row[4],
                "created_at": row[5],
                "chat_id": row[6],
                "product_name": row[7],
                "error_reason": self._parse_error_reason(row[8]),
            }
        return None

    def get_user_orders(self, chat_id, limit=20):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT order_uuid, api_product_id, qty, player_id, status, "
            "created_at, product_name, raw_response "
            "FROM api_orders WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "order_uuid": r[0],
                "api_product_id": r[1],
                "qty": r[2],
                "player_id": r[3],
                "status": r[4],
                "created_at": r[5],
                "product_name": r[6],
                "error_reason": self._parse_error_reason(r[7]),
            }
            for r in rows
        ]

    def get_all_orders(self, limit=50, status=None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        sel = ("SELECT order_uuid, api_product_id, qty, player_id, status, "
               "created_at, chat_id, product_name, raw_response "
               "FROM api_orders")
        if status:
            if isinstance(status, (list, tuple)):
                placeholders = ",".join("?" * len(status))
                cursor.execute(
                    f"{sel} WHERE status IN ({placeholders}) ORDER BY created_at DESC LIMIT ?",
                    (*status, limit),
                )
            else:
                cursor.execute(
                    f"{sel} WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                )
        else:
            cursor.execute(
                f"{sel} ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "order_uuid": r[0],
                "api_product_id": r[1],
                "qty": r[2],
                "player_id": r[3],
                "status": r[4],
                "created_at": r[5],
                "chat_id": r[6],
                "product_name": r[7],
                "error_reason": self._parse_error_reason(r[8]),
            }
            for r in rows
        ]

    def _save_order(self, raw, order_uuid, api_product_id, qty, player_id, chat_id=None, product_name=""):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        data_block = raw.get("data") or {}
        status = data_block.get("status", raw.get("status", "unknown"))
        cursor.execute(
            """
            INSERT OR IGNORE INTO api_orders
                (order_uuid, api_product_id, qty, player_id, status, raw_response,
                 chat_id, product_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (order_uuid, api_product_id, qty, player_id, status, json.dumps(raw),
             chat_id, product_name, now, now),
        )
        conn.commit()
        conn.close()

    def _update_order_status(self, order_uuid, status):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE api_orders SET status = ?, updated_at = ? WHERE order_uuid = ?",
            (status, now, order_uuid),
        )
        conn.commit()
        conn.close()
