from __future__ import annotations


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


WEIGHTS = {
    "CPI": -0.30,
    "CORE_CPI": -0.35,
    "PPI": -0.20,
    "NFP": 0.18,
    "UNEMPLOYMENT": -0.20,
    "GDP": 0.25,
    "RETAIL_SALES": 0.18,
    "FED_RATE": -0.35,
    "FOMC": -0.20,
}


def score_macro_event(event: dict) -> dict:
    event_type = str(event.get("event_type", "UNKNOWN")).upper()
    actual = _f(event.get("actual"))
    expected = _f(event.get("expected"))
    importance = max(0.0, min(1.0, _f(event.get("importance"), 0.5)))
    surprise = (
        (actual - expected) / max(abs(expected), 1e-9)
        if expected != 0 else 0.0
    )
    directional_weight = WEIGHTS.get(event_type, 0.0)
    score = max(
        -1.0,
        min(1.0, surprise * directional_weight * importance),
    )
    return {
        "event_type": event_type,
        "surprise": round(surprise, 8),
        "importance": round(importance, 8),
        "macro_score": round(score, 8),
    }


def macro_regime(scored_events: list[dict]) -> dict:
    if not scored_events:
        return {
            "macro_regime": "UNKNOWN",
            "aggregate_macro_score": 0.0,
            "event_count": 0,
        }
    total_weight = sum(max(x["importance"], 0.01) for x in scored_events)
    aggregate = sum(
        x["macro_score"] * max(x["importance"], 0.01)
        for x in scored_events
    ) / total_weight

    if aggregate >= 0.15:
        regime = "RISK_ON"
    elif aggregate <= -0.15:
        regime = "RISK_OFF"
    else:
        regime = "MIXED_OR_NEUTRAL"

    return {
        "macro_regime": regime,
        "aggregate_macro_score": round(aggregate, 8),
        "event_count": len(scored_events),
    }
