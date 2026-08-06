from __future__ import annotations

LABELS = {
    "LOW": ("Low", "낮음"),
    "MEDIUM": ("Medium", "중간"),
    "HIGH": ("High", "높음"),
    "DIVERSIFIED": ("Diversified", "분산"),
    "CONCENTRATED": ("Concentrated", "집중"),
    "POSITIVE": ("Positive", "양의 상관"),
    "NEGATIVE": ("Negative", "음의 상관"),
    "NEUTRAL": ("Neutral", "중립"),
    "IMPROVING": ("Improving", "개선"),
    "STABLE": ("Stable", "안정"),
    "DEGRADING": ("Degrading", "악화"),
}


def bilingual(code: str) -> dict[str, str]:
    en, ko = LABELS.get(code, (code.replace("_", " ").title(), code))
    return {"code": code, "en": en, "ko": ko}
