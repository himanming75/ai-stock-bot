import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_runtime.autonomous_cycle_v82_01_04 import run_autonomous_shadow_cycle

parser = argparse.ArgumentParser()
parser.add_argument("--execute-cycle", action="store_true")
args = parser.parse_args()

r = run_autonomous_shadow_cycle(
    policy_path=ROOT/"release/v82_01_to_v82_04/input/autonomous_shadow_cycle_policy.json",
    foundation_result_path=ROOT/"release/v81_01_to_v81_04/actual/shadow_trading_foundation_result.json",
    execution_result_path=ROOT/"release/v81_05_to_v81_08/actual/shadow_execution_result.json",
    portfolio_result_path=ROOT/"release/v81_09_to_v81_12/actual/shadow_portfolio_result.json",
    cycle_lock_path=ROOT/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle.lock.json",
    cycle_ledger_path=ROOT/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_ledger.jsonl",
    dashboard_path=ROOT/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_dashboard_state.json",
    recovery_path=ROOT/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_recovery.json",
    result_path=ROOT/"release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_result.json",
    execute_cycle=args.execute_cycle,
)
print(json.dumps(r, indent=2, sort_keys=True))
print("RESULT_FILE=" + r["result_path"])
raise SystemExit(0 if r["status"] == "PASS" else 2)
