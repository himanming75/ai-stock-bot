from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT
        / "release/p5_paper_long_run_qualification/actual/"
          "p5_qualification_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "P5",
    "status": result.get("status") == "PASS",
    "state": result.get("state") == "PAPER_LONG_RUN_OFFLINE_QUALIFIED",
    "offline_qualified": result.get("qualified") is True,
    "thousand_cycles": (
        result.get("metrics", {}).get("successful_cycles") == 1000
    ),
    "zero_failures": (
        result.get("metrics", {}).get("failed_cycles") == 0
    ),
    "fault_matrix": result.get("fault_matrix", {}).get("passed") is True,
    "actual_not_qualified": (
        result.get("actual_paper_long_run_qualified") is False
    ),
    "paper_not_complete": result.get("paper_complete") is False,
    "live_not_complete": result.get("live_complete") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "P5_OFFLINE",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
