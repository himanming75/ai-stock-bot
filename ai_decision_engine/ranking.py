from __future__ import annotations
from .models import D

def rank_candidates(decisions: list[dict]) -> list[dict]:
    candidates = [
        dict(item) for item in decisions
        if item.get("decision") in {"BUY", "SELL"}
        and item.get("status") == "PASS"
    ]
    candidates.sort(
        key=lambda item: (
            D(item.get("final_score")),
            D(item.get("agreement_percent")),
            abs(D(item.get("raw_score"))),
        ),
        reverse=True,
    )
    for index, item in enumerate(candidates, start=1):
        item["rank"] = index
        item["candidate_id"] = f"candidate_{index:03d}_{item['symbol']}"
    return candidates
