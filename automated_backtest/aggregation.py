from __future__ import annotations
from typing import Any

def score_result(row: dict[str, Any]) -> float:
    if row.get("state") != "COMPLETED":
        return -999999.0
    return (
        float(row.get("total_return_pct", 0.0))
        - 1.5 * float(row.get("maximum_drawdown_pct", 0.0))
        + 0.02 * float(row.get("win_rate_pct", 0.0))
    )

def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in results if row.get("state") == "COMPLETED"]
    ranked = []
    for row in completed:
        item = dict(row)
        item["automation_score"] = round(score_result(item), 6)
        ranked.append(item)
    ranked.sort(key=lambda item: item["automation_score"], reverse=True)
    for index, row in enumerate(ranked, 1):
        row["rank"] = index

    return {
        "job_count": len(results),
        "completed_count": len(completed),
        "skipped_count": len(results) - len(completed),
        "failed_count": sum(1 for row in results if row.get("status") == "FAIL"),
        "top_result": ranked[0] if ranked else None,
        "rankings": ranked,
    }
