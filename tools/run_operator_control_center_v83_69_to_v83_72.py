import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.operator_control_center_v83_69_72 import (
    run_operator_control_center,
)

parser = argparse.ArgumentParser()
parser.add_argument("--action", default="")
parser.add_argument("--note", default="")
parser.add_argument("--clear-control-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_69_to_v83_72/actual"
result = run_operator_control_center(
    certification_result_path=(
        ROOT / "release/v83_65_to_v83_68/actual/"
        "end_to_end_paper_cycle_certification_result.json"
    ),
    orchestrator_result_path=(
        ROOT / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion_orchestrator_result.json"
    ),
    recovery_result_path=(
        ROOT / "release/v83_61_to_v83_64/actual/"
        "crash_recovery_restart_result.json"
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
    policy_path=(
        ROOT / "release/v83_69_to_v83_72/input/"
        "operator_control_center_policy.json"
    ),
    control_lock_path=actual / "operator_control.lock.json",
    control_request_path=actual / "operator_control_request.json",
    control_ledger_path=actual / "operator_control_center_ledger.jsonl",
    unified_dashboard_path=(
        actual / "operator_control_center_unified_dashboard.json"
    ),
    result_path=actual / "operator_control_center_result.json",
    action=args.action,
    note=args.note,
    clear_control_lock=args.clear_control_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
