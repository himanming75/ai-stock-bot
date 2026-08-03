from __future__ import annotations

def strategy_score(row: dict) -> float:
    gate = row.get("gate", {})
    approved_bonus = 20.0 if gate.get("approved") else 0.0
    score = (
        float(row.get("total_return_pct", 0.0))
        - 0.7 * float(row.get("maximum_drawdown_pct", 0.0))
        + 3.0 * float(row.get("sharpe_ratio", 0.0))
        + 0.1 * float(row.get("win_rate_pct", 0.0))
        + approved_bonus
    )
    return round(score, 4)

def rank_strategies(rows: list[dict]) -> list[dict]:
    ranked = []
    for row in rows:
        item = dict(row)
        item["portfolio_score"] = strategy_score(item)
        ranked.append(item)
    ranked.sort(key=lambda x: x["portfolio_score"], reverse=True)
    for index, row in enumerate(ranked, 1):
        row["portfolio_rank"] = index
    return ranked
