import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.supervised_reentry_runner_v83_49_52 import (
    run_supervised_reentry_runner,
)

parser = argparse.ArgumentParser()
parser.add_argument("--execute", action="store_true")
parser.add_argument("--run-local", action="store_true")
parser.add_argument("--clear-runner-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_49_to_v83_52/actual"
result = run_supervised_reentry_runner(
    repository_root=ROOT,
    guard_result_path=(
        ROOT / "release/v83_45_to_v83_48/actual/"
        "reentry_execution_guard_audit_result.json"
    ),
    execution_plan_path=(
        ROOT / "release/v83_45_to_v83_48/actual/"
        "reentry_execution_plan.json"
    ),
    execution_lock_path=(
        ROOT / "release/v83_45_to_v83_48/actual/"
        "reentry_execution.lock.json"
    ),
    approval_lock_path=(
        ROOT / "release/v83_41_to_v83_44/actual/"
        "retry_approval.lock.json"
    ),
    retry_lock_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_retry.lock.json"
    ),
    policy_path=(
        ROOT / "release/v83_49_to_v83_52/input/"
        "supervised_reentry_runner_policy.json"
    ),
    runner_lock_path=actual / "supervised_reentry_runner.lock.json",
    audit_ledger_path=actual / "supervised_reentry_runner_ledger.jsonl",
    recovery_snapshot_path=(
        actual / "supervised_reentry_runner_recovery_snapshot.json"
    ),
    completion_result_path=(
        actual / "supervised_reentry_runner_completion.json"
    ),
    dashboard_path=(
        actual / "supervised_reentry_runner_dashboard_state.json"
    ),
    result_path=actual / "supervised_reentry_runner_result.json",
    execute=args.execute,
    dry_run=not args.run_local,
    clear_runner_lock=args.clear_runner_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
