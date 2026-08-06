TEXT = {
    "BUY": {"en": "Buy Candidate", "ko": "매수 후보"},
    "SELL": {"en": "Sell Candidate", "ko": "매도 후보"},
    "HOLD": {"en": "Hold Candidate", "ko": "보유 후보"},
    "TREND_UP": {"en": "Uptrend", "ko": "상승 추세"},
    "TREND_DOWN": {"en": "Downtrend", "ko": "하락 추세"},
    "TREND_SIDEWAYS": {"en": "Sideways", "ko": "횡보"},
    "REGIME_TRENDING": {"en": "Trending Market", "ko": "추세 시장"},
    "REGIME_VOLATILE": {"en": "Volatile Market", "ko": "고변동성 시장"},
    "REGIME_RANGE": {"en": "Range Market", "ko": "박스권 시장"},
    "READY": {"en": "Ready", "ko": "준비 완료"},
    "BLOCKED": {"en": "Blocked", "ko": "차단됨"},
}

def bilingual(key: str) -> dict:
    return dict(TEXT.get(key, {"en": key, "ko": key}))
