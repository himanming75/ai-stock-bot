from __future__ import annotations
import random
from typing import Any

def simulate_fill(
    plan: dict[str, Any],
    policy: dict[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    requested = float(plan.get("quantity", 0.0))
    reference_price = float(plan.get("reference_price", 0.0))
    side = str(plan.get("side", "BUY")).upper()

    partial_probability = float(policy.get("partial_fill_probability", 0.15))
    minimum_fill_ratio = float(policy.get("minimum_partial_fill_ratio", 0.50))
    slippage_bps = float(policy.get("slippage_bps", 5.0))
    commission_per_share = float(policy.get("commission_per_share", 0.0))
    minimum_commission = float(policy.get("minimum_commission", 0.0))

    if requested <= 0 or reference_price <= 0 or plan.get("state") != "PLANNED":
        return {
            "state": "NOT_FILLED",
            "requested_quantity": requested,
            "filled_quantity": 0.0,
            "fill_ratio": 0.0,
            "fill_price": 0.0,
            "gross_notional": 0.0,
            "commission": 0.0,
            "cash_effect": 0.0,
            "reason": "PLAN_NOT_ELIGIBLE",
        }

    is_partial = rng.random() < partial_probability
    fill_ratio = rng.uniform(minimum_fill_ratio, 0.99) if is_partial else 1.0
    filled = float(int(requested * fill_ratio))
    if filled <= 0:
        return {
            "state": "NOT_FILLED",
            "requested_quantity": requested,
            "filled_quantity": 0.0,
            "fill_ratio": 0.0,
            "fill_price": 0.0,
            "gross_notional": 0.0,
            "commission": 0.0,
            "cash_effect": 0.0,
            "reason": "ZERO_FILLED_QUANTITY",
        }

    slip = slippage_bps / 10000.0
    fill_price = reference_price * (1.0 + slip if side == "BUY" else 1.0 - slip)
    gross = filled * fill_price
    commission = max(minimum_commission, filled * commission_per_share)
    cash_effect = -(gross + commission) if side == "BUY" else gross - commission

    return {
        "state": "PARTIALLY_FILLED" if filled < requested else "FILLED",
        "requested_quantity": requested,
        "filled_quantity": filled,
        "fill_ratio": round(filled / requested, 6),
        "fill_price": round(fill_price, 4),
        "gross_notional": round(gross, 4),
        "commission": round(commission, 4),
        "cash_effect": round(cash_effect, 4),
        "reason": "",
    }
