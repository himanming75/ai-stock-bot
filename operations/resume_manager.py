from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .health_score import calculate_health_score
from .scheduler_monitor import scheduler_status
from .watchdog import evaluate_watchdog


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_resume_plan(root: Path) -> dict[str, Any]:
    kill_switch = _read_json(
        root / "release/p1_broker_consolidation/actual/kill_switch.json",
        {"kill_switch_active": True, "reason": "MISSING"},
    )
    p4_checkpoint = _read_json(
        root / "release/p4_autonomous_paper_runtime/actual/"
               "runtime_checkpoint.json",
        {},
    )
    p2 = _read_json(
        root / "release/p2_actual_paper_execution/actual/"
               "p2_actual_validation.json",
        {"validated": False},
    )
    p3 = _read_json(
        root / "release/p3_order_fill_portfolio_sync/actual/"
               "p3_actual_validation.json",
        {"validated": False},
    )

    watchdog = evaluate_watchdog(root)
    scheduler = scheduler_status(root)
    health = calculate_health_score(root)

    checks = {
        "checkpoint_present": bool(p4_checkpoint),
        "watchdog_pass": watchdog.get("status") == "PASS",
        "scheduler_pass": scheduler.get("status") == "PASS",
        "health_not_blocked": health.get("state") in {"HEALTHY", "DEGRADED"},
        "kill_switch_readable": "kill_switch_active" in kill_switch,
        "p2_actual_validation_present": p2.get("validated") is True,
        "p3_actual_validation_present": p3.get("validated") is True,
    }

    blockers = [name for name, passed in checks.items() if not passed]
    operator_review_required = True
    safe_to_prepare_resume = not blockers

    plan = {
        "stage": "O4_RESUME_PLAN",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "blockers": blockers,
        "safe_to_prepare_resume": safe_to_prepare_resume,
        "operator_review_required": operator_review_required,
        "automatic_resume_enabled": False,
        "automatic_order_replay_enabled": False,
        "automatic_broker_restart_enabled": False,
        "required_sequence": [
            "RUN_P4_ACTUAL_RUNTIME_PREFLIGHT",
            "REVIEW_KILL_SWITCH_AND_CHECKPOINT",
            "REVIEW_OPEN_ORDERS_AND_POSITIONS",
            "CONFIRM_NO_DUPLICATE_CYCLE",
            "START_NEW_RUNTIME_SESSION",
        ],
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    return plan
