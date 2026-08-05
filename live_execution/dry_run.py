from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


class LiveDryRunTransport:
    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "dry_run": True,
            "accepted": True,
            "broker_network_used": False,
            "broker_submission_attempted": False,
            "simulated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

    def cancel(self, order_id: str) -> dict[str, Any]:
        return {
            "dry_run": True,
            "action": "cancel",
            "order_id": order_id,
            "broker_network_used": False,
        }

    def replace(self, order_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return {
            "dry_run": True,
            "action": "replace",
            "order_id": order_id,
            "changes": changes,
            "broker_network_used": False,
        }
