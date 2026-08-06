from __future__ import annotations
from .i18n import bilingual
from .models import SignalCandidate
from .regime import classify_regime


def _reason(en: str, ko: str) -> dict:
    return {"en": en, "ko": ko}


def generate_signal(
    *,
    symbol: str,
    features: dict,
    configuration: dict | None = None,
) -> dict:
    configuration = configuration or {}
    regime_info = classify_regime(features)

    score = 0.0
    reasons = []

    ema9 = features.get("ema9")
    ema21 = features.get("ema21")
    if ema9 is not None and ema21 is not None:
        if ema9 > ema21:
            score += 20
            reasons.append(_reason(
                "EMA 9 is above EMA 21.",
                "EMA 9가 EMA 21보다 높습니다.",
            ))
        elif ema9 < ema21:
            score -= 20
            reasons.append(_reason(
                "EMA 9 is below EMA 21.",
                "EMA 9가 EMA 21보다 낮습니다.",
            ))

    rsi14 = features.get("rsi14")
    if rsi14 is not None:
        if rsi14 <= 30:
            score += 20
            reasons.append(_reason(
                "RSI indicates an oversold condition.",
                "RSI가 과매도 상태를 나타냅니다.",
            ))
        elif rsi14 >= 70:
            score -= 20
            reasons.append(_reason(
                "RSI indicates an overbought condition.",
                "RSI가 과매수 상태를 나타냅니다.",
            ))
        elif 45 <= rsi14 <= 60:
            score += 5
            reasons.append(_reason(
                "RSI is in a neutral-positive zone.",
                "RSI가 중립적 상승 구간에 있습니다.",
            ))

    histogram = features.get("macd_histogram")
    if histogram is not None:
        if histogram > 0:
            score += 15
            reasons.append(_reason(
                "MACD histogram is positive.",
                "MACD 히스토그램이 양수입니다.",
            ))
        elif histogram < 0:
            score -= 15
            reasons.append(_reason(
                "MACD histogram is negative.",
                "MACD 히스토그램이 음수입니다.",
            ))

    close = float(features.get("close") or 0)
    vwap = features.get("vwap")
    if vwap is not None:
        if close > vwap:
            score += 10
            reasons.append(_reason(
                "Price is above VWAP.",
                "가격이 VWAP보다 높습니다.",
            ))
        elif close < vwap:
            score -= 10
            reasons.append(_reason(
                "Price is below VWAP.",
                "가격이 VWAP보다 낮습니다.",
            ))

    momentum = float(features.get("momentum_5") or 0)
    if momentum >= 0.01:
        score += 15
        reasons.append(_reason(
            "Five-bar momentum is positive.",
            "5개 봉 모멘텀이 상승 방향입니다.",
        ))
    elif momentum <= -0.01:
        score -= 15
        reasons.append(_reason(
            "Five-bar momentum is negative.",
            "5개 봉 모멘텀이 하락 방향입니다.",
        ))

    volume_ratio = float(features.get("volume_ratio") or 0)
    if volume_ratio >= 1.5:
        score += 5 if score >= 0 else -5
        reasons.append(_reason(
            "Volume is above its recent average.",
            "거래량이 최근 평균보다 높습니다.",
        ))

    volatility_confidence_multiplier = 1.0
    if regime_info["regime"] == "REGIME_VOLATILE":
        volatility_confidence_multiplier = 0.75
        reasons.append(_reason(
            "Confidence was reduced because volatility is high.",
            "변동성이 높아 신뢰도를 낮췄습니다.",
        ))

    score = max(-100.0, min(100.0, score))
    if score >= 25:
        action = "BUY"
    elif score <= -25:
        action = "SELL"
    else:
        action = "HOLD"

    confidence = round(
        min(100.0, abs(score))
        * volatility_confidence_multiplier,
        2,
    )

    max_daily_loss = float(
        (
            configuration.get("profile", {})
            if isinstance(configuration.get("profile"), dict)
            else {}
        ).get("max_daily_loss_percent", 0)
        or 0
    )
    activation = bool(
        (
            configuration.get("execution", {})
            if isinstance(configuration.get("execution"), dict)
            else {}
        ).get("activation_enabled", False)
    )

    if activation:
        risk_gate = "BLOCKED_UNSAFE_ACTIVATION_FLAG"
    elif max_daily_loss < 0:
        risk_gate = "BLOCKED_INVALID_RISK"
    else:
        risk_gate = "PASS_READ_ONLY"

    candidate = SignalCandidate(
        symbol=symbol.upper(),
        action=action,
        confidence=confidence,
        score=round(score, 2),
        regime=regime_info["regime"],
        trend=regime_info["trend"],
        reasons=reasons or [_reason(
            "No strong directional evidence was found.",
            "강한 방향성 근거가 확인되지 않았습니다.",
        )],
        risk_gate=risk_gate,
        features=features,
    ).to_dict()
    candidate["action_i18n"] = bilingual(action)
    candidate["regime_i18n"] = bilingual(candidate["regime"])
    candidate["trend_i18n"] = bilingual(candidate["trend"])
    candidate["order_submission_enabled"] = False
    candidate["broker_write_enabled"] = False
    candidate["execution_mode"] = "SIGNAL_CANDIDATE_ONLY"
    return candidate
