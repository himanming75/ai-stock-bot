from __future__ import annotations
from typing import Any

def evaluate_gates(
    meta_result: dict[str, Any],
    plans: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    planned = [row for row in plans if row.get("state") == "PLANNED"]
    total_notional = sum(float(row.get("planned_notional", 0.0)) for row in planned)
    maximum_total = float(policy.get("maximum_total_planned_notional", 50000.0))
    maximum_orders = int(policy.get("maximum_planned_orders", 5))
    required_decisions = set(policy.get(
        "allowed_paper_decisions",
        [
            "PAPER_TRADE_MINIMAL_EXPOSURE",
            "PAPER_TRADE_REDUCED_EXPOSURE",
            "PAPER_TRADE_NORMAL_EXPOSURE",
        ],
    ))

    checks = {
        "meta_strategy_ready": meta_result.get("state") == "META_STRATEGY_ENGINE_READY",
        "paper_decision_allowed": meta_result.get("paper_decision") in required_decisions,
        "risk_approved": meta_result.get("risk_approved") is True,
        "planned_orders_present": len(planned) > 0,
        "planned_order_count_within_limit": len(planned) <= maximum_orders,
        "planned_notional_within_limit": total_notional <= maximum_total,
        "order_submission_disabled": meta_result.get("order_submission_enabled") is False,
        "live_trading_disabled": meta_result.get("live_trading_enabled") is False,
        "paper_only": meta_result.get("paper_only") is True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
        "planned_order_count": len(planned),
        "total_planned_notional": round(total_notional, 4),
        "maximum_planned_orders": maximum_orders,
        "maximum_total_planned_notional": maximum_total,
    }
