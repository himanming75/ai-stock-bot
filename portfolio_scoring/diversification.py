from __future__ import annotations


def diversification_score(
    allocations: list[dict],
    sector_allocations: dict[str, float],
) -> float:
    if not allocations:
        return 0.0

    symbol_count = len(allocations)
    sector_count = len([
        value for value in sector_allocations.values()
        if value > 0
    ])

    symbol_component = min(1.0, symbol_count / 5.0) * 50.0
    sector_component = min(1.0, sector_count / 4.0) * 50.0
    return round(symbol_component + sector_component, 2)
