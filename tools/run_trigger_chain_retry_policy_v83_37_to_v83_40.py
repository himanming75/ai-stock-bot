import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.trigger_chain_retry_policy_v83_37_40 import (
    run_trigger_chain_retry_policy,
)

parser = argparse.ArgumentParser()
parser.add_argument("--plan-retry", action="store_true")
parser.add_argument("--complete-retry", action="store_true")
parser.add_argument("--clear-retry-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_37_to_v83_40/actual"
result = run_trigger_chain_retry_policy(
    chain_result_path=(
        ROOT / "release/v83_33_to_v83_36/actual/"
        "trigger_recovery_dispatch_chain_result.json"
    ),
    trigger_plan_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger_plan.json"
    ),
    trigger_lock_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger.lock.json"
    ),
    recovery_snapshot_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch_recovery_snapshot.json"
    ),
    policy_path=(
        ROOT / "release/v83_37_to_v83_40/input/"
        "trigger_chain_retry_policy.json"
    ),
    retry_lock_path=actual / "trigger_retry.lock.json",
    retry_ledger_path=actual / "trigger_retry_ledger.jsonl",
    retry_plan_path=actual / "trigger_retry_plan.json",
    dashboard_path=(
        actual / "trigger_chain_retry_policy_dashboard_state.json"
    ),
    result_path=actual / "trigger_chain_retry_policy_result.json",
    plan_retry=args.plan_retry,
    complete_retry=args.complete_retry,
    clear_retry_lock=args.clear_retry_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
