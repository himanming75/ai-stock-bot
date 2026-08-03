
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.controlled_automation_cycle_v83_09_12 import (
    run_controlled_automation_cycle,
)

parser = argparse.ArgumentParser()
parser.add_argument("--execute-cycle", action="store_true")
parser.add_argument("--resume-cycle", action="store_true")
parser.add_argument("--clear-cycle-lock", action="store_true")
args = parser.parse_args()

result = run_controlled_automation_cycle(
    orchestrator_result_path=(
        ROOT / "release/v83_01_to_v83_04/actual/"
        "automated_orchestrator_result.json"
    ),
    dispatcher_result_path=(
        ROOT / "release/v83_05_to_v83_08/actual/"
        "local_action_dispatcher_result.json"
    ),
    orchestrator_action_plan_path=(
        ROOT / "release/v83_01_to_v83_04/actual/"
        "automated_orchestrator_action_plan.json"
    ),
    orchestrator_action_lock_path=(
        ROOT / "release/v83_01_to_v83_04/actual/"
        "automated_orchestrator_action.lock.json"
    ),
    policy_path=(
        ROOT / "release/v83_09_to_v83_12/input/"
        "controlled_automation_cycle_policy.json"
    ),
    cycle_lock_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle.lock.json"
    ),
    cycle_ledger_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle_ledger.jsonl"
    ),
    cycle_report_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle_report.json"
    ),
    recovery_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle_recovery.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_09_to_v83_12/actual/"
        "controlled_automation_cycle_result.json"
    ),
    execute_cycle=args.execute_cycle,
    resume_cycle=args.resume_cycle,
    clear_cycle_lock=args.clear_cycle_lock,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
