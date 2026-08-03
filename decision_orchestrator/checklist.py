from __future__ import annotations
from typing import Any

def build_checklist(
    gates: dict[str, Any],
    plans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    duplicate_count = sum(1 for row in plans if row.get("state") == "BLOCKED_DUPLICATE")
    skipped_count = sum(1 for row in plans if row.get("state") == "SKIPPED")
    planned_count = sum(1 for row in plans if row.get("state") == "PLANNED")
    return [
        {"item": "META_STRATEGY_GATE", "passed": gates.get("checks", {}).get("meta_strategy_ready", False)},
        {"item": "RISK_APPROVAL", "passed": gates.get("checks", {}).get("risk_approved", False)},
        {"item": "PAPER_DECISION_ALLOWED", "passed": gates.get("checks", {}).get("paper_decision_allowed", False)},
        {"item": "DUPLICATE_PROTECTION", "passed": duplicate_count == 0, "duplicate_count": duplicate_count},
        {"item": "PLANNED_ORDER_COUNT", "passed": planned_count > 0, "planned_count": planned_count},
        {"item": "SKIPPED_PLAN_REVIEW", "passed": skipped_count == 0, "skipped_count": skipped_count},
        {"item": "BROKER_WRITE_DISABLED", "passed": True},
        {"item": "LIVE_TRADING_DISABLED", "passed": True},
        {"item": "MANUAL_APPROVAL_REQUIRED", "passed": False},
    ]
