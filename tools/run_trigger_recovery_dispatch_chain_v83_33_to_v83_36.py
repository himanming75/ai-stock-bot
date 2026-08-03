import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.trigger_recovery_dispatch_chain_v83_33_36 import (
    run_trigger_recovery_dispatch_chain,
)

parser = argparse.ArgumentParser()
parser.add_argument("--recover-trigger", action="store_true")
parser.add_argument("--clear-recovery-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_33_to_v83_36/actual"
result = run_trigger_recovery_dispatch_chain(
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
    dispatcher_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    ),
    recovery_snapshot_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch_recovery_snapshot.json"
    ),
    completion_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "automatic_trigger_completion_result.json"
    ),
    recovery_lock_path=actual / "trigger_recovery.lock.json",
    chain_ledger_path=actual / "trigger_dispatch_chain_ledger.jsonl",
    dashboard_path=(
        actual / "trigger_recovery_dispatch_chain_dashboard_state.json"
    ),
    result_path=actual / "trigger_recovery_dispatch_chain_result.json",
    policy_path=(
        ROOT / "release/v83_33_to_v83_36/input/"
        "trigger_recovery_dispatch_chain_policy.json"
    ),
    recover_trigger=args.recover_trigger,
    clear_recovery_lock=args.clear_recovery_lock,
    observed_at_override=args.observed_at,
)
print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
