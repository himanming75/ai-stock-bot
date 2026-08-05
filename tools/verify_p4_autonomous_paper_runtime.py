from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT
        / "release/p4_autonomous_paper_runtime/actual/"
          "p4_runtime_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "P4",
    "status": result.get("status") == "PASS",
    "state": (
        result.get("state")
        == "AUTONOMOUS_PAPER_RUNTIME_SESSION_COMPLETE"
    ),
    "three_cycles": result.get("completed_cycle_count") == 3,
    "no_blockers": result.get("blockers") == [],
    "broker_write_off": result.get("broker_write_enabled") is False,
    "paper_submission_off": result.get("paper_submission_enabled") is False,
    "live_submission_off": result.get("live_submission_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "next_fixed_stage": (
        result.get("next_fixed_stage")
        == "P5_PAPER_LONG_RUN_QUALIFICATION"
    ),
}

verification = {
    "verification_stage": "P4",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
