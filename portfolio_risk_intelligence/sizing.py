from __future__ import annotations
from decimal import Decimal
from .models import D, ZERO, HUNDRED, clamp, text

def candidate_budget(
    candidate: dict,
    *,
    equity: Decimal,
    cash: Decimal,
    policy: dict,
    portfolio_risk_level: str,
) -> dict:
    confidence = clamp(D(candidate.get("final_score")))
    base_risk_percent = D(policy.get("base_risk_budget_percent", "0.25"))
    max_position_percent = D(policy.get("max_single_position_percent", "5"))
    max_order_notional = D(policy.get("max_order_notional", "500"))
    cash_reserve_percent = D(policy.get("minimum_cash_reserve_percent", "20"))
    penalty = D(
        policy.get("risk_level_multiplier", {}).get(
            portfolio_risk_level,
            policy.get("risk_level_multiplier", {}).get("UNKNOWN", "0"),
        )
    )

    available_cash = max(
        ZERO,
        cash - equity * cash_reserve_percent / HUNDRED,
    )
    confidence_factor = confidence / HUNDRED
    risk_budget = equity * base_risk_percent / HUNDRED
    raw = risk_budget * confidence_factor * penalty
    position_cap = equity * max_position_percent / HUNDRED
    proposed = min(raw, position_cap, max_order_notional, available_cash)

    blockers = []
    if equity <= ZERO:
        blockers.append("ACCOUNT_EQUITY_MISSING_OR_ZERO")
    if cash <= ZERO:
        blockers.append("CASH_MISSING_OR_ZERO")
    if portfolio_risk_level not in set(
        policy.get("allowed_risk_levels", ["NORMAL"])
    ):
        blockers.append(
            f"PORTFOLIO_RISK_LEVEL_NOT_ALLOWED:{portfolio_risk_level}"
        )
    if candidate.get("decision") not in {"BUY", "SELL"}:
        blockers.append("CANDIDATE_NOT_DIRECTIONAL")
    if proposed <= ZERO:
        blockers.append("PROPOSED_NOTIONAL_ZERO")

    return {
        "symbol": candidate.get("symbol"),
        "side": candidate.get("decision"),
        "confidence": text(confidence),
        "available_cash_after_reserve": text(available_cash),
        "raw_risk_budget": text(raw),
        "position_cap": text(position_cap),
        "max_order_notional": text(max_order_notional),
        "proposed_notional": text(proposed),
        "blockers": blockers,
        "status": "READY" if not blockers else "BLOCKED",
    }
