
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.session_manager_v82_21_24 import (
    run_paper_session_manager,
)

parser = argparse.ArgumentParser()
parser.add_argument("--start-session", action="store_true")
parser.add_argument("--end-session", action="store_true")
parser.add_argument("--recover-session", action="store_true")
args = parser.parse_args()

result = run_paper_session_manager(
    authorization_result_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_21_to_v82_24/input/"
        "paper_session_policy.json"
    ),
    session_state_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_state.json"
    ),
    session_lock_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session.lock.json"
    ),
    daily_ledger_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_daily_ledger.jsonl"
    ),
    daily_snapshot_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_daily_snapshot.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_result.json"
    ),
    start_session_requested=args.start_session,
    end_session_requested=args.end_session,
    recover_session_requested=args.recover_session,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
