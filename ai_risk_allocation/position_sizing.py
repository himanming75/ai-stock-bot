from __future__ import annotations
from typing import Any
from .models import PositionSize, PositionSizingResult
from .validation import validate


def _round_money(value: float) -> float:
    return round(max(0.0, value), 2)


def size_positions(payload: dict[str, Any]) -> PositionSizingResult:
    errors = validate(payload)
    if errors:
        raise ValueError(",".join(errors))

    equity = float(payload["account_equity"])
    risk_pct = float(payload["risk_per_trade_pct"])
    maximum_position_pct = float(payload["maximum_position_pct"])
    allow_fractional = bool(payload.get("allow_fractional_shares", True))
    minimum_notional = float(payload.get("minimum_notional", 1.0))

    output: list[PositionSize] = []
    for item in payload["positions"]:
        symbol = str(item["symbol"]).strip().upper()
        sector = str(item.get("sector", "UNKNOWN")).strip().upper()
        price = float(item["reference_price"])
        stop_loss_pct = float(item["stop_loss_pct"])
        proposed_weight = float(item["proposed_weight"])

        risk_budget = equity * risk_pct
        maximum_by_risk = risk_budget / stop_loss_pct
        maximum_by_weight = equity * min(proposed_weight, maximum_position_pct)
        recommended_notional = min(maximum_by_risk, maximum_by_weight)

        if recommended_notional < minimum_notional:
            recommended_notional = 0.0

        raw_quantity = recommended_notional / price if price else 0.0
        if allow_fractional:
            quantity = round(raw_quantity, 6)
        else:
            quantity = float(int(raw_quantity))

        recommended_notional = quantity * price
        if recommended_notional < minimum_notional:
            quantity = 0.0
            recommended_notional = 0.0

        risk_at_stop = recommended_notional * stop_loss_pct
        effective_weight = recommended_notional / equity if equity else 0.0

        if recommended_notional == 0:
            constraint = "MINIMUM_NOTIONAL"
            status = "SKIPPED"
        elif maximum_by_risk <= maximum_by_weight:
            constraint = "RISK_BUDGET"
            status = "SIZED"
        else:
            constraint = "POSITION_WEIGHT"
            status = "SIZED"

        reasons = [
            f"Per-trade risk budget is ${risk_budget:.2f}.",
            f"Risk-based maximum notional is ${maximum_by_risk:.2f}.",
            f"Weight-based maximum notional is ${maximum_by_weight:.2f}.",
            f"Binding constraint is {constraint}.",
            "Position size is analytical only and cannot submit an order.",
        ]

        output.append(PositionSize(
            symbol=symbol,
            sector=sector,
            reference_price=round(price, 6),
            stop_loss_pct=round(stop_loss_pct, 6),
            proposed_weight=round(proposed_weight, 6),
            risk_budget=_round_money(risk_budget),
            maximum_notional_by_risk=_round_money(maximum_by_risk),
            maximum_notional_by_weight=_round_money(maximum_by_weight),
            recommended_notional=_round_money(recommended_notional),
            recommended_quantity=quantity,
            effective_weight=round(effective_weight, 6),
            risk_at_stop=_round_money(risk_at_stop),
            binding_constraint=constraint,
            status=status,
            reasons=tuple(reasons),
        ))

    total_notional = sum(item.recommended_notional for item in output)
    total_risk = sum(item.risk_at_stop for item in output)

    return PositionSizingResult(
        account_equity=round(equity, 2),
        risk_per_trade_pct=round(risk_pct, 6),
        maximum_position_pct=round(maximum_position_pct, 6),
        positions=tuple(output),
        total_recommended_notional=_round_money(total_notional),
        total_effective_weight=round(total_notional / equity, 6),
        total_risk_at_stop=_round_money(total_risk),
        remaining_cash=_round_money(equity - total_notional),
    )
