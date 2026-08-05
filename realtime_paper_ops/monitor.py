from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ALLOWED_TRANSITIONS = {
    "QUEUED_PREVIEW": {"VALIDATED_PREVIEW", "CANCELLED_PREVIEW"},
    "VALIDATED_PREVIEW": {"MONITORED_PREVIEW", "CANCELLED_PREVIEW"},
    "MONITORED_PREVIEW": {"COMPLETED_PREVIEW", "CANCELLED_PREVIEW"},
    "COMPLETED_PREVIEW": set(),
    "CANCELLED_PREVIEW": set(),
}


class OrderLifecycleMonitor:
    def __init__(self, ledger_path: Path) -> None:
        self.ledger_path = ledger_path

    def transition(
        self,
        *,
        queue_id: str,
        previous_state: str,
        new_state: str,
        reason: str,
    ) -> dict[str, Any]:
        allowed = new_state in ALLOWED_TRANSITIONS.get(
            previous_state, set()
        )
        if not allowed:
            raise ValueError(
                f"INVALID_TRANSITION:{previous_state}->{new_state}"
            )

        record = {
            "stage": "R20_ORDER_LIFECYCLE_MONITOR",
            "queue_id": queue_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "reason": reason,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "actual_broker_status_read": False,
            "actual_order_modified": False,
            "automatic_retry_enabled": False,
            "automatic_order_replay_enabled": False,
        }
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open(
            "a", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record
