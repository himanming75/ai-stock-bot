from __future__ import annotations

LABELS = {
    "STRONG_BULL": ("Strong Bull", "강한 상승"),
    "WEAK_BULL": ("Weak Bull", "약한 상승"),
    "RANGE": ("Range", "횡보"),
    "WEAK_BEAR": ("Weak Bear", "약한 하락"),
    "STRONG_BEAR": ("Strong Bear", "강한 하락"),
    "BREAKOUT": ("Breakout", "돌파"),
    "FAKE_BREAKOUT": ("Fake Breakout", "가짜 돌파"),
    "GAP_UP": ("Gap Up", "갭 상승"),
    "GAP_DOWN": ("Gap Down", "갭 하락"),
    "NORMAL": ("Normal", "일반"),
    "BUY": ("Buy", "매수"),
    "SELL": ("Sell", "매도"),
    "HOLD": ("Hold", "보유"),
}


def bilingual(code: str) -> dict[str, str]:
    en, ko = LABELS.get(code, (code.replace("_", " ").title(), code))
    return {"code": code, "en": en, "ko": ko}
