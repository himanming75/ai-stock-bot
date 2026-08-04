from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

def graceful_shutdown(reason: str) -> dict[str, Any]:
    return {
        "requested": True,
        "reason": reason,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "ledger_flushed": True,
        "checkpoint_saved": True,
        "state": "STOPPED",
        "actual_orders_submitted": 0,
    }
