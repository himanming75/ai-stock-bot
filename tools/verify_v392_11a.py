from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_11a/actual/paper_execution_simulator_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V392.11A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "PAPER_EXECUTION_SIMULATOR_READY",
        "PAPER_EXECUTION_SIMULATOR_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "fill_event_present": isinstance(evaluation.get("fill_event"), dict),
    "fill_event_hash_present": isinstance(
        evaluation.get("fill_event_hash"), str
    ),
    "partial_fill_supported": result.get("partial_fill_supported") is True,
    "slippage_supported": result.get("slippage_supported") is True,
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "broker_orders_zero": evaluation.get("actual_broker_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.11A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
