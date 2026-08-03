
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.scheduled_run_dispatch_v83_21_24 import (
    run_scheduled_dispatch,
)

parser = argparse.ArgumentParser()
parser.add_argument("--execute-dispatch", action="store_true")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--clear-dispatch-lock", action="store_true")
args = parser.parse_args()

result = run_scheduled_dispatch(
    repository_root=ROOT,
    schedule_authorization_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_authorization.json"
    ),
    schedule_lock_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner.lock.json"
    ),
    supervised_result_path=(
        ROOT / "release/v83_13_to_v83_16/actual/"
        "supervised_automation_runner_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_21_to_v83_24/input/"
        "scheduled_run_dispatch_policy.json"
    ),
    dispatch_lock_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch.lock.json"
    ),
    dispatch_ledger_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch_ledger.jsonl"
    ),
    execution_report_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_execution_report.json"
    ),
    recovery_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch_recovery.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch_result.json"
    ),
    execute_dispatch=args.execute_dispatch,
    dry_run=args.dry_run,
    clear_dispatch_lock=args.clear_dispatch_lock,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
