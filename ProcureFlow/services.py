from __future__ import annotations

from datetime import date
from typing import Any

from .db import MySQLRepository, PurchaseOrderRepository


class InventoryService:
    def __init__(self, repository: MySQLRepository | None = None) -> None:
        self.repository = repository or MySQLRepository()

    def query(
        self,
        material_code: str | None = None,
        material_name: str | None = None,
        warehouse: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if material_code:
            clauses.append("m.code=%s")
            params.append(material_code)
        if material_name:
            clauses.append("m.name LIKE %s")
            params.append(f"%{material_name}%")
        if warehouse:
            clauses.append("i.warehouse LIKE %s")
            params.append(f"%{warehouse}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        safe_limit = max(1, min(int(limit), 100))
        sql = f"""
            SELECT m.code AS material_code, m.name AS material_name, m.unit,
                   i.warehouse, i.on_hand_qty, i.reserved_qty, i.available_qty,
                   m.safety_stock,
                   CASE WHEN i.available_qty < m.safety_stock THEN 'LOW' ELSE 'NORMAL' END AS stock_level
            FROM inventory i
            JOIN materials m ON m.id=i.material_id
            {where}
            ORDER BY CASE WHEN i.available_qty < m.safety_stock THEN 0 ELSE 1 END, m.code
            LIMIT {safe_limit}
        """
        return self.repository.fetch_all(sql, tuple(params))


class SupplierService:
    def __init__(self, repository: MySQLRepository | None = None) -> None:
        self.repository = repository or MySQLRepository()

    def query_quotes(
        self,
        material_code: str,
        quantity: int,
        supplier_name: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        clauses = ["m.code=%s", "q.min_qty<=%s", "q.valid_until>=CURRENT_DATE", "s.status='ACTIVE'"]
        params: list[Any] = [material_code, quantity]
        if supplier_name:
            clauses.append("s.name LIKE %s")
            params.append(f"%{supplier_name}%")
        safe_limit = max(1, min(int(limit), 100))
        sql = f"""
            SELECT s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name,
                   s.rating, s.on_time_rate, q.unit_price, q.min_qty, q.lead_time_days,
                   q.valid_until, ROUND(q.unit_price * %s, 2) AS total_amount
            FROM supplier_quotes q
            JOIN suppliers s ON s.id=q.supplier_id
            JOIN materials m ON m.id=q.material_id
            WHERE {' AND '.join(clauses)}
            ORDER BY q.unit_price ASC, s.rating DESC, q.lead_time_days ASC
            LIMIT {safe_limit}
        """
        return self.repository.fetch_all(sql, tuple([quantity, *params]))


class PurchaseOrderService:
    REQUIRED_FIELDS = {
        "requester",
        "supplier_id",
        "material_code",
        "quantity",
        "unit_price",
        "expected_date",
        "idempotency_key",
    }

    def __init__(self, repository: PurchaseOrderRepository | None = None) -> None:
        self.repository = repository or PurchaseOrderRepository()

    def create(self, confirmed: bool, **payload: Any) -> dict[str, Any]:
        missing = sorted(self.REQUIRED_FIELDS - {key for key, value in payload.items() if value not in (None, "")})
        if missing:
            return {"created": False, "reason": "missing_fields", "missing_fields": missing}
        if not confirmed:
            return {
                "created": False,
                "reason": "confirmation_required",
                "message": "写入采购单前需要人工确认",
                "preview": payload,
            }
        if int(payload["quantity"]) <= 0 or float(payload["unit_price"]) <= 0:
            raise ValueError("采购数量和单价必须大于 0")
        if date.fromisoformat(str(payload["expected_date"])) < date.today():
            raise ValueError("期望交付日期不能早于今天")
        return self.repository.create_order(
            requester=str(payload["requester"]),
            supplier_id=int(payload["supplier_id"]),
            material_code=str(payload["material_code"]),
            quantity=int(payload["quantity"]),
            unit_price=float(payload["unit_price"]),
            expected_date=str(payload["expected_date"]),
            idempotency_key=str(payload["idempotency_key"]),
        )

    def get_status(self, po_no: str) -> dict[str, Any] | None:
        return self.repository.fetch_one(
            """
            SELECT p.po_no, p.status, p.requester, p.total_amount, p.expected_date,
                   s.name AS supplier_name, p.created_at
            FROM purchase_orders p JOIN suppliers s ON s.id=p.supplier_id
            WHERE p.po_no=%s
            """,
            (po_no,),
        )
