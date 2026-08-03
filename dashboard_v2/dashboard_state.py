from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_SOURCES = {
    "paper_autonomous": (
        "release/v83_73_to_v83_76/actual/paper_autonomous_mode_result.json"
    ),
    "multi_day_validation": (
        "release/v83_77_to_v83_80/actual/"
        "multi_day_paper_validation_result.json"
    ),
    "stability_runtime": (
        "release/v83_81_to_v83_88/actual/"
        "paper_stability_runtime_result.json"
    ),
    "performance_readiness": (
        "release/v83_89_to_v83_96/actual/"
        "performance_production_readiness_result.json"
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def source_summary(name: str, path: Path) -> dict[str, Any]:
    value = load_json(path)
    return {
        "name": name,
        "available": bool(value),
        "path": str(path),
        "state": value.get("state", "NOT_AVAILABLE"),
        "status": value.get("status", "NOT_AVAILABLE"),
        "stage": value.get("stage", ""),
        "stage_range": value.get("stage_range", ""),
        "observed_at": value.get("observed_at", ""),
        "next_phase": value.get("next_phase", ""),
        "blocking_issue_count": value.get("blocking_issue_count", 0),
        "issue_count": value.get("issue_count", 0),
        "paper_only": value.get("paper_only", True),
        "broker_write_enabled": value.get("broker_write_enabled", False),
        "order_submission_enabled": value.get(
            "order_submission_enabled", False
        ),
        "live_trading_enabled": value.get("live_trading_enabled", False),
        "external_network_enabled": value.get(
            "external_network_enabled", False
        ),
        "payload": value,
    }


def build_dashboard_state(root: Path) -> dict[str, Any]:
    sources = {
        name: source_summary(name, root / relative)
        for name, relative in STATE_SOURCES.items()
    }

    available_count = sum(
        1 for item in sources.values() if item["available"]
    )
    blocking_count = sum(
        int(item.get("blocking_issue_count", 0))
        for item in sources.values()
    )
    safety_violations = []
    for name, item in sources.items():
        if item["broker_write_enabled"]:
            safety_violations.append(f"{name}:broker_write")
        if item["order_submission_enabled"]:
            safety_violations.append(f"{name}:order_submission")
        if item["live_trading_enabled"]:
            safety_violations.append(f"{name}:live_trading")
        if item["external_network_enabled"]:
            safety_violations.append(f"{name}:external_network")

    performance = sources["performance_readiness"]["payload"]
    multi_day = sources["multi_day_validation"]["payload"]
    stability = sources["stability_runtime"]["payload"]

    return {
        "dashboard_stage_range": "V85.01-V85.08",
        "dashboard_state": (
            "DASHBOARD_V2_SAFE"
            if not safety_violations and blocking_count == 0
            else "DASHBOARD_V2_ATTENTION_REQUIRED"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available_source_count": available_count,
        "total_source_count": len(sources),
        "blocking_issue_count": blocking_count,
        "safety_violations": safety_violations,
        "paper_only": True,
        "read_only": True,
        "external_network_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "summary": {
            "validation_completed_days": multi_day.get(
                "completed_days", 0
            ),
            "validation_remaining_days": multi_day.get(
                "remaining_days", 0
            ),
            "stability_score": stability.get("stability_score", 0),
            "stability_certificate_valid": stability.get(
                "certificate_valid", False
            ),
            "performance_score": performance.get(
                "metrics", {}
            ).get("performance_score", 0),
            "risk_gate_passed": performance.get(
                "risk_gate_passed", False
            ),
            "production_ready": performance.get(
                "production_ready", False
            ),
        },
        "sources": sources,
    }
