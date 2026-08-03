import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.full_schedule_completion_orchestrator_v83_57_60 import (
    run_full_schedule_completion_orchestrator,
)

parser = argparse.ArgumentParser()
parser.add_argument("--start-cycle", action="store_true")
parser.add_argument("--finalize-cycle", action="store_true")
parser.add_argument("--clear-cycle-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_57_to_v83_60/actual"
result = run_full_schedule_completion_orchestrator(
    schedule_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    ),
    dispatcher_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    ),
    chain_result_path=(
        ROOT / "release/v83_33_to_v83_36/actual/"
        "trigger_recovery_dispatch_chain_result.json"
    ),
    retry_result_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_chain_retry_policy_result.json"
    ),
    approval_result_path=(
        ROOT / "release/v83_41_to_v83_44/actual/"
        "retry_approval_supervised_reentry_result.json"
    ),
    guard_result_path=(
        ROOT / "release/v83_45_to_v83_48/actual/"
        "reentry_execution_guard_audit_result.json"
    ),
    runner_result_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_result.json"
    ),
    retry_completion_result_path=(
        ROOT / "release/v83_53_to_v83_56/actual/"
        "retry_cycle_completion_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_57_to_v83_60/input/"
        "full_schedule_completion_orchestrator_policy.json"
    ),
    cycle_lock_path=actual / "full_schedule_completion.lock.json",
    ledger_path=actual / "full_schedule_completion_ledger.jsonl",
    certificate_path=(
        actual / "full_schedule_completion_certificate.json"
    ),
    dashboard_path=(
        actual / "full_schedule_completion_orchestrator_dashboard_state.json"
    ),
    result_path=(
        actual / "full_schedule_completion_orchestrator_result.json"
    ),
    start_cycle=args.start_cycle,
    finalize_cycle=args.finalize_cycle,
    clear_cycle_lock=args.clear_cycle_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
