from __future__ import annotations

LABELS = {
    "PASS": ("Pass", "통과"),
    "BLOCKED": ("Blocked", "차단"),
    "LOW": ("Low", "낮음"),
    "MEDIUM": ("Medium", "중간"),
    "HIGH": ("High", "높음"),
    "NORMAL": ("Normal", "정상"),
    "CORRECTION": ("Correction", "조정"),
    "SELL_OFF": ("Sell-off", "급락"),
    "VOLATILITY_SPIKE": ("Volatility Spike", "변동성 급등"),
    "CORRELATION_SHOCK": ("Correlation Shock", "상관관계 충격"),
}


def bilingual(code: str) -> dict[str, str]:
    en, ko = LABELS.get(code, (code.replace("_", " ").title(), code))
    return {"code": code, "en": en, "ko": ko}
