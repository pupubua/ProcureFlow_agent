from __future__ import annotations

import re


class UnsafeSQL(ValueError):
    """Raised when model-generated SQL violates the read-only policy."""


_BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|replace|call|load|outfile|dumpfile)\b",
    flags=re.IGNORECASE,
)
_TABLE = re.compile(r"\b(?:from|join)\s+`?([a-zA-Z_][\w]*)`?", flags=re.IGNORECASE)


def validate_readonly_sql(sql: str, allowed_tables: set[str], max_rows: int = 100) -> str:
    """Validate and cap LLM-generated SQL before it reaches MySQL.

    This deliberately supports only a single SELECT statement and a strict table
    allowlist. All write operations go through parameterized domain services.
    """
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned or not re.match(r"^select\b", cleaned, flags=re.IGNORECASE):
        raise UnsafeSQL("只允许执行 SELECT 查询")
    if ";" in cleaned or "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise UnsafeSQL("不允许多语句或 SQL 注释")
    if _BLOCKED.search(cleaned):
        raise UnsafeSQL("检测到写操作关键字")

    referenced = {name.lower() for name in _TABLE.findall(cleaned)}
    allowlist = {name.lower() for name in allowed_tables}
    if not referenced or not referenced.issubset(allowlist):
        raise UnsafeSQL(f"查询表不在白名单中: {sorted(referenced - allowlist)}")

    limit_match = re.search(r"\blimit\s+(\d+)\s*$", cleaned, flags=re.IGNORECASE)
    if limit_match:
        if int(limit_match.group(1)) > max_rows:
            cleaned = re.sub(
                r"\blimit\s+\d+\s*$", f"LIMIT {max_rows}", cleaned, flags=re.IGNORECASE
            )
        return cleaned
    return f"{cleaned} LIMIT {max_rows}"

