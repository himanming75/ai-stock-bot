
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.end_of_day_v82_33_36 import run_end_of_day_manager

parser = argparse.ArgumentParser()
parser.add_argument("--certify-day", action="store_true")
parser.add_argument("--prepare-next-day", action="store_true")
args = parser.parse_args()

result = run_end_of_day_manager(
    session_result_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_result.json"
    ),
    scheduler_result_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_result.json"
    ),
    intraday_result_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop_result.json"
    ),
    performance_result_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_result.json"
    ),
    risk_result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_33_to_v82_36/input/"
        "end_of_day_policy.json"
    ),
    daily_report_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "end_of_day_daily_report.json"
    ),
    certification_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "daily_paper_certification.json"
    ),
    ledger_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "end_of_day_ledger.jsonl"
    ),
    next_day_state_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "next_trading_day_state.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "end_of_day_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_33_to_v82_36/actual/"
        "end_of_day_result.json"
    ),
    certify_day_requested=args.certify_day,
    prepare_next_day_requested=args.prepare_next_day,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
