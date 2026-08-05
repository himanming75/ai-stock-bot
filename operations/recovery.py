from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def build_recovery_snapshot(root: Path) -> dict[str, Any]:
    paths = {
        "p4_checkpoint": (
            root / "release/p4_autonomous_paper_runtime/actual/"
                   "runtime_checkpoint.json"
        ),
        "p4_cycle_registry": (
            root / "release/p4_autonomous_paper_runtime/actual/"
                   "cycle_registry.json"
        ),
        "p3_fill_registry": (
            root / "release/p3_order_fill_portfolio_sync/actual/"
                   "actual_fill_registry.json"
        ),
        "p2_order_registry": (
            root / "release/p1_broker_consolidation/actual/"
                   "order_idempotency_registry.json"
        ),
    }

    snapshot = {
        "stage": "O2_RECOVERY",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "safe_to_auto_resume": False,
        "automatic_broker_restart_enabled": False,
        "automatic_order_replay_enabled": False,
        "required_action": "OPERATOR_REVIEW_THEN_P4_PREFLIGHT",
        "actual_live_orders_submitted": 0,
    }

    for name, path in paths.items():
        if path.exists():
            try:
                snapshot["sources"][name] = {
                    "present": True,
                    "value": json.loads(
                        path.read_text(encoding="utf-8-sig")
                    ),
                }
            except Exception as exc:
                snapshot["sources"][name] = {
                    "present": True,
                    "read_error": str(exc),
                }
        else:
            snapshot["sources"][name] = {"present": False}

    return snapshot
