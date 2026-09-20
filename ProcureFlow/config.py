from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv(
        "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    openai_model: str = os.getenv("OPENAI_MODEL", "qwen-plus")

    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "procureflow")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "procureflow_dev")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "procureflow")

    inventory_mcp_url: str = os.getenv("INVENTORY_MCP_URL", "http://127.0.0.1:8001/mcp")
    supplier_mcp_url: str = os.getenv("SUPPLIER_MCP_URL", "http://127.0.0.1:8002/mcp")
    purchase_order_mcp_url: str = os.getenv("PURCHASE_ORDER_MCP_URL", "http://127.0.0.1:8003/mcp")
    inventory_agent_url: str = os.getenv("INVENTORY_AGENT_URL", "http://127.0.0.1:5005")
    supplier_agent_url: str = os.getenv("SUPPLIER_AGENT_URL", "http://127.0.0.1:5006")
    purchase_order_agent_url: str = os.getenv("PURCHASE_ORDER_AGENT_URL", "http://127.0.0.1:5007")
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:9000")

    @property
    def mysql_config(self) -> dict[str, object]:
        return {
            "host": self.mysql_host,
            "port": self.mysql_port,
            "user": self.mysql_user,
            "password": self.mysql_password,
            "database": self.mysql_database,
            "autocommit": False,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
