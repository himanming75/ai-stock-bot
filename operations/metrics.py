from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any


def _process_metrics() -> dict[str, Any]:
    result = {
        "process_id": os.getpid(),
        "python_process_time_seconds": time.process_time(),
    }
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        result["maximum_resident_set_kb"] = int(usage.ru_maxrss)
    except Exception:
        result["maximum_resident_set_kb"] = None
    return result


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        return sum(1 for line in handle if line.strip())


def collect_metrics(root: Path) -> dict[str, Any]:
    p1 = root / "release/p1_broker_consolidation/actual"
    p3 = root / "release/p3_order_fill_portfolio_sync/actual"
    p4 = root / "release/p4_autonomous_paper_runtime/actual"
    ops = root / "release/operations_bundle/actual"

    heartbeat = {}
    heartbeat_path = p4 / "heartbeat.json"
    if heartbeat_path.exists():
        heartbeat = json.loads(
            heartbeat_path.read_text(encoding="utf-8-sig")
        )

    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "process": _process_metrics(),
        "runtime": {
            "heartbeat_state": heartbeat.get("state"),
            "heartbeat_cycle_number": heartbeat.get("cycle_number"),
            "heartbeat_observed_at": heartbeat.get("observed_at"),
        },
        "history_counts": {
            "operation_events": _count_jsonl(
                ops / "operations_events.jsonl"
            ),
            "order_events": _count_jsonl(
                p1 / "order_ledger.jsonl"
            ),
            "fill_events": _count_jsonl(
                p3 / "actual_fill_ledger.jsonl"
            ),
            "drift_events": _count_jsonl(
                p3 / "actual_drift_ledger.jsonl"
            ),
            "runtime_cycles": _count_jsonl(
                p4 / "cycle_ledger.jsonl"
            ),
        },
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_live_orders_submitted": 0,
    }
