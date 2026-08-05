from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import QueuedOrder


class SafeOrderQueue:
    def __init__(self, path: Path) -> None:
        self.path = path

    def enqueue(
        self,
        *,
        routed_order: dict[str, Any],
    ) -> QueuedOrder:
        checks = {
            "route_allowed": routed_order.get("route_allowed") is True,
            "submit_flag_off": routed_order.get("submit_allowed") is False,
            "paper_mode": routed_order.get("broker_mode") == "paper",
            "notional_positive": (
                Decimal(str(routed_order.get("routed_notional", "0"))) > 0
            ),
        }
        if not all(checks.values()):
            raise ValueError(
                "QUEUE_REJECTED:" +
                ",".join(k for k, v in checks.items() if not v)
            )

        raw = json.dumps(
            routed_order,
            sort_keys=True,
            separators=(",", ":"),
        )
        queue_id = "r19-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]
        order = QueuedOrder(
            queue_id=queue_id,
            candidate_id=str(routed_order.get("candidate_id", "")),
            account_id=str(routed_order.get("account_id", "")),
            symbol=str(routed_order.get("symbol", "")),
            side=str(routed_order.get("side", "")),
            order_type=str(routed_order.get("order_type", "")),
            time_in_force=str(routed_order.get("time_in_force", "")),
            notional=Decimal(str(routed_order.get("routed_notional", "0"))),
            state="QUEUED_PREVIEW",
            dispatch_allowed=False,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                **order.as_json(),
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "actual_dispatch_performed": False,
            }, sort_keys=True) + "\n")
        return order

    def dispatch(self, queue_id: str) -> None:
        raise RuntimeError(f"ORDER_DISPATCH_DISABLED:{queue_id}")
