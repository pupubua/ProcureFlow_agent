from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Intent(str, Enum):
    INVENTORY = "inventory"
    SUPPLIER = "supplier"
    PURCHASE_ORDER = "purchase_order"
    ORDER_STATUS = "order_status"


class RoutingDecision(BaseModel):
    intents: list[Intent]
    entities: dict[str, Any] = Field(default_factory=dict)
    needs_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    confirmed: bool = False
    idempotency_key: str | None = None


class ChatResponse(BaseModel):
    status: str
    answer: str
    results: dict[str, Any] = Field(default_factory=dict)
    trace_id: str

