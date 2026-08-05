from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_15a/actual/fully_autonomous_paper_qualification_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
certificate = evaluation.get("certificate", {})

checks = {
    "stage": result.get("stage") == "V392.15A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "FULLY_AUTONOMOUS_PAPER_TRADING_QUALIFIED",
        "FULLY_AUTONOMOUS_PAPER_TRADING_NOT_QUALIFIED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "certificate_present": isinstance(certificate, dict),
    "certificate_hash_present": isinstance(
        evaluation.get("certificate_hash"), str
    ),
    "replay_protection_verified": (
        result.get("replay_protection_verified") is True
    ),
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.15A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "qualified": result.get(
        "fully_autonomous_local_paper_trading_ready"
    ) is True,
    "qualification_state": certificate.get("qualification_state"),
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
