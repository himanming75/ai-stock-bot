from __future__ import annotations
from decimal import Decimal
from .models import D, ZERO, HUNDRED, text

def current_exposure(portfolio: dict) -> dict:
    equity = D(portfolio.get("account_equity"))
    cash = D(portfolio.get("cash"))
    positions = list(portfolio.get("positions", []))
    gross = sum((abs(D(p.get("market_value"))) for p in positions), ZERO)
    net = sum((D(p.get("market_value")) for p in positions), ZERO)
    return {
        "equity": equity,
        "cash": cash,
        "gross": gross,
        "net": net,
        "gross_percent": gross / equity * HUNDRED if equity else ZERO,
        "net_percent": net / equity * HUNDRED if equity else ZERO,
        "positions": positions,
    }

def sector_exposure(positions: list[dict]) -> dict[str, Decimal]:
    result = {}
    for position in positions:
        sector = str(position.get("sector") or "UNKNOWN")
        result[sector] = result.get(sector, ZERO) + abs(
            D(position.get("market_value"))
        )
    return result

def symbol_exposure(positions: list[dict]) -> dict[str, Decimal]:
    return {
        str(p.get("symbol")): abs(D(p.get("market_value")))
        for p in positions
        if p.get("symbol")
    }

def correlation_value(matrix: dict, left: str, right: str) -> Decimal:
    if left == right:
        return Decimal("1")
    return D(
        matrix.get(left, {}).get(
            right,
            matrix.get(right, {}).get(left, "0"),
        )
    )

def serialize_decimal_map(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: text(value) for key, value in values.items()}
