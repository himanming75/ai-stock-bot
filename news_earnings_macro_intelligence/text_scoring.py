from __future__ import annotations
import re

POSITIVE = {
    "beat": 1.5, "beats": 1.5, "growth": 1.0, "upgrade": 1.2,
    "record": 0.8, "strong": 0.9, "surge": 1.1, "profit": 0.8,
    "optimistic": 0.9, "raise": 1.0, "raised": 1.0, "expands": 0.7,
    "approval": 1.2, "approved": 1.2, "partnership": 0.7,
}
NEGATIVE = {
    "miss": -1.5, "misses": -1.5, "decline": -1.0, "downgrade": -1.2,
    "weak": -0.9, "loss": -0.9, "cuts": -1.0, "cut": -1.0,
    "warning": -1.1, "investigation": -1.2, "lawsuit": -1.0,
    "recall": -1.2, "layoff": -0.9, "fraud": -1.7, "default": -1.8,
}
URGENCY = {
    "breaking": 1.0, "urgent": 1.0, "halts": 0.9, "halted": 0.9,
    "sec": 0.7, "fda": 0.7, "fomc": 0.7, "guidance": 0.6,
    "bankruptcy": 1.0, "acquisition": 0.7, "merger": 0.7,
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def sentiment_score(text: str) -> float:
    score = 0.0
    for token in tokenize(text):
        score += POSITIVE.get(token, 0.0)
        score += NEGATIVE.get(token, 0.0)
    return max(-1.0, min(1.0, score / 5.0))


def urgency_score(text: str) -> float:
    score = sum(URGENCY.get(token, 0.0) for token in tokenize(text))
    return max(0.0, min(1.0, score / 2.0))
