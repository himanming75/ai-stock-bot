from __future__ import annotations
import json
from pathlib import Path
from typing import Any


TERMS = {
    "retry": ("retry", "attempt"),
    "timeout": ("timeout", "timed out"),
    "rate_limit": ("rate_limit", "429", "rate limit"),
    "authentication": ("authentication", "401", "unauthorized"),
    "network": ("network", "connection", "socket"),
}


def collect_error_statistics(root: Path) -> dict[str, Any]:
    paths = [
        root / "release/operations_bundle/actual/operations_events.jsonl",
        root / "release/p1_broker_consolidation/actual/error_ledger.jsonl",
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "actual_drift_ledger.jsonl",
    ]
    counters = {name: 0 for name in TERMS}
    total_records = 0
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines():
            total_records += 1
            lower = line.lower()
            for name, terms in TERMS.items():
                if any(term in lower for term in terms):
                    counters[name] += 1
    return {
        "total_records_scanned": total_records,
        "counters": counters,
    }
