
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.local_action_dispatcher_v83_05_08 import (
    run_local_action_dispatcher,
)

parser = argparse.ArgumentParser()
parser.add_argument("--execute-action", action="store_true")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--clear-dispatch-lock", action="store_true")
args = parser.parse_args()

result = run_local_action_dispatcher(
    repository_root=ROOT,
    action_plan_path=(
        ROOT / "release/v83_01_to_v83_04/actual/"
        "automated_orchestrator_action_plan.json"
    ),
    action_lock_path=(
        ROOT / "release/v83_01_to_v83_04/actual/"
        "automated_orchestrator_action.lock.json"
    ),
    policy_path=(
        ROOT / "release/v83_05_to_v83_08/input/"
        "local_action_dispatcher_policy.json"
    ),
    dispatch_lock_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatch.lock.json"
    ),
    dispatch_ledger_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatch_ledger.jsonl"
    ),
    execution_report_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_execution_report.json"
    ),
    recovery_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatch_recovery.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatcher_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatcher_result.json"
    ),
    execute_action=args.execute_action,
    dry_run=args.dry_run,
    clear_dispatch_lock=args.clear_dispatch_lock,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
