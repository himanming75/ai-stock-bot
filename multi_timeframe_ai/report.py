from __future__ import annotations
from pathlib import Path
from .i18n import bilingual
from .io import write_json


def build_report(*, analyses: list[dict], output_path: Path) -> dict:
    rows = []
    for item in analyses:
        rows.append({
            **item,
            "action_i18n": bilingual(item["action"]),
            "market_regime_2_i18n": bilingual(item["market_regime_2"]),
            "dominant_structure_i18n": bilingual(item["dominant_structure"]),
        })

    report = {
        "title": {
            "en": "Multi-Timeframe AI and Market Regime 2.0 Report",
            "ko": "멀티 타임프레임 AI 및 시장 국면 2.0 보고서",
        },
        "summary": {
            "en": (
                "Read-only analysis across 1m, 3m, 5m, 15m, 30m, "
                "1h, and daily timeframes."
            ),
            "ko": (
                "1분, 3분, 5분, 15분, 30분, 1시간, 일봉을 "
                "통합한 읽기 전용 분석입니다."
            ),
        },
        "columns": {
            "symbol": {"en": "Symbol", "ko": "종목"},
            "action": {"en": "Action", "ko": "신호"},
            "regime": {"en": "Regime", "ko": "시장 국면"},
            "probability": {"en": "Probability", "ko": "확률"},
            "expected_return": {"en": "Expected Return", "ko": "기대수익"},
            "expected_risk": {"en": "Expected Risk", "ko": "기대위험"},
            "reward_risk": {"en": "Reward/Risk", "ko": "보상/위험"},
            "confidence": {"en": "Calibrated Confidence", "ko": "보정 신뢰도"},
        },
        "analyses": rows,
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancellation_enabled": False,
            "position_allocation_enabled": False,
            "live_trading_enabled": False,
            "paper_orders_during_build": 0,
            "live_orders_during_build": 0,
        },
    }
    write_json(output_path, report)
    return report
