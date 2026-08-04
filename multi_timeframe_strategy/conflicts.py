from __future__ import annotations
from collections import defaultdict
from typing import Any

def resolve(rows: list[dict[str, Any]], allow_same_symbol: bool) -> list[dict[str, Any]]:
    if allow_same_symbol:
        return rows
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row.get("symbol"))].append(row)
    resolved = []
    for symbol_rows in grouped.values():
        symbol_rows.sort(key=lambda row: row.get("strategy_score", 0), reverse=True)
        winner = symbol_rows[0]
        resolved.append(winner)
        for loser in symbol_rows[1:]:
            resolved.append({
                **loser,
                "eligible": False,
                "rejection_reason": "LOWER_SCORE_SAME_SYMBOL_CONFLICT",
            })
    return resolved
