TEXT = {
    "BUY": {"en": "Buy", "ko": "매수"},
    "SELL": {"en": "Sell", "ko": "매도"},
    "HOLD": {"en": "Hold", "ko": "보유"},
    "LOW": {"en": "Low Risk", "ko": "낮은 리스크"},
    "MEDIUM": {"en": "Medium Risk", "ko": "중간 리스크"},
    "HIGH": {"en": "High Risk", "ko": "높은 리스크"},
    "READY": {"en": "Ready", "ko": "준비 완료"},
    "BLOCKED": {"en": "Blocked", "ko": "차단됨"},
}

def bilingual(key: str) -> dict:
    return dict(TEXT.get(key, {"en": key, "ko": key}))
