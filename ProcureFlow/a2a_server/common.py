from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from python_a2a import TaskState, TaskStatus


def task_text(task: Any) -> str:
    content = (task.message or {}).get("content", {})
    return content.get("text", "") if isinstance(content, dict) else ""


def parse_payload(task: Any) -> dict[str, Any]:
    text = task_text(task).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"query": text}
    except json.JSONDecodeError:
        return {"query": text}


def complete(task: Any, result: Any) -> Any:
    text = json.dumps(result, ensure_ascii=False, default=str)
    task.artifacts = [{"parts": [{"type": "text", "text": text}]}]
    task.status = TaskStatus(state=TaskState.COMPLETED)
    return task


def require_input(task: Any, message: str) -> Any:
    task.status = TaskStatus(
        state=TaskState.INPUT_REQUIRED,
        message={"role": "agent", "content": {"text": message}},
    )
    return task


def fail(task: Any, message: str) -> Any:
    task.status = TaskStatus(
        state=TaskState.FAILED,
        message={"role": "agent", "content": {"text": message}},
    )
    return task


async def call_mcp(url: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if getattr(result, "isError", False):
                raise RuntimeError(result.content[0].text if result.content else "MCP 工具执行失败")
            if not result.content:
                return None
            text = result.content[0].text
            try:
                return json.loads(text)
            except (TypeError, json.JSONDecodeError):
                return text

