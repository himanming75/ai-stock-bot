
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.multi_day_runtime_v82_37_40 import (
    run_multi_day_runtime,
)

parser = argparse.ArgumentParser()
parser.add_argument("--execute-rollover", action="store_true")
parser.add_argument("--reset-runtime", action="store_true")
args = parser.parse_args()

result = run_multi_day_runtime(
    end_of_day_result_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "end_of_day_result.json"
    ),
    certification_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "daily_paper_certification.json"
    ),
    next_day_state_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "next_trading_day_state.json"
    ),
    policy_path=(
        ROOT / "release/v82_37_to_v82_40/input/"
        "multi_day_runtime_policy.json"
    ),
    runtime_state_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "multi_day_runtime_state.json"
    ),
    rollover_lock_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "multi_day_rollover.lock.json"
    ),
    runtime_ledger_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "multi_day_runtime_ledger.jsonl"
    ),
    rollover_plan_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "next_day_rollover_plan.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "multi_day_runtime_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_37_to_v82_40/actual/"
        "multi_day_runtime_result.json"
    ),
    execute_rollover=args.execute_rollover,
    reset_runtime=args.reset_runtime,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
