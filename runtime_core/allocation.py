from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import AllocationDecision, Signal


class CapitalAllocationEngine:
    def allocate(
        self,
        *,
        signal: Signal,
        runtime_snapshot: dict[str, Any],
        portfolio_snapshot: dict[str, Any],
    ) -> AllocationDecision:
        risk = runtime_snapshot["risk_limits"]
        maximum_order = Decimal(str(risk["maximum_order_notional"]))
        gross_limit = Decimal(str(risk["maximum_gross_exposure"]))
        symbol_limit = Decimal(str(risk["maximum_symbol_exposure"]))
        gross_used = Decimal(str(portfolio_snapshot.get("gross_exposure", "0")))
        symbol_used = Decimal(str(
            portfolio_snapshot.get("symbol_exposure", {}).get(
                signal.symbol, "0"
            )
        ))

        requested = (maximum_order * signal.strength).quantize(
            Decimal("0.01")
        )
        remaining_gross = max(Decimal("0"), gross_limit - gross_used)
        remaining_symbol = max(Decimal("0"), symbol_limit - symbol_used)
        approved = min(requested, maximum_order, remaining_gross, remaining_symbol)

        blockers: list[str] = []
        if signal.side == "hold":
            blockers.append("HOLD_SIGNAL")
        if signal.symbol not in runtime_snapshot.get("allowed_symbols", []):
            blockers.append("SYMBOL_NOT_ALLOWED")
        if approved <= 0:
            blockers.append("NO_REMAINING_CAPACITY")
        if runtime_snapshot.get("allocation_enabled") is not True:
            blockers.append("ALLOCATION_DISABLED")

        blocked = bool(blockers)
        if blocked:
            approved = Decimal("0")

        fraction = (
            (approved / maximum_order).quantize(Decimal("0.0001"))
            if maximum_order > 0 else Decimal("0")
        )
        return AllocationDecision(
            symbol=signal.symbol,
            side=signal.side,
            approved_notional=approved,
            requested_notional=requested,
            allocation_fraction=fraction,
            blocked=blocked,
            blockers=tuple(blockers),
        )
