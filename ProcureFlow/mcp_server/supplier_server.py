from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ProcureFlow.services import SupplierService

mcp = FastMCP("ProcureFlow Supplier MCP", host="127.0.0.1", port=8002)
service = SupplierService()


@mcp.tool()
def query_supplier_quotes(
    material_code: str,
    quantity: int,
    supplier_name: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """查询指定物料和数量下仍有效的供应商报价，并按综合条件排序。"""
    return service.query_quotes(material_code, quantity, supplier_name, limit)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
