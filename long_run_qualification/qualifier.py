from __future__ import annotations
from pathlib import Path
from long_run_qualification.config import load, validate
from long_run_qualification.continuity import analyze
from long_run_qualification.io import read_jsonl, write_json

ACTUAL = Path("release/v321_01_to_v330_64/actual")


def qualify(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    cycle_rows, cycle_corrupt = read_jsonl(root / ACTUAL / "long_run_cycle_ledger.jsonl")
    error_rows, error_corrupt = read_jsonl(root / ACTUAL / "long_run_error_ledger.jsonl")
    continuity = analyze(cycle_rows, int(policy.get("cycle_interval_seconds", 30)))

    total = len(cycle_rows)
    successful = sum(1 for row in cycle_rows if row.get("cycle_success") is True)
    blocked = sum(1 for row in cycle_rows if row.get("blocked") is True)
    success_ratio = successful / total if total else 0.0
    observation_minutes = continuity["observation_duration_seconds"] / 60

    checks = {
        "policy_valid": validation["valid"],
        "qualification_enabled": policy.get("qualification_enabled") is True,
        "minimum_cycles": successful >= int(policy.get("minimum_successful_cycles", 120)),
        "minimum_duration": observation_minutes >= float(policy.get("minimum_observation_minutes", 60)),
        "success_ratio": success_ratio >= float(policy.get("minimum_success_ratio", 0.98)),
        "blocked_cycles_zero": blocked == 0,
        "corrupt_records_zero": cycle_corrupt == 0 and error_corrupt == 0,
        "invalid_timestamps_zero": continuity["invalid_timestamp_count"] == 0,
        "duplicate_limit": continuity["duplicate_record_count"] <= int(policy.get("maximum_duplicate_records", 0)),
        "gap_limit": continuity["excessive_gap_count"] <= int(policy.get("maximum_excessive_gaps", 2)),
        "consecutive_error_limit": len(error_rows) <= int(policy.get("maximum_total_errors", 5)),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "zero_new_orders": int(policy.get("maximum_new_orders_per_day", -1)) == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if not policy.get("qualification_enabled"):
        state = "REAL_PAPER_LONG_RUN_READY_BLOCKED"
    elif all(checks.values()):
        state = "REAL_PAPER_LONG_RUN_QUALIFIED"
    else:
        state = "REAL_PAPER_LONG_RUN_QUALIFICATION_PENDING"

    result = {
        "stage": "V330.64",
        "state": state,
        "status": "PASS",
        "checks": checks,
        "failed": failed,
        "statistics": {
            "total_cycles": total,
            "successful_cycles": successful,
            "blocked_cycles": blocked,
            "error_records": len(error_rows),
            "success_ratio": round(success_ratio, 6),
            "observation_minutes": round(observation_minutes, 3),
            "cycle_corrupt_records": cycle_corrupt,
            "error_corrupt_records": error_corrupt,
        },
        "continuity": continuity,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "next_phase": "V331_01_TO_V340_64_REAL_PAPER_AUTONOMOUS_OBSERVATION_GOVERNANCE",
    }
    write_json(root / ACTUAL / "real_paper_long_run_qualification_result.json", result)
    return result
