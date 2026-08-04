from __future__ import annotations


def evaluate(context: dict, action: str, quantity: float) -> dict:
    reasons: list[str] = []
    allowed = True

    governance = context["governance"]
    if governance.get("state") != "REAL_PAPER_OBSERVATION_GOVERNANCE_QUALIFIED":
        allowed = False
        reasons.append("GOVERNANCE_NOT_QUALIFIED")
    if governance.get("health") != "HEALTHY":
        allowed = False
        reasons.append("GOVERNANCE_NOT_HEALTHY")
    if governance.get("incidents"):
        allowed = False
        reasons.append("GOVERNANCE_INCIDENT_PRESENT")

    account = context["account"]
    if account.get("status") not in {"ACTIVE", None}:
        allowed = False
        reasons.append("ACCOUNT_NOT_ACTIVE")
    if account.get("trading_blocked") is True or account.get("account_blocked") is True:
        allowed = False
        reasons.append("ACCOUNT_BLOCKED")

    if action == "BUY":
        estimated_notional = quantity * float(context["risk"].get("reference_price", 0.0))
        buying_power = float(account.get("buying_power", 0.0))
        if estimated_notional > buying_power + 1e-9:
            allowed = False
            reasons.append("INSUFFICIENT_BUYING_POWER")

    duplicate = any(
        str(order.get("symbol", "")).upper() == context["symbol"]
        and str(order.get("side", "")).upper() == action
        and str(order.get("status", "")).lower() in {"new", "accepted", "pending_new", "partially_filled"}
        for order in context.get("open_orders", [])
    )
    if duplicate:
        allowed = False
        reasons.append("DUPLICATE_OPEN_ORDER")

    if quantity <= 0 and action in {"BUY", "SELL"}:
        allowed = False
        reasons.append("NON_POSITIVE_QUANTITY")

    if action == "HOLD":
        allowed = False
        reasons.append("HOLD_HAS_NO_ORDER_CANDIDATE")

    return {
        "decision_allowed": allowed,
        "blocking_reasons": reasons,
        "duplicate_open_order": duplicate,
    }
