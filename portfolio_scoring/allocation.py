from __future__ import annotations

from collections import defaultdict


def allocate(
    ranked: list[dict],
    *,
    portfolio_exposure_pct: float,
    sector_limit_pct: float,
    minimum_score: float,
) -> tuple[list[dict], dict]:
    exposure_limit = max(0.0, min(100.0, float(portfolio_exposure_pct)))
    sector_limit = max(0.0, min(100.0, float(sector_limit_pct)))

    eligible = [
        row for row in ranked
        if row["decision"] in {"BUY", "WATCH"}
        and row["risk_adjusted_score"] >= minimum_score
    ]
    positive_total = sum(
        max(0.0, row["risk_adjusted_score"])
        for row in eligible
    )

    allocations = []
    sector_usage = defaultdict(float)
    remaining = exposure_limit

    for row in eligible:
        if remaining <= 0:
            break

        proportional = (
            exposure_limit
            * max(0.0, row["risk_adjusted_score"])
            / positive_total
            if positive_total > 0
            else 0.0
        )
        symbol_cap = max(0.0, float(row["max_position_pct"]))
        sector_remaining = max(
            0.0,
            sector_limit - sector_usage[row["sector"]],
        )
        allocation = min(
            proportional,
            symbol_cap,
            sector_remaining,
            remaining,
        )

        if allocation <= 0:
            continue

        allocation_row = {
            **row,
            "recommended_weight_pct": round(allocation, 4),
        }
        allocations.append(allocation_row)
        sector_usage[row["sector"]] += allocation
        remaining -= allocation

    summary = {
        "portfolio_exposure_limit_pct": round(exposure_limit, 4),
        "allocated_pct": round(
            sum(row["recommended_weight_pct"] for row in allocations), 4
        ),
        "unallocated_pct": round(remaining, 4),
        "sector_limit_pct": round(sector_limit, 4),
        "sector_allocations_pct": {
            sector: round(value, 4)
            for sector, value in sorted(sector_usage.items())
        },
        "eligible_count": len(eligible),
        "allocated_count": len(allocations),
    }
    return allocations, summary
