from __future__ import annotations

import asyncio

from python_a2a import A2AServer, AgentCard, AgentSkill, run_server

from ProcureFlow.a2a_server.common import call_mcp, complete, fail, parse_payload
from ProcureFlow.config import get_settings

settings = get_settings()

agent_card = AgentCard(
    name="InventoryQueryAgent",
    description="查询物料库存、占用量、安全库存和仓库分布",
    url=settings.inventory_agent_url,
    version="1.0.0",
    capabilities={"streaming": True, "memory": True},
    skills=[AgentSkill(
        name="query inventory",
        description="按物料编码、名称或仓库查询库存",
        examples=["查询 MAT-1001 的可用库存", "哪些物料低于安全库存"],
    )],
)


class InventoryQueryServer(A2AServer):
    def __init__(self) -> None:
        super().__init__(agent_card=agent_card)

    def handle_task(self, task):
        payload = parse_payload(task)
        arguments = {
            key: payload[key]
            for key in ("material_code", "material_name", "warehouse", "limit")
            if payload.get(key) not in (None, "")
        }
        try:
            result = asyncio.run(call_mcp(settings.inventory_mcp_url, "query_inventory", arguments))
            return complete(task, {"status": "success", "data": result})
        except Exception as exc:
            return fail(task, f"库存查询失败: {exc}")


if __name__ == "__main__":
    run_server(InventoryQueryServer(), host="127.0.0.1", port=5005)

