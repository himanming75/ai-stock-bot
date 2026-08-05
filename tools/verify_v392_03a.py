from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_03a/actual/dispatch_preparation_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V392.03A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "DISPATCH_PREPARATION_GATE_READY",
        "DISPATCH_PREPARATION_GATE_BLOCKED",
    },
    "evaluation_present": isinstance(result.get("evaluation"), dict),
    "dispatch_execution_disabled": (
        result.get("dispatch_execution_allowed") is False
    ),
    "automatic_dispatch_disabled": (
        result.get("automatic_dispatch_enabled") is False
    ),
    "replay_protection_enabled": (
        result.get("replay_protection_enabled") is True
    ),
    "paper_only": result.get("paper_endpoint_only") is True,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.03A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
