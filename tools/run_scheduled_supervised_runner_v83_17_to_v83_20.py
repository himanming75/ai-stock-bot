
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.scheduled_supervised_runner_v83_17_20 import (
    run_scheduled_supervised_runner,
)

parser = argparse.ArgumentParser()
parser.add_argument("--authorize-run", action="store_true")
parser.add_argument("--complete-run", action="store_true")
parser.add_argument("--clear-schedule-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

result = run_scheduled_supervised_runner(
    market_calendar_path=(
        ROOT / "release/v83_17_to_v83_20/input/"
        "market_calendar_state.json"
    ),
    risk_result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    supervised_result_path=(
        ROOT / "release/v83_13_to_v83_16/actual/"
        "supervised_automation_runner_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_17_to_v83_20/input/"
        "scheduled_supervised_runner_policy.json"
    ),
    schedule_lock_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner.lock.json"
    ),
    schedule_ledger_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_ledger.jsonl"
    ),
    authorization_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_authorization.json"
    ),
    dashboard_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_result.json"
    ),
    authorize_run=args.authorize_run,
    complete_run=args.complete_run,
    clear_schedule_lock=args.clear_schedule_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
