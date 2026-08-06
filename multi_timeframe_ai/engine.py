from __future__ import annotations
from dataclasses import dataclass
from math import exp
from typing import Iterable

TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1h", "1d")
TIMEFRAME_WEIGHTS = {
    "1m": 0.06,
    "3m": 0.08,
    "5m": 0.12,
    "15m": 0.17,
    "30m": 0.17,
    "1h": 0.18,
    "1d": 0.22,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


def classify_regime(score: float) -> str:
    if score >= 0.60:
        return "STRONG_BULL"
    if score >= 0.18:
        return "WEAK_BULL"
    if score > -0.18:
        return "RANGE"
    if score > -0.60:
        return "WEAK_BEAR"
    return "STRONG_BEAR"


def classify_structure(
    *,
    gap_percent: float,
    close_vs_range: float,
    volume_ratio: float,
    follow_through: float,
) -> str:
    if gap_percent >= 0.012:
        return "GAP_UP"
    if gap_percent <= -0.012:
        return "GAP_DOWN"
    if close_vs_range >= 0.82 and volume_ratio >= 1.35:
        return "BREAKOUT" if follow_through >= 0 else "FAKE_BREAKOUT"
    if close_vs_range <= 0.18 and volume_ratio >= 1.35:
        return "BREAKOUT" if follow_through <= 0 else "FAKE_BREAKOUT"
    return "NORMAL"


def score_timeframe(timeframe: str, features: dict) -> dict:
    close = float(features.get("close", 0.0))
    ema_fast = float(features.get("ema_fast", close))
    ema_slow = float(features.get("ema_slow", close))
    momentum = float(features.get("momentum", 0.0))
    rsi = float(features.get("rsi", 50.0))
    volume_ratio = float(features.get("volume_ratio", 1.0))
    atr_percent = max(float(features.get("atr_percent", 0.01)), 0.0001)
    gap_percent = float(features.get("gap_percent", 0.0))
    close_vs_range = clamp(float(features.get("close_vs_range", 0.5)), 0.0, 1.0)
    follow_through = float(features.get("follow_through", momentum))

    trend_raw = 0.0 if close == 0 else (ema_fast - ema_slow) / abs(close)
    trend_score = clamp(trend_raw / max(atr_percent, 0.002), -1.0, 1.0)
    momentum_score = clamp(momentum / max(atr_percent * 1.5, 0.003), -1.0, 1.0)
    rsi_score = clamp((rsi - 50.0) / 25.0, -1.0, 1.0)
    volume_score = clamp((volume_ratio - 1.0) / 1.0, -0.5, 1.0)

    directional = (
        trend_score * 0.38
        + momentum_score * 0.28
        + rsi_score * 0.18
        + volume_score * 0.16 * (1 if momentum_score >= 0 else -1)
    )
    directional = clamp(directional, -1.0, 1.0)

    structure = classify_structure(
        gap_percent=gap_percent,
        close_vs_range=close_vs_range,
        volume_ratio=volume_ratio,
        follow_through=follow_through,
    )
    regime = classify_regime(directional)

    if directional >= 0.16:
        signal = "BUY"
    elif directional <= -0.16:
        signal = "SELL"
    else:
        signal = "HOLD"

    base_probability = _sigmoid(abs(directional) * 3.4)
    noise_penalty = clamp(atr_percent / 0.08, 0.0, 0.35)
    probability = clamp(base_probability - noise_penalty, 0.50, 0.96)
    expected_return = directional * atr_percent * 2.4
    expected_risk = atr_percent * (1.0 + (1.0 - probability))
    reward_risk = abs(expected_return) / expected_risk if expected_risk else 0.0

    return {
        "timeframe": timeframe,
        "weight": TIMEFRAME_WEIGHTS[timeframe],
        "signal": signal,
        "directional_score": round(directional, 6),
        "trend_score": round(trend_score, 6),
        "momentum_score": round(momentum_score, 6),
        "regime": regime,
        "structure": structure,
        "probability": round(probability, 6),
        "expected_return": round(expected_return, 6),
        "expected_risk": round(expected_risk, 6),
        "reward_risk": round(reward_risk, 6),
        "features": {
            "close": close,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "momentum": momentum,
            "rsi": rsi,
            "volume_ratio": volume_ratio,
            "atr_percent": atr_percent,
            "gap_percent": gap_percent,
            "close_vs_range": close_vs_range,
            "follow_through": follow_through,
        },
    }


def analyze_symbol(symbol: str, timeframe_features: dict[str, dict]) -> dict:
    missing = [tf for tf in TIMEFRAMES if tf not in timeframe_features]
    if missing:
        raise ValueError(f"missing timeframes: {', '.join(missing)}")

    analyses = [
        score_timeframe(tf, timeframe_features[tf])
        for tf in TIMEFRAMES
    ]
    consensus_score = sum(
        item["directional_score"] * item["weight"] for item in analyses
    )
    positive_weight = sum(
        item["weight"] for item in analyses if item["signal"] == "BUY"
    )
    negative_weight = sum(
        item["weight"] for item in analyses if item["signal"] == "SELL"
    )
    hold_weight = sum(
        item["weight"] for item in analyses if item["signal"] == "HOLD"
    )

    dominant_weight = max(positive_weight, negative_weight, hold_weight)
    alignment = clamp(dominant_weight, 0.0, 1.0)
    weighted_probability = sum(
        item["probability"] * item["weight"] for item in analyses
    )
    disagreement = 1.0 - alignment
    raw_confidence = (
        weighted_probability * 0.55
        + alignment * 0.35
        + abs(consensus_score) * 0.10
    )
    calibrated_confidence = clamp(
        raw_confidence - disagreement * 0.18,
        0.0,
        0.99,
    )

    if consensus_score >= 0.14:
        action = "BUY"
    elif consensus_score <= -0.14:
        action = "SELL"
    else:
        action = "HOLD"

    expected_return = sum(
        item["expected_return"] * item["weight"] for item in analyses
    )
    expected_risk = sum(
        item["expected_risk"] * item["weight"] for item in analyses
    ) * (1.0 + disagreement * 0.35)
    reward_risk = (
        abs(expected_return) / expected_risk if expected_risk else 0.0
    )

    structures = {}
    for item in analyses:
        structures[item["structure"]] = structures.get(item["structure"], 0) + 1
    dominant_structure = max(structures, key=structures.get)

    return {
        "symbol": symbol,
        "action": action,
        "consensus_score": round(consensus_score, 6),
        "timeframe_consensus": {
            "buy_weight": round(positive_weight, 6),
            "sell_weight": round(negative_weight, 6),
            "hold_weight": round(hold_weight, 6),
            "alignment": round(alignment, 6),
            "disagreement": round(disagreement, 6),
        },
        "trend_alignment": round(alignment, 6),
        "market_regime_2": classify_regime(consensus_score),
        "dominant_structure": dominant_structure,
        "probability": round(weighted_probability, 6),
        "expected_return": round(expected_return, 6),
        "expected_risk": round(expected_risk, 6),
        "reward_risk": round(reward_risk, 6),
        "confidence_calibration": {
            "raw_confidence": round(raw_confidence, 6),
            "calibrated_confidence": round(calibrated_confidence, 6),
            "calibration_method": "ALIGNMENT_DISAGREEMENT_PENALTY_V2",
        },
        "timeframes": analyses,
        "execution_mode": "ANALYSIS_ONLY",
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancellation_enabled": False,
        "position_allocation_enabled": False,
        "live_trading_enabled": False,
    }
