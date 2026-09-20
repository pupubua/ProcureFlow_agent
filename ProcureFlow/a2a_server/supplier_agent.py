from __future__ import annotations

import asyncio

from python_a2a import A2AServer, AgentCard, AgentSkill, run_server

from ProcureFlow.a2a_server.common import call_mcp, complete, fail, parse_payload, require_input
from ProcureFlow.config import get_settings

settings = get_settings()

agent_card = AgentCard(
    name="SupplierQuoteAgent",
    description="查询供应商有效报价并综合价格、交期和履约率排序",
    url=settings.supplier_agent_url,
    version="1.0.0",
    capabilities={"streaming": True, "memory": True},
    skills=[AgentSkill(
        name="compare supplier quotes",
        description="按物料和数量查询、比较供应商报价",
        examples=["比较 MAT-1001 采购 100 件的供应商报价"],
    )],
)


class SupplierQuoteServer(A2AServer):
    def __init__(self) -> None:
        super().__init__(agent_card=agent_card)

    def handle_task(self, task):
        payload = parse_payload(task)
        missing = [name for name in ("material_code", "quantity") if not payload.get(name)]
        if missing:
            return require_input(task, f"询价还需要字段: {', '.join(missing)}")
        arguments = {
            key: payload[key]
            for key in ("material_code", "quantity", "supplier_name", "limit")
            if payload.get(key) not in (None, "")
        }
        try:
            result = asyncio.run(call_mcp(settings.supplier_mcp_url, "query_supplier_quotes", arguments))
            return complete(task, {"status": "success", "data": result})
        except Exception as exc:
            return fail(task, f"供应商询价失败: {exc}")


if __name__ == "__main__":
    run_server(SupplierQuoteServer(), host="127.0.0.1", port=5006)

