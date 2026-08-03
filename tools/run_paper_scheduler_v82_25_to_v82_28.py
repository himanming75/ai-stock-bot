
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.scheduler_v82_25_28 import (
    run_paper_trading_scheduler,
)

parser = argparse.ArgumentParser()
parser.add_argument("--write-heartbeat", action="store_true")
parser.add_argument("--authorize-tick", action="store_true")
parser.add_argument("--complete-tick", action="store_true")
args = parser.parse_args()

result = run_paper_trading_scheduler(
    session_result_path=(
        ROOT / "release/v82_21_to_v82_24/actual/"
        "paper_session_manager_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_25_to_v82_28/input/"
        "paper_scheduler_policy.json"
    ),
    heartbeat_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_heartbeat.json"
    ),
    tick_lock_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_tick.lock.json"
    ),
    tick_ledger_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_tick_ledger.jsonl"
    ),
    dashboard_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_25_to_v82_28/actual/"
        "paper_scheduler_result.json"
    ),
    write_heartbeat=args.write_heartbeat,
    authorize_tick=args.authorize_tick,
    complete_tick=args.complete_tick,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
