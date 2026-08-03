
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_runtime.risk_controller_v82_13_16 import (
    run_shadow_risk_controller,
)

parser = argparse.ArgumentParser()
parser.add_argument("--emergency-stop", action="store_true")
parser.add_argument("--request-recovery", action="store_true")
args = parser.parse_args()

result = run_shadow_risk_controller(
    analytics_result_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_result.json"
    ),
    portfolio_state_path=(
        ROOT / "release/v81_09_to_v81_12/actual/"
        "shadow_portfolio_state.json"
    ),
    policy_path=(
        ROOT / "release/v82_13_to_v82_16/input/"
        "shadow_risk_policy.json"
    ),
    kill_switch_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_kill_switch.json"
    ),
    recovery_lock_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_recovery.lock.json"
    ),
    risk_report_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_report.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    emergency_stop_requested=args.emergency_stop,
    recovery_requested=args.request_recovery,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
