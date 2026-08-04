from __future__ import annotations
from typing import Any


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("CANDIDATES_REQUIRED")
        return errors

    seen: set[str] = set()
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            errors.append(f"CANDIDATE_{index}_INVALID")
            continue
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol:
            errors.append(f"CANDIDATE_{index}_SYMBOL_REQUIRED")
        if symbol in seen:
            errors.append(f"DUPLICATE_SYMBOL_{symbol}")
        seen.add(symbol)
        if not isinstance(item.get("bars"), list) or len(item.get("bars", [])) < 2:
            errors.append(f"{symbol or index}_AT_LEAST_TWO_BARS_REQUIRED")

    maximum = int(payload.get("maximum_positions", 5))
    if maximum < 1 or maximum > 20:
        errors.append("MAXIMUM_POSITIONS_OUT_OF_RANGE")
    sector_cap = int(payload.get("maximum_positions_per_sector", 2))
    if sector_cap < 1 or sector_cap > maximum:
        errors.append("SECTOR_CAP_OUT_OF_RANGE")
    return errors
