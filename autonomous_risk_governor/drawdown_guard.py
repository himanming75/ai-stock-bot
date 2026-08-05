from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .drawdown import evaluate_drawdown


def run_guard(
    policy_result: dict[str, Any],
    account: dict[str, Any],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    policy = policy_result["policy"]
    peak_equity = checkpoint.get("peak_equity", account.get("equity"))

    evaluation = evaluate_drawdown(
        equity=account.get("equity"),
        peak_equity=peak_equity,
        maximum_drawdown_pct=policy.get("maximum_drawdown_pct"),
    )

    paused = evaluation["breached"]
    state = (
        "MAX_DRAWDOWN_GUARD_PAUSE_REQUIRED"
        if paused
        else "MAX_DRAWDOWN_GUARD_WARNING"
        if evaluation["warning"]
        else "MAX_DRAWDOWN_GUARD_ACTIVE"
    )

    return {
        "stage": "V391.03A",
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
        "evaluation": evaluation,
        "pause_required": paused,
        "risk_operations_allowed": (
            policy_result.get("risk_operations_allowed") is True
            and evaluation["new_risk_allowed"]
            and account.get("status") in {"ACTIVE", None}
            and not bool(account.get("account_blocked", False))
            and not bool(account.get("trading_blocked", False))
        ),
        "automatic_resume_enabled": False,
        "manual_resume_required": paused,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_04A_POSITION_SIZE_LIMIT",
    }
