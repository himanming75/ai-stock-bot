from __future__ import annotations
from typing import Any

def evaluate(candidate: dict[str, Any], risk: dict[str, Any], exits: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    symbol = candidate.get("symbol")
    exit_symbols = {
        row.get("symbol")
        for row in exits.get("snapshot", {}).get("rows", [])
        if row.get("exit_triggered")
    }
    risk_passed = risk.get("risk_gate", {}).get("passed") is True
    checks = {
        "candidate_present": bool(candidate),
        "confidence_sufficient": float(candidate.get("confidence", 0) or 0) >= float(policy["minimum_final_confidence"]),
        "risk_gate_passed": risk_passed if policy.get("risk_gate_required") else True,
        "no_exit_conflict": symbol not in exit_symbols if policy.get("exit_conflict_blocks_entry") else True,
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {"passed": not failed, "checks": checks, "failed": failed}
