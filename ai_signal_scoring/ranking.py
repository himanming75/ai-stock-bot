from __future__ import annotations


def rank_candidates(items: list[dict]) -> list[dict]:
    action_priority = {"BUY": 3, "HOLD": 2, "SELL": 1}
    ranked = sorted(
        items,
        key=lambda item: (
            item.get("ai_score", 0),
            item.get("ensemble_confidence", 0),
            action_priority.get(item.get("action"), 0),
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked
