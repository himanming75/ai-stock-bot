from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


class PaperSessionCoordinator:
    def create(
        self,
        *,
        runtime_session: dict[str, Any],
        market_state: dict[str, Any],
    ) -> dict[str, Any]:
        checks = {
            "runtime_session_complete": (
                runtime_session.get("state") == "PREVIEW_SESSION_COMPLETE"
            ),
            "paper_mode": (
                runtime_session.get("broker_mode") == "paper"
            ),
            "market_state_present": bool(market_state),
            "broker_network_disabled": (
                runtime_session.get("broker_network_enabled") is False
            ),
            "broker_write_disabled": (
                runtime_session.get("broker_write_enabled") is False
            ),
        }
        raw = json.dumps(
            {
                "runtime_session_id": runtime_session.get("session_id", ""),
                "market_state": market_state,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        session_id = "r16-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]
        return {
            "stage": "R16_PAPER_SESSION_COORDINATOR",
            "paper_session_id": session_id,
            "runtime_session_id": runtime_session.get("session_id", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "state": "PAPER_SESSION_PREPARED",
            "actual_session_started": False,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
        }
