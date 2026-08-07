from __future__ import annotations

import json
from pathlib import Path
from typing import Any


AI_CATEGORIES = {
    "feature_engine": (
        "Feature generation",
        [
            "feature_engine/service.py",
            "ai_feature_engine/service.py",
            "multi_timeframe_ai/engine.py",
        ],
    ),
    "signal_candidates": (
        "BUY / SELL / HOLD candidates",
        [
            "signal_candidates/service.py",
            "ai_signal_engine/service.py",
            "multi_timeframe_ai/service.py",
        ],
    ),
    "signal_scoring": (
        "AI signal scoring",
        [
            "ai_signal_scoring/service.py",
            "signal_scoring/service.py",
            "multi_timeframe_ai/engine.py",
        ],
    ),
    "weighted_ensemble": (
        "Weighted ensemble",
        [
            "weighted_ensemble/service.py",
            "ensemble_engine/service.py",
            "multi_timeframe_ai/engine.py",
        ],
    ),
    "multi_timeframe": (
        "Multi-timeframe analysis",
        [
            "multi_timeframe_ai/service.py",
            "multi_timeframe_ai/engine.py",
        ],
    ),
    "market_regime": (
        "Market regime",
        [
            "multi_timeframe_ai/engine.py",
            "market_regime/service.py",
            "regime_engine/service.py",
        ],
    ),
    "confidence_engine": (
        "Confidence calibration",
        [
            "multi_timeframe_ai/engine.py",
            "confidence_engine/service.py",
        ],
    ),
    "explainability": (
        "Explainability",
        [
            "explainability/service.py",
            "ai_explainability/service.py",
            "multi_timeframe_ai/report.py",
        ],
    ),
    "ranking_selection": (
        "Candidate ranking and selection",
        [
            "portfolio_context_ai/service.py",
            "portfolio_optimizer_ai/service.py",
            "ranking_engine/service.py",
        ],
    ),
    "portfolio_context": (
        "Portfolio context and correlation",
        [
            "portfolio_context_ai/service.py",
            "portfolio_context_ai/engine.py",
        ],
    ),
    "portfolio_optimizer": (
        "Portfolio optimizer and guardrails",
        [
            "portfolio_optimizer_ai/service.py",
            "portfolio_optimizer_ai/optimizer.py",
        ],
    ),
    "backtest_bridge": (
        "Offline backtest bridge",
        [
            "offline_backtest_bridge/service.py",
            "backtest_bridge/service.py",
        ],
    ),
    "bilingual_reporting": (
        "English and Korean report/dashboard",
        [
            "multi_timeframe_ai/report.py",
            "multi_timeframe_ai/dashboard.py",
            "portfolio_optimizer_ai/report.py",
        ],
    ),
}

EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
    "release", "runtime", "output", "dist", "build", "tests", "test",
    "fixtures", "fixture", "samples", "sample", "examples", "example",
    "mock", "mocks", "sandbox",
}

EXCLUDED_TOKENS = {
    "test", "mock", "sample", "fixture", "example", "deprecated",
    "legacy", "backup", "old",
}

POSITIVE_TOKENS = {
    "service": 12,
    "engine": 10,
    "feature": 8,
    "signal": 8,
    "ensemble": 10,
    "regime": 10,
    "confidence": 10,
    "explain": 8,
    "portfolio": 8,
    "optimizer": 10,
    "report": 5,
    "dashboard": 4,
    "actual": 4,
    "latest": 3,
}


def _normalize(value: str) -> str:
    return value.replace("\\", "/").strip("/")


def _is_operational_python(path: str) -> bool:
    normalized = _normalize(path)
    low = normalized.lower()
    parts = low.split("/")
    if Path(low).suffix != ".py":
        return False
    if any(part in EXCLUDED_PARTS for part in parts):
        return False
    name_tokens = set(Path(low).stem.replace("-", "_").split("_"))
    if name_tokens & EXCLUDED_TOKENS:
        return False
    if Path(low).name.startswith("test_"):
        return False
    if low.startswith("tools/test_"):
        return False
    return True


def _score(category: str, item: dict[str, Any]) -> int:
    path = _normalize(item["path"])
    low = path.lower()
    preferred = AI_CATEGORIES[category][1]
    if path in preferred:
        return 10000 - preferred.index(path)

    value = int(item.get("score", 0))
    for token, bonus in POSITIVE_TOKENS.items():
        if token in low:
            value += bonus

    value -= len(Path(path).parts)
    if low.startswith("tools/"):
        value -= 20
    if low.endswith("/__init__.py"):
        value -= 30
    return value


def _matches(category: str, item: dict[str, Any]) -> bool:
    path = _normalize(item["path"]).lower()
    functions = " ".join(item.get("functions", [])).lower()
    classes = " ".join(item.get("classes", [])).lower()
    text = f"{path} {functions} {classes}"

    patterns = {
        "feature_engine": ("feature",),
        "signal_candidates": ("signal", "candidate"),
        "signal_scoring": ("signal", "score"),
        "weighted_ensemble": ("ensemble", "weight"),
        "multi_timeframe": ("multi_timeframe", "timeframe"),
        "market_regime": ("regime",),
        "confidence_engine": ("confidence", "calibrat"),
        "explainability": ("explain", "reason"),
        "ranking_selection": ("rank", "select", "candidate"),
        "portfolio_context": ("portfolio_context", "correlation"),
        "portfolio_optimizer": ("portfolio_optimizer", "optimizer"),
        "backtest_bridge": ("backtest_bridge", "offline_backtest"),
        "bilingual_reporting": ("report", "dashboard", "i18n"),
    }

    return any(pattern in text for pattern in patterns[category])


def canonicalize_ai_engine(audit: dict[str, Any]) -> dict[str, Any]:
    records = [
        item for item in audit.get("records", [])
        if _is_operational_python(item["path"])
    ]

    selected = {}
    missing = []

    for category, (label, _) in AI_CATEGORIES.items():
        candidates = []
        for item in records:
            if _matches(category, item):
                candidate = dict(item)
                candidate["ai_canonical_score"] = _score(category, item)
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                item["ai_canonical_score"],
                item.get("modified_ns", 0),
                -len(item["path"]),
            ),
            reverse=True,
        )

        selected[category] = {
            "label": label,
            "selected": candidates[0] if candidates else None,
            "alternatives": candidates[1:5],
            "candidate_count": len(candidates),
        }
        if not candidates:
            missing.append(category)

    prohibited_expansions = [
        "NEWS_ANALYSIS",
        "EARNINGS_ANALYSIS",
        "ECONOMIC_INDICATORS",
        "OPTIONS_DATA",
        "SOCIAL_SENTIMENT",
        "REINFORCEMENT_LEARNING",
        "LLM_DECISION_ENGINE",
        "AUTO_MODEL_RETRAINING",
    ]

    return {
        "stage": "PHASE2_AI_ENGINE_CANONICALIZATION",
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "scope_locked": True,
        "new_ai_feature_development_allowed": False,
        "existing_ai_code_only": True,
        "actual_market_day_validation_performed": False,
        "selected": selected,
        "missing_categories": missing,
        "prohibited_expansions_until_operational_review": prohibited_expansions,
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
