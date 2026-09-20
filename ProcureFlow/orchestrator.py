from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from .config import Settings, get_settings
from .intent_router import LLMIntentRouter
from .logging_config import get_logger
from .schemas import Intent

logger = get_logger(__name__)


class ProcureFlowOrchestrator:
    AGENT_NAMES = {
        Intent.INVENTORY: "InventoryQueryAgent",
        Intent.SUPPLIER: "SupplierQuoteAgent",
        Intent.PURCHASE_ORDER: "PurchaseOrderAgent",
        Intent.ORDER_STATUS: "PurchaseOrderAgent",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.router = LLMIntentRouter(self.settings)
        self._network = None

    def _get_network(self):
        if self._network is None:
            from python_a2a import AgentNetwork

            network = AgentNetwork(name="ProcureFlow采购协同网络")
            network.add("InventoryQueryAgent", self.settings.inventory_agent_url)
            network.add("SupplierQuoteAgent", self.settings.supplier_agent_url)
            network.add("PurchaseOrderAgent", self.settings.purchase_order_agent_url)
            self._network = network
        return self._network

    async def _dispatch(self, intent: Intent, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        from python_a2a import Message, MessageRole, Task, TextContent

        agent_name = self.AGENT_NAMES[intent]
        agent = self._get_network().get_agent(agent_name)
        if intent == Intent.ORDER_STATUS:
            payload = {**payload, "action": "status"}
        message = Message(
            content=TextContent(text=json.dumps(payload, ensure_ascii=False)),
            role=MessageRole.USER,
        )
        task = Task(id=f"task-{uuid.uuid4()}", message=message.to_dict())
        response = await agent.send_task_async(task)
        state = str(getattr(response.status.state, "value", response.status.state)).lower()
        if state == "completed":
            return intent.value, json.loads(response.artifacts[0]["parts"][0]["text"])
        status_message = response.status.message or {}
        return intent.value, {
            "status": state,
            "message": status_message.get("content", {}).get("text", "Agent 未返回结果"),
        }

    async def process(
        self,
        query: str,
        *,
        confirmed: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        trace_id = str(uuid.uuid4())
        decision = self.router.route(query, confirmed)
        payload = {**decision.entities, "confirmed": confirmed}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        if decision.missing_fields:
            return {
                "status": "input_required",
                "answer": f"还需要补充：{', '.join(decision.missing_fields)}。",
                "results": {"routing": decision.model_dump(mode="json")},
                "trace_id": trace_id,
            }
        if decision.needs_confirmation:
            return {
                "status": "input_required",
                "answer": "采购单属于写操作，请核对物料、数量、供应商、单价和交期后确认。",
                "results": {"preview": payload},
                "trace_id": trace_id,
            }

        dispatched = await asyncio.gather(
            *(self._dispatch(intent, payload) for intent in decision.intents),
            return_exceptions=True,
        )
        results: dict[str, Any] = {}
        for item in dispatched:
            if isinstance(item, Exception):
                results[f"error_{len(results) + 1}"] = {"status": "error", "message": str(item)}
            else:
                results[item[0]] = item[1]
        answer = self._summarize(query, results)
        logger.info("trace_id=%s intents=%s", trace_id, [i.value for i in decision.intents])
        return {"status": "success", "answer": answer, "results": results, "trace_id": trace_id}

    def _summarize(self, query: str, results: dict[str, Any]) -> str:
        if not self.settings.openai_api_key:
            return json.dumps(results, ensure_ascii=False, default=str, indent=2)
        try:
            from langchain_openai import ChatOpenAI

            from .prompts import SUMMARY_PROMPT

            llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                temperature=0.1,
            )
            response = llm.invoke([
                ("system", SUMMARY_PROMPT),
                ("human", f"用户问题：{query}\nAgent结果：{json.dumps(results, ensure_ascii=False, default=str)}"),
            ])
            return str(response.content)
        except Exception as exc:
            logger.warning("LLM summary failed: %s", exc)
            return json.dumps(results, ensure_ascii=False, default=str, indent=2)
