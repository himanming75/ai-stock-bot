from __future__ import annotations
from .utils import clamp, f, signal


def score_options(item: dict) -> dict:
    put_call = f(item.get("put_call_ratio"), 1.0)
    iv_rank = f(item.get("iv_rank"), 0.5)
    iv_percentile = f(item.get("iv_percentile"), 0.5)
    call_put_oi = f(item.get("call_put_open_interest_ratio"), 1.0)
    skew = f(item.get("skew"))
    gamma_exposure = f(item.get("gamma_exposure"))
    expected_move = f(item.get("expected_move"))
    max_pain_distance = f(item.get("max_pain_distance"))
    unusual_flow = f(item.get("unusual_flow_score"))

    positioning = clamp(
        (1.0 - put_call) * 0.75
        + (call_put_oi - 1.0) * 0.45
        + unusual_flow * 0.65
    )
    volatility_bias = clamp(
        (0.5 - iv_rank) * 0.45
        + (0.5 - iv_percentile) * 0.30
        - abs(skew) * 0.25
    )
    gamma = clamp(gamma_exposure)
    pin_risk = min(abs(max_pain_distance) * 4.0, 0.5)
    event_risk = clamp(
        iv_rank * 0.45
        + iv_percentile * 0.30
        + min(expected_move * 5.0, 0.25)
        + pin_risk
    , 0.0, 1.0)

    score = clamp(
        positioning * 0.55
        + volatility_bias * 0.20
        + gamma * 0.25
    )

    return {
        "options_score": round(score, 8),
        "options_signal": signal(score),
        "positioning_score": round(positioning, 8),
        "volatility_bias_score": round(volatility_bias, 8),
        "gamma_score": round(gamma, 8),
        "options_event_risk": round(event_risk, 8),
    }
