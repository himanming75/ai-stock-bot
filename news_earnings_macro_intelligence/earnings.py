from __future__ import annotations


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_earnings(event: dict) -> dict:
    actual_eps = _f(event.get("actual_eps"))
    expected_eps = _f(event.get("expected_eps"))
    actual_revenue = _f(event.get("actual_revenue"))
    expected_revenue = _f(event.get("expected_revenue"))
    guidance_score = _f(event.get("guidance_score"))

    eps_surprise = (
        (actual_eps - expected_eps) / abs(expected_eps)
        if expected_eps != 0 else 0.0
    )
    revenue_surprise = (
        (actual_revenue - expected_revenue) / abs(expected_revenue)
        if expected_revenue != 0 else 0.0
    )
    composite = (
        eps_surprise * 0.45
        + revenue_surprise * 0.35
        + guidance_score * 0.20
    )
    composite = max(-1.0, min(1.0, composite))
    if composite >= 0.15:
        label = "STRONG_BEAT"
    elif composite <= -0.15:
        label = "STRONG_MISS"
    else:
        label = "MIXED_OR_IN_LINE"

    return {
        "eps_surprise": round(eps_surprise, 8),
        "revenue_surprise": round(revenue_surprise, 8),
        "guidance_score": round(guidance_score, 8),
        "earnings_score": round(composite, 8),
        "earnings_label": label,
    }
