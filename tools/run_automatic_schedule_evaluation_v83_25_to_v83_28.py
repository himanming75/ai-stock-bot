
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.automatic_schedule_evaluation_v83_25_28 import (
    run_automatic_schedule_evaluation,
)

parser = argparse.ArgumentParser()
parser.add_argument("--create-trigger", action="store_true")
parser.add_argument("--complete-trigger", action="store_true")
parser.add_argument("--clear-trigger-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

result = run_automatic_schedule_evaluation(
    session_result_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_result.json"
    ),
    risk_result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    supervised_result_path=(
        ROOT / "release/v83_13_to_v83_16/actual/"
        "supervised_automation_runner_result.json"
    ),
    schedule_result_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_25_to_v83_28/input/"
        "automatic_schedule_evaluation_policy.json"
    ),
    trigger_lock_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger.lock.json"
    ),
    trigger_ledger_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger_ledger.jsonl"
    ),
    trigger_plan_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger_plan.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_evaluation_result.json"
    ),
    create_trigger=args.create_trigger,
    complete_trigger=args.complete_trigger,
    clear_trigger_lock=args.clear_trigger_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
