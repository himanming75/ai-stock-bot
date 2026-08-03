import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.crash_recovery_restart_continuation_v83_61_64 import (
    run_crash_recovery_restart_continuation,
)

parser = argparse.ArgumentParser()
parser.add_argument("--analyze", action="store_true")
parser.add_argument("--apply-recovery", action="store_true")
parser.add_argument("--clear-stale-locks", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_61_to_v83_64/actual"
result = run_crash_recovery_restart_continuation(
    orchestrator_result_path=(
        ROOT / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion_orchestrator_result.json"
    ),
    cycle_lock_path=(
        ROOT / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion.lock.json"
    ),
    dispatcher_lock_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch.lock.json"
    ),
    runner_lock_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner.lock.json"
    ),
    retry_lock_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_retry.lock.json"
    ),
    approval_lock_path=(
        ROOT / "release/v83_41_to_v83_44/actual/"
        "retry_approval.lock.json"
    ),
    policy_path=(
        ROOT / "release/v83_61_to_v83_64/input/"
        "crash_recovery_restart_policy.json"
    ),
    recovery_lock_path=actual / "restart_recovery.lock.json",
    recovery_plan_path=actual / "restart_recovery_plan.json",
    recovery_snapshot_path=actual / "restart_recovery_snapshot.json",
    recovery_ledger_path=actual / "restart_recovery_ledger.jsonl",
    dashboard_path=actual / "crash_recovery_restart_dashboard_state.json",
    result_path=actual / "crash_recovery_restart_result.json",
    analyze=args.analyze,
    apply_recovery=args.apply_recovery,
    clear_stale_locks=args.clear_stale_locks,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
