from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "strategy_selection": result,
        "network_used": False,
        "order_submission_allowed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
