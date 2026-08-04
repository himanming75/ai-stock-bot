from __future__ import annotations


OPEN_STATUSES = {"new", "accepted", "pending_new", "partially_filled"}


def run_checks(decision: dict, runtime: dict, policy: dict) -> dict:
    candidate = decision.get("paper_order_candidate", {})
    reasons: list[str] = []

    if decision.get("state") != "GOVERNED_DECISION_CANDIDATE_READY":
        reasons.append("DECISION_NOT_READY")
    if decision.get("status") != "PASS":
        reasons.append("DECISION_STATUS_NOT_PASS")
    if candidate.get("decision_allowed") is not True:
        reasons.append("DECISION_NOT_ALLOWED")
    if candidate.get("submission_allowed") is not False:
        reasons.append("UPSTREAM_SUBMISSION_POLICY_INVALID")

    symbol = str(candidate.get("symbol", "")).upper()
    side = str(candidate.get("side", "")).upper()
    quantity = float(candidate.get("quantity", 0.0))
    reference_price = float(runtime.get("reference_price", 0.0))
    estimated_notional = quantity * reference_price

    if side not in {"BUY", "SELL"}:
        reasons.append("SIDE_INVALID")
    if quantity <= 0:
        reasons.append("QUANTITY_INVALID")
    if estimated_notional <= 0:
        reasons.append("NOTIONAL_INVALID")

    if runtime.get("market_open") is not True:
        reasons.append("MARKET_CLOSED")
    if runtime.get("kill_switch_active") is True:
        reasons.append("KILL_SWITCH_ACTIVE")
    if runtime.get("account_status") != "ACTIVE":
        reasons.append("ACCOUNT_NOT_ACTIVE")
    if runtime.get("trading_blocked") is True:
        reasons.append("ACCOUNT_TRADING_BLOCKED")

    buying_power = float(runtime.get("buying_power", 0.0))
    if side == "BUY" and estimated_notional > buying_power + 1e-9:
        reasons.append("INSUFFICIENT_BUYING_POWER")

    position_qty = float(runtime.get("position_qty", 0.0))
    if side == "SELL" and quantity > position_qty + 1e-9:
        reasons.append("INSUFFICIENT_POSITION_QUANTITY")

    max_notional = float(policy.get("maximum_proposal_notional", 1000.0))
    if estimated_notional > max_notional + 1e-9:
        reasons.append("MAXIMUM_PROPOSAL_NOTIONAL_EXCEEDED")

    daily_loss = abs(min(0.0, float(runtime.get("daily_pnl", 0.0))))
    if daily_loss >= float(policy.get("daily_loss_limit", 500.0)):
        reasons.append("DAILY_LOSS_LIMIT_REACHED")

    duplicates = [
        order for order in runtime.get("open_orders", [])
        if str(order.get("symbol", "")).upper() == symbol
        and str(order.get("side", "")).upper() == side
        and str(order.get("status", "")).lower() in OPEN_STATUSES
    ]
    if duplicates:
        reasons.append("DUPLICATE_OPEN_ORDER")

    policy_safe = (
        policy.get("paper_endpoint_only") is True
        and policy.get("paper_submission_enabled") is False
        and policy.get("live_submission_enabled") is False
        and policy.get("broker_write_enabled") is False
        and int(policy.get("maximum_new_orders_per_day", -1)) == 0
    )
    if not policy_safe:
        reasons.append("SAFETY_POLICY_INVALID")

    return {
        "eligible_for_approval": len(reasons) == 0,
        "blocking_reasons": reasons,
        "estimated_notional": round(estimated_notional, 2),
        "duplicate_open_order_count": len(duplicates),
        "daily_loss": round(daily_loss, 2),
        "buying_power": round(buying_power, 2),
        "position_qty": round(position_qty, 6),
    }
