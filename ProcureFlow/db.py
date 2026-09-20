from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from .config import Settings, get_settings


class MySQLRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @contextmanager
    def connection(self) -> Iterator[Any]:
        import mysql.connector

        conn = mysql.connector.connect(**self.settings.mysql_config)
        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
            finally:
                cursor.close()

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None


class PurchaseOrderRepository(MySQLRepository):
    def create_order(
        self,
        *,
        requester: str,
        supplier_id: int,
        material_code: str,
        quantity: int,
        unit_price: float,
        expected_date: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Create a procurement order after validating material and quote.

        Creating an inbound purchase order must not deduct or reserve current
        warehouse stock. Inventory changes only when goods are received.
        """
        with self.connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT po_no, status FROM purchase_orders WHERE idempotency_key=%s",
                    (idempotency_key,),
                )
                existing = cursor.fetchone()
                if existing:
                    conn.rollback()
                    return {"created": False, "reason": "idempotent_replay", **existing}

                cursor.execute(
                    "SELECT id AS material_id, name AS material_name FROM materials WHERE code=%s FOR UPDATE",
                    (material_code,),
                )
                material = cursor.fetchone()
                if not material:
                    raise ValueError(f"物料不存在: {material_code}")

                cursor.execute(
                    "SELECT COALESCE(SUM(available_qty), 0) AS current_available_qty FROM inventory WHERE material_id=%s",
                    (material["material_id"],),
                )
                current_available_qty = int(cursor.fetchone()["current_available_qty"])

                cursor.execute(
                    "SELECT id, unit_price FROM supplier_quotes WHERE supplier_id=%s AND material_id=%s AND valid_until>=CURRENT_DATE AND min_qty<=%s ORDER BY min_qty DESC LIMIT 1",
                    (supplier_id, material["material_id"], quantity),
                )
                quote = cursor.fetchone()
                if not quote:
                    raise ValueError("该供应商没有满足数量且在有效期内的报价")
                if abs(float(quote["unit_price"]) - unit_price) > 0.01:
                    raise ValueError(f"提交单价与有效报价不一致，当前报价为 {quote['unit_price']}")

                po_no = f"PO{datetime.now():%Y%m%d}{secrets.randbelow(100000):05d}"
                total_amount = round(quantity * unit_price, 2)
                cursor.execute(
                    """
                    INSERT INTO purchase_orders
                      (po_no, requester, supplier_id, status, total_amount, expected_date, idempotency_key)
                    VALUES (%s, %s, %s, 'PENDING_APPROVAL', %s, %s, %s)
                    """,
                    (po_no, requester, supplier_id, total_amount, expected_date, idempotency_key),
                )
                order_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO purchase_order_items
                      (purchase_order_id, material_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (order_id, material["material_id"], quantity, unit_price),
                )
                cursor.execute(
                    "INSERT INTO audit_logs (entity_type, entity_id, action, operator_name, detail) VALUES ('purchase_order', %s, 'CREATE', %s, %s)",
                    (order_id, requester, f"{material_code} x {quantity}"),
                )
                conn.commit()
                return {
                    "created": True,
                    "po_no": po_no,
                    "status": "PENDING_APPROVAL",
                    "material_name": material["material_name"],
                    "quantity": quantity,
                    "total_amount": total_amount,
                    "current_available_qty": current_available_qty,
                }
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
