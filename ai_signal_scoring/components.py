from __future__ import annotations


def clamp(value: float, minimum=0.0, maximum=100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def trend_score(features: dict) -> float:
    close = float(features.get("close") or 0)
    ema9 = features.get("ema9")
    ema21 = features.get("ema21")
    if not close or ema9 is None or ema21 is None:
        return 50.0
    spread = (float(ema9) - float(ema21)) / close
    return clamp(50 + spread * 1200)


def momentum_score(features: dict) -> float:
    momentum = float(features.get("momentum_5") or 0)
    rsi = features.get("rsi14")
    base = 50 + momentum * 1200
    if rsi is not None:
        rsi = float(rsi)
        if 45 <= rsi <= 65:
            base += 10
        elif rsi >= 80:
            base -= 20
        elif rsi <= 20:
            base += 5
    return clamp(base)


def volume_score(features: dict) -> float:
    ratio = float(features.get("volume_ratio") or 0)
    if ratio <= 0:
        return 25.0
    return clamp(40 + (ratio - 1.0) * 50)


def volatility_score(features: dict) -> float:
    atr_percent = float(features.get("atr_percent") or 0)
    width = float(features.get("bollinger_width") or 0)
    penalty = atr_percent * 1200 + width * 250
    return clamp(100 - penalty)


def regime_score(candidate: dict) -> float:
    regime = str(candidate.get("regime") or "")
    trend = str(candidate.get("trend") or "")
    if regime == "REGIME_TRENDING":
        return 90.0 if trend != "TREND_SIDEWAYS" else 65.0
    if regime == "REGIME_RANGE":
        return 60.0
    if regime == "REGIME_VOLATILE":
        return 45.0
    return 50.0


def risk_score(candidate: dict) -> float:
    if candidate.get("risk_gate") != "PASS_READ_ONLY":
        return 0.0
    conflict = candidate.get("conflict_analysis", {})
    count = int(conflict.get("conflict_count") or 0)
    return clamp(100 - count * 25)


def direction_score(candidate: dict) -> float:
    action = candidate.get("action")
    raw = float(candidate.get("score") or 0)
    if action == "BUY":
        return clamp(50 + raw / 2)
    if action == "SELL":
        return clamp(50 + abs(raw) / 2)
    return clamp(50 - abs(raw) / 4)
