from __future__ import annotations
from pathlib import Path
from .io import read_json


def load_signal_candidates(path: Path) -> list[dict]:
    report = read_json(path)
    analyses = report.get("analyses", [])
    return analyses if isinstance(analyses, list) else []


def select_candidate(
    candidates: list[dict],
    *,
    allowed_symbols: tuple[str, ...],
    min_confidence: float,
    min_reward_risk: float,
) -> dict | None:
    eligible = []
    for item in candidates:
        symbol = str(item.get("symbol", "")).upper()
        action = str(item.get("action", "HOLD")).upper()
        confidence = float(
            item.get("confidence_calibration", {}).get(
                "calibrated_confidence", 0.0
            )
        )
        reward_risk = float(item.get("reward_risk", 0.0))
        guardrail_ok = bool(item.get("execution_mode") == "ANALYSIS_ONLY")
        if (
            symbol in allowed_symbols
            and action in {"BUY", "SELL"}
            and confidence >= min_confidence
            and reward_risk >= min_reward_risk
            and guardrail_ok
        ):
            eligible.append(
                (
                    confidence,
                    reward_risk,
                    {
                        "symbol": symbol,
                        "side": action.lower(),
                        "confidence": round(confidence, 6),
                        "reward_risk": round(reward_risk, 6),
                        "consensus_score": float(
                            item.get("consensus_score", 0.0)
                        ),
                    },
                )
            )
    if not eligible:
        return None
    eligible.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return eligible[0][2]
