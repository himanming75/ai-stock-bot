from __future__ import annotations
from .models import D

def evaluate_guards(
    allocation: dict,
    *,
    approval: dict,
    market: dict,
    policy: dict,
    duplicate_keys: set[str],
) -> list[str]:
    blockers = []
    symbol = str(allocation.get("symbol", ""))
    side = str(allocation.get("side", ""))
    notional = D(allocation.get("proposed_notional"))
    duplicate_key = f"{symbol}:{side}:{notional}"

    if allocation.get("status") != "READY":
        blockers.append("ALLOCATION_NOT_READY")
    if approval.get("status") != "APPROVED_FOR_SEPARATE_SUBMISSION_STAGE":
        blockers.append("APPROVAL_NOT_GRANTED")
    if policy.get("require_market_open", True) and not market.get("is_open", False):
        blockers.append("MARKET_CLOSED")
    if duplicate_key in duplicate_keys:
        blockers.append("DUPLICATE_EXECUTION_PLAN")
    if notional <= 0:
        blockers.append("NOTIONAL_INVALID")
    if notional > D(policy.get("max_order_notional", "500")):
        blockers.append("ORDER_NOTIONAL_LIMIT_EXCEEDED")
    if D(market.get("estimated_spread_bps")) > D(
        policy.get("max_spread_bps", "25")
    ):
        blockers.append("SPREAD_TOO_WIDE")
    if D(market.get("average_daily_dollar_volume")) < D(
        policy.get("minimum_daily_dollar_volume", "10000000")
    ):
        blockers.append("LIQUIDITY_TOO_LOW")
    if D(market.get("estimated_slippage_bps")) > D(
        policy.get("max_slippage_bps", "20")
    ):
        blockers.append("SLIPPAGE_TOO_HIGH")
    if D(market.get("volatility_percent")) > D(
        policy.get("max_volatility_percent", "5")
    ):
        blockers.append("VOLATILITY_TOO_HIGH")
    if policy.get("submission_enabled", False):
        blockers.append("SUBMISSION_FLAG_MUST_REMAIN_OFF")
    return blockers
