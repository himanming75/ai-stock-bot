from __future__ import annotations
from pathlib import Path
from .i18n import bilingual
from .io import write_json


def build_report(
    *,
    optimizer: dict,
    stress_results: list[dict],
    guardrails: dict,
    output_path: Path,
) -> dict:
    report = {
        "title": {
            "en": "Portfolio Optimizer and Stress Guardrail Report",
            "ko": "포트폴리오 최적화 및 스트레스 가드레일 보고서",
        },
        "summary": {
            "en": (
                "Simulation-only candidate weights, scenario stress testing, "
                "and capital guardrail evaluation."
            ),
            "ko": (
                "시뮬레이션 전용 후보 비중, 시나리오 스트레스 테스트 및 "
                "자금 가드레일 평가입니다."
            ),
        },
        "optimizer": optimizer,
        "stress_results": [
            {
                **item,
                "scenario_i18n": bilingual(item["scenario"]),
            }
            for item in stress_results
        ],
        "guardrails": {
            **guardrails,
            "status_i18n": bilingual(guardrails["status"]),
        },
        "safety": {
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancellation_enabled": False,
            "position_allocation_enabled": False,
            "capital_lock_enabled": False,
            "live_trading_enabled": False,
            "paper_orders_during_build": 0,
            "live_orders_during_build": 0,
        },
    }
    write_json(output_path, report)
    return report
