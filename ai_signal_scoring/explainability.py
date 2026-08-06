from __future__ import annotations


def explain(candidate: dict, scoring: dict) -> list[dict]:
    components = scoring.get("component_scores", {})
    reasons = []

    ranking = sorted(
        components.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    for name, value in ranking[:3]:
        labels = {
            "direction": ("Direction agreement", "방향성 일치"),
            "trend": ("Trend strength", "추세 강도"),
            "momentum": ("Momentum quality", "모멘텀 품질"),
            "volume": ("Volume confirmation", "거래량 확인"),
            "volatility": ("Volatility stability", "변동성 안정성"),
            "regime": ("Market regime fit", "시장 국면 적합성"),
            "risk": ("Risk gate quality", "리스크 게이트 품질"),
        }
        en, ko = labels.get(name, (name, name))
        reasons.append({
            "type": "POSITIVE_DRIVER",
            "component": name,
            "score": round(value, 2),
            "en": f"{en} contributed positively.",
            "ko": f"{ko}이 긍정적으로 기여했습니다.",
        })

    conflicts = candidate.get("conflict_analysis", {}).get("conflicts", [])
    for conflict in conflicts:
        reasons.append({
            "type": "CONFLICT",
            "component": conflict.get("code"),
            "score": None,
            "en": conflict.get("en", "Signal conflict detected."),
            "ko": conflict.get("ko", "신호 충돌이 감지되었습니다."),
        })

    if not conflicts:
        reasons.append({
            "type": "SAFETY",
            "component": "risk_gate",
            "score": scoring.get("component_scores", {}).get("risk"),
            "en": "No signal conflict penalty was applied.",
            "ko": "신호 충돌 패널티가 적용되지 않았습니다.",
        })
    return reasons
