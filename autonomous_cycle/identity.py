from __future__ import annotations
from typing import Any
from autonomous_cycle.io import digest

def build_cycle_identity(
    decision_result: dict[str, Any],
    policy: dict[str, Any],
    cycle_date: str,
) -> dict[str, Any]:
    decision_id = str(decision_result.get("decision_id", ""))
    decision = str(
        decision_result.get("autonomous_decision", {}).get("decision", "")
    )
    base = {
        "decision_id": decision_id,
        "decision": decision,
        "cycle_date": cycle_date,
        "policy_version": policy.get("policy_version"),
    }
    return {
        "cycle_key": digest(base),
        "cycle_id": digest({"cycle": base, "kind": "V103"})[:24],
        "source_decision_id": decision_id,
        "cycle_date": cycle_date,
    }
