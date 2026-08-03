
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.intraday_loop_v82_29_32 import run_intraday_loop

parser = argparse.ArgumentParser()
parser.add_argument("--execute-loop", action="store_true")
parser.add_argument("--resume-loop", action="store_true")
args = parser.parse_args()

result = run_intraday_loop(
    session_result_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_result.json"
    ),
    scheduler_result_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_result.json"
    ),
    signal_path=(
        ROOT / "release/v81_01_to_v81_04/actual/"
        "shadow_trade_observation.json"
    ),
    risk_result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    authorization_result_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_result.json"
    ),
    execution_result_path=(
        ROOT / "release/v81_05_to_v81_08/actual/"
        "shadow_execution_result.json"
    ),
    portfolio_result_path=(
        ROOT / "release/v81_09_to_v81_12/actual/"
        "shadow_portfolio_result.json"
    ),
    analytics_result_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_29_to_v82_32/input/"
        "intraday_loop_policy.json"
    ),
    loop_lock_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop.lock.json"
    ),
    loop_ledger_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop_ledger.jsonl"
    ),
    recovery_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop_recovery.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_29_to_v82_32/actual/"
        "intraday_loop_result.json"
    ),
    execute_loop=args.execute_loop,
    resume_loop=args.resume_loop,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
