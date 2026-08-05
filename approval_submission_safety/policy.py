from __future__ import annotations

from .models import D


def evaluate_ticket(
    ticket: dict,
    *,
    policy: dict,
    market: dict,
    risk: dict,
    prior_keys: set[str],
) -> list[str]:
    blockers = []
    payload = ticket.get("payload", {})
    symbol = str(payload.get("symbol", ""))
    notional = D(payload.get("notional"))
    risk_level = str(risk.get("risk_level", "UNKNOWN"))
    idempotency_key = ticket.get("idempotency_key")

    if ticket.get("status") != "VALID":
        blockers.append("TICKET_NOT_VALID")
    if ticket.get("paper_endpoint_only") is not True:
        blockers.append("PAPER_ENDPOINT_MARKER_MISSING")
    if ticket.get("submission_enabled") is not False:
        blockers.append("TICKET_SUBMISSION_FLAG_MUST_BE_OFF")
    if ticket.get("broker_write_allowed") is not False:
        blockers.append("TICKET_BROKER_WRITE_FLAG_MUST_BE_OFF")

    if policy.get("mode") != "paper":
        blockers.append("NON_PAPER_MODE_BLOCKED")
    if policy.get("paper_endpoint") != "https://paper-api.alpaca.markets":
        blockers.append("NON_PAPER_ENDPOINT_BLOCKED")
    if symbol not in set(policy.get("symbol_allow_list", [])):
        blockers.append("SYMBOL_NOT_ALLOWED")
    if notional <= 0:
        blockers.append("NOTIONAL_INVALID")
    if notional > D(policy.get("max_notional_per_ticket", "500")):
        blockers.append("TICKET_NOTIONAL_LIMIT_EXCEEDED")
    if risk_level not in set(policy.get("allowed_risk_levels", ["NORMAL"])):
        blockers.append(f"RISK_LEVEL_NOT_ALLOWED:{risk_level}")
    if policy.get("require_market_open", True) and not market.get("is_open", False):
        blockers.append("MARKET_CLOSED")
    if idempotency_key in prior_keys:
        blockers.append("DUPLICATE_IDEMPOTENCY_KEY")
    if policy.get("submission_enabled", False):
        blockers.append("SUBMISSION_POLICY_MUST_REMAIN_OFF")
    if policy.get("broker_write_enabled", False):
        blockers.append("BROKER_WRITE_POLICY_MUST_REMAIN_OFF")

    return blockers
