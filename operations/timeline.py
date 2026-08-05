from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path, source: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception:
            continue
        value["_source"] = source
        result.append(value)
    return result


def build_timeline(root: Path, limit: int = 200) -> list[dict[str, Any]]:
    sources = [
        (
            root / "release/operations_bundle/actual/"
                   "operations_events.jsonl",
            "operations",
        ),
        (
            root / "release/p1_broker_consolidation/actual/"
                   "order_ledger.jsonl",
            "orders",
        ),
        (
            root / "release/p3_order_fill_portfolio_sync/actual/"
                   "actual_fill_ledger.jsonl",
            "fills",
        ),
        (
            root / "release/p3_order_fill_portfolio_sync/actual/"
                   "actual_drift_ledger.jsonl",
            "drifts",
        ),
        (
            root / "release/p4_autonomous_paper_runtime/actual/"
                   "cycle_ledger.jsonl",
            "runtime_cycles",
        ),
    ]
    events = []
    for path, source in sources:
        events.extend(_read_jsonl(path, source))

    def key(value):
        return str(
            value.get("observed_at")
            or value.get("created_at")
            or value.get("updated_at")
            or ""
        )

    return sorted(events, key=key)[-limit:]
