from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classifier import classify
from .config import load, validate
from .io import append_jsonl, read_json, read_jsonl, write_json

LONG_RUN_ACTUAL = Path("release/v321_01_to_v330_64/actual")
GOV_ACTUAL = Path("release/v331_01_to_v340_64/actual")


def govern(root: Path, qualification_path: Path | None = None, persist: bool = True) -> dict[str, Any]:
    policy = load(root)
    policy_validation = validate(policy)

    qpath = qualification_path or (root / LONG_RUN_ACTUAL / "real_paper_long_run_qualification_result.json")
    qualification = read_json(qpath)

    cycle_rows, cycle_corrupt = read_jsonl(root / LONG_RUN_ACTUAL / "long_run_cycle_ledger.jsonl")
    error_rows, error_corrupt = read_jsonl(root / LONG_RUN_ACTUAL / "long_run_error_ledger.jsonl")
    corrupt_records = cycle_corrupt + error_corrupt

    qchecks = qualification.get("checks", {})
    statistics = qualification.get("statistics", {})
    continuity = qualification.get("continuity", {})

    required_cycles = int(policy.get("minimum_successful_cycles", 120))
    required_minutes = float(policy.get("minimum_observation_minutes", 60))
    minimum_ratio = float(policy.get("minimum_success_ratio", 0.98))
    maximum_gaps = int(policy.get("maximum_excessive_gaps", 2))

    checks = {
        "qualification_gate": qualification.get("state") == policy.get("required_qualification_state"),
        "qualification_status_pass": qualification.get("status") == "PASS",
        "minimum_cycles": int(statistics.get("successful_cycles", 0)) >= required_cycles,
        "minimum_duration": float(statistics.get("observation_minutes", 0)) >= required_minutes,
        "minimum_success_ratio": float(statistics.get("success_ratio", 0)) >= minimum_ratio,
        "zero_blocked_cycles": int(statistics.get("blocked_cycles", 0)) == 0,
        "zero_errors": int(statistics.get("error_records", 0)) == 0,
        "ledger_integrity": corrupt_records == 0,
        "continuity_healthy": (
            int(continuity.get("invalid_timestamp_count", 0)) == 0
            and int(continuity.get("duplicate_record_count", 0)) == 0
            and int(continuity.get("excessive_gap_count", 0)) <= maximum_gaps
        ),
        "safety_policy_valid": (
            qchecks.get("paper_submission_disabled") is True
            and qchecks.get("live_submission_disabled") is True
            and qchecks.get("broker_write_disabled") is True
            and qchecks.get("zero_new_orders") is True
            and policy_validation["valid"]
        ),
        "paper_orders_zero": int(qualification.get("actual_paper_orders_submitted", -1)) == 0,
        "live_orders_zero": int(qualification.get("actual_live_orders_submitted", -1)) == 0,
    }

    health, incidents = classify(checks, statistics, corrupt_records)
    failed = [name for name, passed in checks.items() if not passed]
    qualified = all(checks.values()) and health == "HEALTHY"

    now = datetime.now(timezone.utc).isoformat()
    result = {
        "stage": "V340.64",
        "state": (
            "REAL_PAPER_OBSERVATION_GOVERNANCE_QUALIFIED"
            if qualified
            else "REAL_PAPER_OBSERVATION_GOVERNANCE_BLOCKED"
        ),
        "status": "PASS",
        "health": health,
        "observed_at": now,
        "checks": checks,
        "failed": failed,
        "incidents": incidents,
        "statistics": {
            "cycle_ledger_records": len(cycle_rows),
            "error_ledger_records": len(error_rows),
            "corrupt_records": corrupt_records,
            "successful_cycles": int(statistics.get("successful_cycles", 0)),
            "observation_minutes": float(statistics.get("observation_minutes", 0)),
            "success_ratio": float(statistics.get("success_ratio", 0)),
            "blocked_cycles": int(statistics.get("blocked_cycles", 0)),
            "excessive_gap_count": int(continuity.get("excessive_gap_count", 0)),
            "maximum_gap_seconds": float(continuity.get("maximum_gap_seconds", 0)),
        },
        "qualification_source": str(qpath),
        "governance_mode": "READ_ONLY_MONITOR",
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "next_phase": "V341_01_TO_V350_64_REAL_PAPER_GOVERNED_DECISION_BRIDGE",
    }

    if persist:
        write_json(root / GOV_ACTUAL / "latest_governance_result.json", result)
        checkpoint = {
            "stage": "V340.64",
            "state": result["state"],
            "health": health,
            "observed_at": now,
            "qualified": qualified,
            "incident_count": len(incidents),
        }
        write_json(root / GOV_ACTUAL / "governance_checkpoint.json", checkpoint)
        append_jsonl(root / GOV_ACTUAL / "governance_ledger.jsonl", result)
        if incidents:
            append_jsonl(root / GOV_ACTUAL / "governance_incident_ledger.jsonl", {
                "observed_at": now,
                "health": health,
                "incidents": incidents,
                "failed": failed,
            })
    return result
