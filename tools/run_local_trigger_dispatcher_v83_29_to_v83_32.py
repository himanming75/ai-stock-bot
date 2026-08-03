import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.local_trigger_dispatcher_v83_29_32 import (
    run_local_trigger_dispatcher,
)

parser = argparse.ArgumentParser()
parser.add_argument("--dispatch", action="store_true")
parser.add_argument("--execute", action="store_true")
parser.add_argument("--clear-dispatch-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

result = run_local_trigger_dispatcher(
    repository_root=ROOT,
    trigger_plan_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger_plan.json"
    ),
    trigger_lock_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger.lock.json"
    ),
    dispatch_lock_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch.lock.json"
    ),
    dispatch_ledger_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch_ledger.jsonl"
    ),
    recovery_snapshot_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch_recovery_snapshot.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_29_to_v83_32/input/"
        "local_trigger_dispatcher_policy.json"
    ),
    trigger_completion_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "automatic_trigger_completion_result.json"
    ),
    dispatch=args.dispatch,
    dry_run=not args.execute,
    clear_dispatch_lock=args.clear_dispatch_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
