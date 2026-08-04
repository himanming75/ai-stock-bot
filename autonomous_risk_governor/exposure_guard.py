from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .exposure import evaluate_total_exposure


def run_guard(
    policy_result: dict[str, Any],
    account: dict[str, Any],
    positions: list[dict[str, Any]],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    policy = policy_result["policy"]

    proposed_order_notional = (
        proposal.get("estimated_notional")
        if proposal.get("estimated_notional") is not None
        else proposal.get("proposal", {}).get("estimated_notional", 0)
    )

    evaluation = evaluate_total_exposure(
        equity=account.get("equity"),
        positions=positions,
        proposed_order_notional=proposed_order_notional,
        maximum_total_exposure_pct=policy.get("maximum_total_exposure_pct"),
    )

    state = (
        "TOTAL_EXPOSURE_GUARD_BLOCKED"
        if evaluation["breached"]
        else "TOTAL_EXPOSURE_GUARD_WARNING"
        if evaluation["warning"]
        else "TOTAL_EXPOSURE_GUARD_ACTIVE"
    )

    risk_operations_allowed = (
        policy_result.get("risk_operations_allowed") is True
        and evaluation["new_risk_allowed"]
        and account.get("status") in {"ACTIVE", None}
        and not bool(account.get("account_blocked", False))
        and not bool(account.get("trading_blocked", False))
    )

    return {
        "stage": "V391.05A",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_result.get("policy_hash"),
        "account": {
            "equity": account.get("equity"),
            "status": account.get("status"),
            "account_blocked": bool(account.get("account_blocked", False)),
            "trading_blocked": bool(account.get("trading_blocked", False)),
        },
        "positions": positions,
        "proposal": proposal,
        "evaluation": evaluation,
        "total_exposure_blocked": evaluation["breached"],
        "risk_operations_allowed": risk_operations_allowed,
        "automatic_resize_enabled": False,
        "manual_review_required": evaluation["breached"] or evaluation["warning"],
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_06A_SYMBOL_CONCENTRATION_GUARD",
    }
