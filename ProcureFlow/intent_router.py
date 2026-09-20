from __future__ import annotations

import json
import re
from typing import Any

from .config import Settings, get_settings
from .schemas import Intent, RoutingDecision


class RuleBasedIntentRouter:
    """Deterministic fallback used when an LLM is unavailable."""

    def route(self, query: str, confirmed: bool = False) -> RoutingDecision:
        intents: list[Intent] = []
        if any(word in query for word in ("库存", "现货", "可用量", "仓库", "缺货")):
            intents.append(Intent.INVENTORY)
        if any(word in query for word in ("供应商", "询价", "报价", "交期", "比价")):
            intents.append(Intent.SUPPLIER)
        if any(word in query for word in ("创建采购单", "下采购单", "采购订单", "下单")):
            intents.append(Intent.PURCHASE_ORDER)
        if any(word in query for word in ("订单状态", "采购单状态", "审批进度")):
            intents.append(Intent.ORDER_STATUS)
        if not intents:
            intents = [Intent.INVENTORY]

        entities: dict[str, Any] = {}
        code = re.search(r"\b(?:MAT|M)-?\d{3,}\b", query, flags=re.IGNORECASE)
        if code:
            entities["material_code"] = code.group(0).upper()
        quantity = re.search(r"(?:采购|需要|数量|买)\s*(\d+)\s*(?:个|件|套|台|只|根)?", query)
        if quantity:
            entities["quantity"] = int(quantity.group(1))
        po_no = re.search(r"\bPO\d{8}\d{5}\b", query, flags=re.IGNORECASE)
        if po_no:
            entities["po_no"] = po_no.group(0).upper()

        missing: list[str] = []
        if Intent.PURCHASE_ORDER in intents:
            required = ("material_code", "quantity", "supplier_id", "unit_price", "expected_date", "requester")
            missing = [name for name in required if name not in entities]
        return RoutingDecision(
            intents=list(dict.fromkeys(intents)),
            entities=entities,
            needs_confirmation=Intent.PURCHASE_ORDER in intents and not confirmed,
            missing_fields=missing,
        )


class LLMIntentRouter:
    SYSTEM_PROMPT = """你是企业采购意图路由器。仅返回 JSON：
{"intents":["inventory|supplier|purchase_order|order_status"],"entities":{}}
识别物料编码、物料名称、数量、仓库、供应商、supplier_id、unit_price、expected_date、requester、po_no。
不要臆造用户未提供的字段；组合问题可以返回多个 intents。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.fallback = RuleBasedIntentRouter()

    def route(self, query: str, confirmed: bool = False) -> RoutingDecision:
        if not self.settings.openai_api_key:
            return self.fallback.route(query, confirmed)
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                temperature=0,
            )
            response = llm.invoke([
                ("system", self.SYSTEM_PROMPT),
                ("human", query),
            ])
            text = str(response.content).strip().removeprefix("```json").removesuffix("```").strip()
            payload = json.loads(text)
            decision = RoutingDecision.model_validate(payload)
            decision.needs_confirmation = Intent.PURCHASE_ORDER in decision.intents and not confirmed
            if Intent.PURCHASE_ORDER in decision.intents:
                required = ("material_code", "quantity", "supplier_id", "unit_price", "expected_date", "requester")
                decision.missing_fields = [name for name in required if name not in decision.entities]
            return decision
        except Exception:
            return self.fallback.route(query, confirmed)

