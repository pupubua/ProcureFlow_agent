from __future__ import annotations

import subprocess
import sys
import time


MODULES = [
    ["-m", "ProcureFlow.mcp_server.inventory_server"],
    ["-m", "ProcureFlow.mcp_server.supplier_server"],
    ["-m", "ProcureFlow.mcp_server.purchase_order_server"],
    ["-m", "ProcureFlow.a2a_server.inventory_agent"],
    ["-m", "ProcureFlow.a2a_server.supplier_agent"],
    ["-m", "ProcureFlow.a2a_server.purchase_order_agent"],
    ["-m", "ProcureFlow.jobs.sync_supplier_quotes"],
    ["-m", "uvicorn", "ProcureFlow.api:app", "--host", "127.0.0.1", "--port", "9000"],
]


def main() -> None:
    processes: list[subprocess.Popen] = []
    try:
        for args in MODULES:
            process = subprocess.Popen([sys.executable, *args])
            processes.append(process)
            time.sleep(0.4)
        print("ProcureFlow services started. Press Ctrl+C to stop.")
        while all(process.poll() is None for process in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
