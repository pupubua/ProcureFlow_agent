from __future__ import annotations

import asyncio
import json
import uuid

from python_a2a import (
    A2AClient,
    A2AServer,
    AgentCard,
    AgentSkill,
    Message,
    MessageRole,
    Task,
    TextContent,
    run_server,
)

from ProcureFlow.a2a_server.common import call_mcp, complete, fail, parse_payload, require_input
from ProcureFlow.config import get_settings

settings = get_settings()

agent_card = AgentCard(
    name="PurchaseOrderAgent",
    description="跨 Agent 核验库存和报价，在人工确认后幂等创建采购单",
    url=settings.purchase_order_agent_url,
    version="1.0.0",
    capabilities={"streaming": True, "memory": True},
    skills=[AgentSkill(
        name="create purchase order",
        description="库存与报价核验、订单预览、人工确认、幂等下单",
        examples=["为 MAT-1001 创建 100 件采购单"],
    )],
)


async def ask_agent(url: str, payload: dict) -> dict:
    client = A2AClient(url)
    message = Message(content=TextContent(text=json.dumps(payload, ensure_ascii=False)), role=MessageRole.USER)
    response = await client.send_task_async(Task(id=f"task-{uuid.uuid4()}", message=message.to_dict()))
    state = getattr(response.status.state, "value", response.status.state)
    if str(state).lower() != "completed":
        message_data = response.status.message or {}
        raise ValueError(message_data.get("content", {}).get("text", "依赖 Agent 未完成"))
    return json.loads(response.artifacts[0]["parts"][0]["text"])


async def run_prechecks(payload: dict) -> tuple[dict, dict]:
    return await asyncio.gather(
        ask_agent(settings.inventory_agent_url, {"material_code": payload["material_code"]}),
        ask_agent(settings.supplier_agent_url, {
            "material_code": payload["material_code"],
            "quantity": payload["quantity"],
        }),
    )


class PurchaseOrderServer(A2AServer):
    REQUIRED = ("requester", "supplier_id", "material_code", "quantity", "unit_price", "expected_date")

    def __init__(self) -> None:
        super().__init__(agent_card=agent_card)

    def handle_task(self, task):
        payload = parse_payload(task)
        if payload.get("action") == "status":
            if not payload.get("po_no"):
                return require_input(task, "请提供采购单号，例如 PO2026092000001")
            try:
                result = asyncio.run(call_mcp(
                    settings.purchase_order_mcp_url,
                    "get_purchase_order_status",
                    {"po_no": payload["po_no"]},
                ))
                return complete(task, {"status": "success", "data": result})
            except Exception as exc:
                return fail(task, f"采购单状态查询失败: {exc}")

        missing = [name for name in self.REQUIRED if payload.get(name) in (None, "")]
        if missing:
            return require_input(task, f"创建采购单还需要字段: {', '.join(missing)}")
        if not payload.get("confirmed"):
            preview = {name: payload[name] for name in self.REQUIRED}
            return require_input(task, f"请确认采购单信息后重新提交 confirmed=true：{json.dumps(preview, ensure_ascii=False)}")

        payload.setdefault("idempotency_key", f"po-{uuid.uuid4()}")
        try:
            inventory, quotes = asyncio.run(run_prechecks(payload))
            result = asyncio.run(call_mcp(
                settings.purchase_order_mcp_url,
                "create_purchase_order",
                {key: payload[key] for key in (*self.REQUIRED, "idempotency_key", "confirmed")},
            ))
            return complete(task, {
                "status": "success",
                "precheck": {"inventory": inventory, "quotes": quotes},
                "order": result,
            })
        except Exception as exc:
            return fail(task, f"采购单创建失败: {exc}")


if __name__ == "__main__":
    run_server(PurchaseOrderServer(), host="127.0.0.1", port=5007)
