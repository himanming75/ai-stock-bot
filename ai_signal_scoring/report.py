from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json


def build_report(
    *,
    ranked_candidates: list[dict],
    backtest_results: dict,
    output_path: Path,
) -> dict:
    top_buy = next(
        (item for item in ranked_candidates if item.get("action") == "BUY"),
        None,
    )
    top_sell = next(
        (item for item in ranked_candidates if item.get("action") == "SELL"),
        None,
    )

    report = {
        "report_type": "AI_ENSEMBLE_SCORING_REPORT",
        "report_title": {
            "en": "AI Ensemble Scoring and Backtest Bridge Report",
            "ko": "AI 앙상블 점수 및 백테스트 연결 보고서",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "OFFLINE_ANALYSIS_ONLY",
        "summary": {
            "candidate_count": len(ranked_candidates),
            "top_buy_symbol": None if top_buy is None else top_buy["symbol"],
            "top_sell_symbol": None if top_sell is None else top_sell["symbol"],
            "average_ai_score": round(
                sum(item["ai_score"] for item in ranked_candidates)
                / max(1, len(ranked_candidates)),
                2,
            ),
        },
        "ranked_candidates": ranked_candidates,
        "backtest_bridge": backtest_results,
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "position_allocation_enabled": False,
            "configuration_activation_enabled": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
