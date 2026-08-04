from __future__ import annotations
from pathlib import Path
from typing import Any
from continuous_autonomous_engine.io import load_json

def collect_sources(root: Path) -> dict[str, Any]:
    return {
        "scheduler": load_json(
            root/"release/v103_33_to_v103_64/actual/"
            "multi_day_scheduler_result.json"
        ),
        "cycle": load_json(
            root/"release/v103_01_to_v103_32/actual/"
            "autonomous_cycle_result.json"
        ),
        "decision": load_json(
            root/"release/v102_33_to_v102_64/actual/"
            "autonomous_decision_result.json"
        ),
        "risk": load_json(
            root/"release/v100_01_to_v100_32/actual/"
            "ai_risk_manager_result.json"
        ),
        "adaptive_rebalance": load_json(
            root/"release/v101_33_to_v101_64/actual/"
            "adaptive_rebalance_optimization_result.json"
        ),
    }

def validate_sources(sources: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "scheduler_ready": sources["scheduler"].get("state")
            == "MULTI_DAY_SCHEDULER_READY",
        "cycle_allowed": sources["cycle"].get("state") in {
            "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
            "AUTONOMOUS_CYCLE_HOLD",
            "AUTONOMOUS_CYCLE_REVIEW_REQUIRED",
            "AUTONOMOUS_CYCLE_BLOCKED",
        },
        "decision_valid": sources["decision"].get("status") == "PASS",
        "risk_valid": sources["risk"].get("state") == "AI_RISK_MANAGER_READY",
        "adaptive_valid": sources["adaptive_rebalance"].get("state") in {
            "ADAPTIVE_REBALANCE_OPTIMIZATION_READY",
            "ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION",
        },
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {"passed": not failed, "checks": checks, "failed": failed}
