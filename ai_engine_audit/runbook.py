from __future__ import annotations

from pathlib import Path


ORDER = [
    "feature_engine",
    "signal_candidates",
    "signal_scoring",
    "weighted_ensemble",
    "multi_timeframe",
    "market_regime",
    "confidence_engine",
    "explainability",
    "ranking_selection",
    "portfolio_context",
    "portfolio_optimizer",
    "backtest_bridge",
    "bilingual_reporting",
]


def build_markdown(result: dict) -> str:
    lines = [
        "# Phase 2 AI Engine Canonical Runbook",
        "",
        "## Fixed operating scope",
        "",
        "- Existing AI code only",
        "- No new model family",
        "- No news, options, RL, LLM, or retraining expansion",
        "- File deletion is prohibited",
        "- One canonical path per AI capability",
        "- Improvements are deferred until Paper operation data exists",
        "",
        "## Canonical AI pipeline",
        "",
        "| # | Capability | Selected path | Candidate count |",
        "|---:|---|---|---:|",
    ]

    for index, category in enumerate(ORDER, start=1):
        item = result["selected"][category]
        selected = item["selected"]
        path = selected["path"] if selected else "MISSING"
        lines.append(
            f"| {index} | {item['label']} | `{path}` | "
            f"{item['candidate_count']} |"
        )

    lines.extend([
        "",
        "## Operating flow",
        "",
        "Market data → Feature Engine → Signal Candidates → Signal Scoring → "
        "Weighted Ensemble → Multi-Timeframe → Market Regime → Confidence → "
        "Explainability → Ranking → Portfolio Context → Portfolio Optimizer → "
        "Paper execution handoff",
        "",
        "## Deferred until operational data review",
        "",
    ])

    for item in result["prohibited_expansions_until_operational_review"]:
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def save_markdown(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown(result), encoding="utf-8")
