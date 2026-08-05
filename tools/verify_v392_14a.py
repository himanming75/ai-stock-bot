from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_14a/actual/autonomous_paper_cycle_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
report = evaluation.get("cycle_report", {})

checks = {
    "stage": result.get("stage") == "V392.14A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_READY",
        "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "cycle_report_present": isinstance(report, dict),
    "cycle_hash_present": isinstance(evaluation.get("cycle_hash"), str),
    "stage_summaries_present": isinstance(report.get("stage_summaries"), list),
    "replay_protection_enabled": (
        result.get("single_cycle_replay_protection_enabled") is True
    ),
    "fail_closed_enabled": result.get("fail_closed_enabled") is True,
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.14A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "cycle_completed": result.get("cycle_completed") is True,
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
