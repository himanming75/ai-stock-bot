from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_10a/actual/local_paper_dispatch_engine_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V392.10A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "LOCAL_PAPER_DISPATCH_ENGINE_READY",
        "LOCAL_PAPER_DISPATCH_ENGINE_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "local_order_present": isinstance(evaluation.get("local_order"), dict),
    "local_order_hash_present": isinstance(
        evaluation.get("local_order_hash"), str
    ),
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "broker_network_unused": evaluation.get("broker_network_used") is False,
    "broker_submission_not_attempted": (
        evaluation.get("broker_submission_attempted") is False
    ),
    "queue_mutation_disabled": result.get("queue_mutation_enabled") is False,
    "automatic_dispatch_disabled": (
        result.get("automatic_dispatch_enabled") is False
    ),
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.10A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
