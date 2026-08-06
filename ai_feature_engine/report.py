from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json


def write_report(
    *,
    candidates: list[dict],
    output_path: Path,
) -> dict:
    counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for item in candidates:
        counts[item["action"]] += 1

    report = {
        "report_type": "AI_SIGNAL_CANDIDATE_REPORT",
        "report_title": {
            "en": "AI Signal Candidate Report",
            "ko": "AI 신호 후보 보고서",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "OFFLINE_SIGNAL_CANDIDATES_ONLY",
        "summary": {
            "total": len(candidates),
            "buy_candidates": counts["BUY"],
            "sell_candidates": counts["SELL"],
            "hold_candidates": counts["HOLD"],
        },
        "candidates": candidates,
        "safety": {
            "configuration_activation_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "live_trading_enabled": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
