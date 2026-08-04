from __future__ import annotations
from typing import Any


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    try:
        equity = float(payload.get("account_equity"))
        if equity <= 0:
            errors.append("ACCOUNT_EQUITY_MUST_BE_POSITIVE")
    except (TypeError, ValueError):
        errors.append("ACCOUNT_EQUITY_INVALID")

    for name, minimum, maximum in (
        ("risk_per_trade_pct", 0.0001, 0.10),
        ("maximum_position_pct", 0.001, 1.0),
    ):
        try:
            value = float(payload.get(name))
            if not minimum <= value <= maximum:
                errors.append(f"{name.upper()}_OUT_OF_RANGE")
        except (TypeError, ValueError):
            errors.append(f"{name.upper()}_INVALID")

    candidates = payload.get("positions")
    if not isinstance(candidates, list) or not candidates:
        errors.append("POSITIONS_REQUIRED")
        return errors

    seen: set[str] = set()
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            errors.append(f"POSITION_{index}_INVALID")
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            errors.append(f"POSITION_{index}_SYMBOL_REQUIRED")
        if symbol in seen:
            errors.append(f"DUPLICATE_SYMBOL_{symbol}")
        seen.add(symbol)

        for field, low, high in (
            ("reference_price", 0.000001, float("inf")),
            ("stop_loss_pct", 0.0001, 0.50),
            ("proposed_weight", 0.0, 1.0),
        ):
            try:
                value = float(item.get(field))
                if not low <= value <= high:
                    errors.append(f"{symbol or index}_{field.upper()}_OUT_OF_RANGE")
            except (TypeError, ValueError):
                errors.append(f"{symbol or index}_{field.upper()}_INVALID")
    return errors
