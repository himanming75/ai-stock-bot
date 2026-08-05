from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any


LATENCY_FIELDS = (
    "latency_ms",
    "broker_latency_ms",
    "request_latency_ms",
    "elapsed_ms",
)


def _numbers(value: Any) -> list[Decimal]:
    result = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in LATENCY_FIELDS:
                try:
                    result.append(Decimal(str(item)))
                except Exception:
                    pass
            result.extend(_numbers(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(_numbers(item))
    return result


def collect_latency_statistics(root: Path) -> dict[str, Any]:
    files = [
        root / "release/operations_bundle/actual/operations_events.jsonl",
        root / "release/p1_broker_consolidation/actual/order_ledger.jsonl",
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "actual_order_state_ledger.jsonl",
    ]
    values = []
    for path in files:
        if not path.exists():
            continue
        for line in path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines():
            try:
                values.extend(_numbers(json.loads(line)))
            except Exception:
                continue

    values.sort()
    count = len(values)
    average = (
        sum(values, Decimal("0")) / count
        if count else Decimal("0")
    )
    p95 = (
        values[min(count - 1, int((count - 1) * 0.95))]
        if count else Decimal("0")
    )
    return {
        "sample_count": count,
        "average_ms": str(average),
        "minimum_ms": str(values[0] if values else Decimal("0")),
        "maximum_ms": str(values[-1] if values else Decimal("0")),
        "p95_ms": str(p95),
    }
