from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .daily_loss import evaluate_daily_loss


def run_guard(policy_result: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    policy = policy_result["policy"]
    evaluation = evaluate_daily_loss(
        equity=account.get("equity"),
        last_equity=account.get("last_equity"),
        daily_loss_limit_pct=policy.get("daily_loss_limit_pct"),
    )

    paused = evaluation["breached"]
    state = (
        "DAILY_LOSS_GUARD_PAUSE_REQUIRED"
        if paused
        else "DAILY_LOSS_GUARD_WARNING"
        if evaluation["warning"]
        else "DAILY_LOSS_GUARD_ACTIVE"
    )

    return {
        "stage": "V391.02A",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_result.get("policy_hash"),
        "account": {
            "equity": account.get("equity"),
            "last_equity": account.get("last_equity"),
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
        "next_phase": "V391_03A_MAX_DRAWDOWN_GUARD",
    }
