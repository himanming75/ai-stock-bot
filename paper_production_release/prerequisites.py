from __future__ import annotations

from pathlib import Path
from typing import Any

from paper_production_release.io import load_json


SOURCE_PATHS = {
    "multi_day": (
        "release/v83_77_to_v83_80/actual/"
        "multi_day_paper_validation_result.json"
    ),
    "stability": (
        "release/v83_81_to_v83_88/actual/"
        "paper_stability_runtime_result.json"
    ),
    "readiness": (
        "release/v83_89_to_v83_96/actual/"
        "performance_production_readiness_result.json"
    ),
    "orchestrator": (
        "release/v88_09_to_v88_16/actual/"
        "paper_orchestrator_result.json"
    ),
    "robustness": (
        "release/v87_09_to_v87_16/actual/"
        "walk_forward_stress_validation_result.json"
    ),
    "multi_asset": (
        "release/v87_17_to_v87_24/actual/"
        "multi_asset_backtest_result.json"
    ),
    "web_ui": (
        "release/v88_01_to_v88_08/actual/"
        "web_ui_v2_state.json"
    ),
}


def evaluate_prerequisites(root: Path) -> dict[str, Any]:
    sources = {
        name: load_json(root / relative)
        for name, relative in SOURCE_PATHS.items()
    }

    multi_day = sources["multi_day"]
    stability = sources["stability"]
    readiness = sources["readiness"]
    orchestrator = sources["orchestrator"]
    robustness = sources["robustness"]
    multi_asset = sources["multi_asset"]
    web_ui = sources["web_ui"]

    checks = {
        "multi_day_requirement_met": (
            multi_day.get("requirement_met") is True
            or int(multi_day.get("completed_days", 0))
            >= int(multi_day.get("minimum_days", 3))
        ),
        "stability_certificate_valid": (
            stability.get("certificate_valid") is True
            or stability.get("stability_certificate_valid") is True
            or stability.get("state") == "EXTENDED_PAPER_RUNTIME_READY"
        ),
        "production_readiness_approved": (
            readiness.get("production_ready") is True
            or readiness.get("state") == "PRODUCTION_READINESS_APPROVED"
        ),
        "orchestrator_ready": (
            orchestrator.get("state")
            == "PAPER_AUTOMATION_ORCHESTRATOR_READY"
            and orchestrator.get("status") == "PASS"
            and orchestrator.get("safe_mode") is False
            and orchestrator.get("completed_step_count")
            == orchestrator.get("total_step_count")
            == 7
        ),
        "robustness_validated": (
            robustness.get("state") == "BACKTEST_ROBUSTNESS_VALIDATED"
        ),
        "multi_asset_certified": (
            multi_asset.get("state") == "MULTI_ASSET_BACKTEST_CERTIFIED"
        ),
        "web_ui_ready": (
            web_ui.get("state") == "WEB_UI_V2_READY"
        ),
    }

    blocking = [
        name for name, passed in checks.items() if not passed
    ]
    time_based = [
        name for name in (
            "multi_day_requirement_met",
            "stability_certificate_valid",
            "production_readiness_approved",
        )
        if not checks[name]
    ]
    system_based = [
        name for name in checks
        if name not in {
            "multi_day_requirement_met",
            "stability_certificate_valid",
            "production_readiness_approved",
        }
        and not checks[name]
    ]

    return {
        "checks": checks,
        "blocking_prerequisites": blocking,
        "time_based_pending": time_based,
        "system_based_pending": system_based,
        "ready": not blocking,
        "sources_available": {
            name: bool(value) for name, value in sources.items()
        },
        "source_states": {
            name: value.get("state", "NOT_AVAILABLE")
            for name, value in sources.items()
        },
    }
