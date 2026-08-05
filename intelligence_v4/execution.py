from __future__ import annotations
from decimal import Decimal
from .models import ExecutionPlan

class ExecutionIntelligenceV2:
    def plan(
        self,
        *,
        symbol: str,
        side: str,
        quantity: Decimal,
        reference_price: Decimal,
        spread_bps: Decimal,
        volatility: Decimal,
        urgency: Decimal,
        maximum_order_notional: Decimal,
    ) -> ExecutionPlan:
        blockers = []
        if side not in {"buy", "sell"}:
            blockers.append("INVALID_SIDE")
        if quantity <= 0 or reference_price <= 0:
            blockers.append("INVALID_QUANTITY_OR_PRICE")
        notional = quantity * reference_price
        if notional > maximum_order_notional:
            blockers.append("MAXIMUM_ORDER_NOTIONAL_EXCEEDED")
        expected_slippage = (spread_bps / Decimal("2") + volatility * Decimal("100") * urgency).quantize(Decimal("0.01"))
        use_market = urgency >= Decimal("0.80") and spread_bps <= Decimal("8")
        order_type = "market" if use_market else "limit"
        slices = 1
        if notional > maximum_order_notional * Decimal("0.50"):
            slices = 3
        elif notional > maximum_order_notional * Decimal("0.25"):
            slices = 2
        limit_price = None
        if order_type == "limit":
            offset = spread_bps / Decimal("10000")
            limit_price = (
                reference_price * (Decimal("1") + offset if side == "buy" else Decimal("1") - offset)
            ).quantize(Decimal("0.01"))
        return ExecutionPlan(
            symbol=symbol,
            side=side,
            order_type=order_type,
            total_quantity=quantity,
            slice_count=slices,
            limit_price=limit_price,
            expected_slippage_bps=expected_slippage,
            time_limit_seconds=30 if use_market else 120,
            blocked=bool(blockers),
            blockers=tuple(blockers),
        )
