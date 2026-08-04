from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

def heartbeat(sequence: int, runtime_state: str) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "runtime_state": runtime_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "HEALTHY",
        "actual_orders_submitted": 0,
        "execution_authorized": False,
    }
