from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ProcureFlow.services import InventoryService

mcp = FastMCP("ProcureFlow Inventory MCP", host="127.0.0.1", port=8001)
service = InventoryService()


@mcp.tool()
def query_inventory(
    material_code: str | None = None,
    material_name: str | None = None,
    warehouse: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """查询物料库存、安全库存水位和仓库分布。"""
    return service.query(material_code, material_name, warehouse, limit)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
