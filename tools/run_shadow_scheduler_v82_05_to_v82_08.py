
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_runtime.scheduler_v82_05_08 import run_shadow_scheduler

parser = argparse.ArgumentParser()
parser.add_argument("--write-heartbeat", action="store_true")
parser.add_argument("--authorize-next-cycle", action="store_true")
args = parser.parse_args()

result = run_shadow_scheduler(
    cycle_result_path=(
        ROOT / "release/v82_01_to_v82_04/actual/"
        "autonomous_shadow_cycle_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_05_to_v82_08/input/"
        "shadow_scheduler_policy.json"
    ),
    heartbeat_path=(
        ROOT / "release/v82_05_to_v82_08/actual/"
        "shadow_scheduler_heartbeat.json"
    ),
    scheduler_lock_path=(
        ROOT / "release/v82_05_to_v82_08/actual/"
        "shadow_scheduler.lock.json"
    ),
    scheduler_ledger_path=(
        ROOT / "release/v82_05_to_v82_08/actual/"
        "shadow_scheduler_ledger.jsonl"
    ),
    dashboard_path=(
        ROOT / "release/v82_05_to_v82_08/actual/"
        "shadow_scheduler_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_05_to_v82_08/actual/"
        "shadow_scheduler_result.json"
    ),
    write_heartbeat=args.write_heartbeat,
    authorize_next_cycle=args.authorize_next_cycle,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
