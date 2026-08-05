from __future__ import annotations


def allocate(candidates: list[dict], max_positions: int = 3) -> list[dict]:
    eligible = [
        item for item in candidates
        if item.get("decision_status") == "APPROVED_CANDIDATE"
        and item.get("final_score", 0.0) > 0
    ][:max_positions]

    if not eligible:
        return []

    weights = [
        max(
            item["final_score"] * item["confidence"] / 100.0,
            0.000001,
        )
        for item in eligible
    ]
    total = sum(weights)

    allocations = []
    for item, raw_weight in zip(eligible, weights):
        allocation = min(raw_weight / total, 0.45)
        allocations.append({
            "symbol": item["symbol"],
            "target_weight": round(allocation, 8),
            "source_rank": item["rank"],
            "final_score": item["final_score"],
            "confidence": item["confidence"],
            "execution_enabled": False,
        })

    allocated = sum(item["target_weight"] for item in allocations)
    if allocated > 1.0:
        for item in allocations:
            item["target_weight"] = round(
                item["target_weight"] / allocated,
                8,
            )

    return allocations
