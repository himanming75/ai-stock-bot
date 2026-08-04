from __future__ import annotations
from collections import defaultdict


def select(
    candidates: list[dict],
    maximum_positions: int,
    maximum_positions_per_sector: int,
    minimum_confidence: float,
    maximum_risk_score: int,
) -> tuple[list[dict], list[dict]]:
    selected: list[dict] = []
    excluded: list[dict] = []
    sector_counts: dict[str, int] = defaultdict(int)

    ordered = sorted(
        candidates,
        key=lambda item: (
            -float(item["selection_score"]),
            float(item["risk_score"]),
            str(item["symbol"]),
        ),
    )

    for item in ordered:
        reasons: list[str] = []
        sector = str(item.get("sector", "UNKNOWN")).upper()

        if item["action"] != "BUY":
            reasons.append("ACTION_NOT_BUY")
        if float(item["confidence"]) < minimum_confidence:
            reasons.append("CONFIDENCE_TOO_LOW")
        if int(item["risk_score"]) > maximum_risk_score:
            reasons.append("RISK_TOO_HIGH")
        if item["signal_rank"] == "D":
            reasons.append("SIGNAL_RANK_TOO_LOW")
        if len(selected) >= maximum_positions:
            reasons.append("MAXIMUM_POSITIONS_REACHED")
        if sector_counts[sector] >= maximum_positions_per_sector:
            reasons.append("SECTOR_CONCENTRATION_LIMIT")

        if reasons:
            copy = dict(item)
            copy["selected"] = False
            copy["exclusion_reasons"] = reasons
            excluded.append(copy)
        else:
            copy = dict(item)
            copy["selected"] = True
            copy["exclusion_reasons"] = []
            selected.append(copy)
            sector_counts[sector] += 1

    return selected, excluded
