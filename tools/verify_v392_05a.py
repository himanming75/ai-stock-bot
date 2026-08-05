from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_05a/actual/queue_inspection_gate_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V392.05A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "QUEUE_INSPECTION_GATE_READY",
        "QUEUE_INSPECTION_GATE_BLOCKED",
    },
    "evaluation_present": isinstance(result.get("evaluation"), dict),
    "health_score_present": isinstance(
        result.get("evaluation", {}).get("health_score"), (int, float)
    ),
    "queue_hash_present": isinstance(
        result.get("evaluation", {}).get("queue_hash"), str
    ),
    "dispatch_execution_disabled": (
        result.get("dispatch_execution_allowed") is False
    ),
    "automatic_release_disabled": (
        result.get("automatic_release_enabled") is False
    ),
    "queue_mutation_disabled": result.get("queue_mutation_enabled") is False,
    "fifo_enforced": result.get("fifo_enforced") is True,
    "paper_only": result.get("paper_endpoint_only") is True,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.05A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
