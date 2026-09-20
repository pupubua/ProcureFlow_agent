from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ProcureFlow.services import PurchaseOrderService

mcp = FastMCP("ProcureFlow Purchase Order MCP", host="127.0.0.1", port=8003)
service = PurchaseOrderService()


@mcp.tool()
def create_purchase_order(
    requester: str,
    supplier_id: int,
    material_code: str,
    quantity: int,
    unit_price: float,
    expected_date: str,
    idempotency_key: str,
    confirmed: bool = False,
) -> dict:
    """在人工确认后创建采购订单；工具内置库存锁定、报价校验和幂等控制。"""
    return service.create(
        confirmed=confirmed,
        requester=requester,
        supplier_id=supplier_id,
        material_code=material_code,
        quantity=quantity,
        unit_price=unit_price,
        expected_date=expected_date,
        idempotency_key=idempotency_key,
    )


@mcp.tool()
def get_purchase_order_status(po_no: str) -> dict:
    """按采购单号查询审批与履约状态。"""
    result = service.get_status(po_no)
    return result or {"found": False, "po_no": po_no}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
