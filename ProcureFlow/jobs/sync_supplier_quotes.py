from __future__ import annotations

import json
import time
from pathlib import Path

import schedule

from ProcureFlow.db import MySQLRepository
from ProcureFlow.logging_config import get_logger

logger = get_logger(__name__)
FEED_PATH = Path(__file__).resolve().parents[2] / "data" / "supplier_quotes.json"


def sync_quotes(repository: MySQLRepository | None = None) -> int:
    """Import a mock supplier feed; replace this adapter with ERP/SRM API calls in production."""
    repository = repository or MySQLRepository()
    if not FEED_PATH.exists():
        logger.info("No supplier quote feed found: %s", FEED_PATH)
        return 0
    payload = json.loads(FEED_PATH.read_text(encoding="utf-8"))
    synced = 0
    with repository.connection() as conn:
        cursor = conn.cursor()
        try:
            for quote in payload:
                cursor.execute(
                    """
                    INSERT INTO supplier_quotes (supplier_id, material_id, min_qty, unit_price, lead_time_days, valid_until)
                    SELECT s.id, m.id, %s, %s, %s, %s
                    FROM suppliers s JOIN materials m
                    WHERE s.code=%s AND m.code=%s
                    ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price), lead_time_days=VALUES(lead_time_days),
                                            valid_until=VALUES(valid_until), updated_at=NOW()
                    """,
                    (
                        quote["min_qty"], quote["unit_price"], quote["lead_time_days"],
                        quote["valid_until"], quote["supplier_code"], quote["material_code"],
                    ),
                )
                synced += cursor.rowcount > 0
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    logger.info("Supplier quote sync completed: %s rows", synced)
    return synced


def main() -> None:
    sync_quotes()
    schedule.every(30).minutes.do(sync_quotes)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()

