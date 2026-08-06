from __future__ import annotations
from pathlib import Path
from .i18n import bilingual
from .io import write_json


def build_report(
    *,
    portfolio_context: dict,
    signal_feedback: dict,
    performance: dict,
    output_path: Path,
) -> dict:
    report = {
        "title": {
            "en": "Portfolio Context and Signal Feedback Report",
            "ko": "포트폴리오 컨텍스트 및 신호 피드백 보고서",
        },
        "summary": {
            "en": (
                "Read-only portfolio concentration, cross-asset correlation, "
                "offline feedback, and performance analytics."
            ),
            "ko": (
                "읽기 전용 포트폴리오 집중도, 자산 간 상관관계, "
                "오프라인 피드백 및 성과 분석입니다."
            ),
        },
        "portfolio_context": {
            **portfolio_context,
            "portfolio_risk_level_i18n": bilingual(
                portfolio_context["portfolio_risk_level"]
            ),
            "diversification_state_i18n": bilingual(
                portfolio_context["diversification_state"]
            ),
        },
        "signal_feedback": {
            **signal_feedback,
            "feedback_health_i18n": bilingual(
                signal_feedback["feedback_health"]
            ),
        },
        "performance": performance,
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancellation_enabled": False,
            "position_allocation_enabled": False,
            "automatic_model_update_enabled": False,
            "live_learning_enabled": False,
            "live_trading_enabled": False,
            "paper_orders_during_build": 0,
            "live_orders_during_build": 0,
        },
    }
    write_json(output_path, report)
    return report
