from __future__ import annotations

from fastapi import FastAPI

from .orchestrator import ProcureFlowOrchestrator
from .schemas import ChatRequest, ChatResponse

app = FastAPI(title="ProcureFlow API", version="1.0.0")
orchestrator = ProcureFlowOrchestrator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "procureflow-api"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = await orchestrator.process(
        request.query,
        confirmed=request.confirmed,
        idempotency_key=request.idempotency_key,
    )
    return ChatResponse.model_validate(result)

